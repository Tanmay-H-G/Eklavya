"""
JARVIS / Eklavya — main.py
===========================
Entry point. Run:  python main.py
Requires Chrome/Chromium installed (eel opens it automatically).
"""

import os
import json
import threading
import asyncio
import time
from random import choice
import eel
from dotenv import load_dotenv
from threading import Lock

# ── Ensure correct working directory ──────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

Assistantname = os.environ.get('AssistantName', 'Eklavya')
Username      = os.environ.get('NickName',      'Admin')
InputLanguage = os.environ.get('InputLanguage', 'en')

# ── Import Backend modules ────────────────────────────────────────────────────
try:
    from Backend.Extra        import AnswerModifier, QueryModifier, LoadMessages, GuiMessagesConverter, SaveMessage
    from Backend.Automation   import run_automation as Automation
    from Backend.Automation   import PROFESSIONAL_RESPONSES as professional_responses
    from Backend.RSE          import RealTimeChatBotAI
    from Backend.Chatbot      import ChatBotAI
    from Backend.TTS          import TTS
    from Backend.StatsPusher  import start_stats_pusher
    from Backend.Database     import (
        init_db, add_user, verify_user, migrate_json_data, clear_chats,
        create_session, verify_session, delete_session, delete_all_sessions,
        set_preference, get_preference, get_db_stats, get_user_by_id
    )
    print("All Backend modules loaded.")
except Exception as e:
    print(f"Backend Import Error: {e}")
    raise

# ── Global state ──────────────────────────────────────────────────────────────
state             = 'Available...'
js_messageslist   = []
lock              = Lock()
CURRENT_USER_ID   = None
CURRENT_USER_NAME = None
CURRENT_SESSION_TOKEN = None          # For remember-me
CURRENT_SESSION_ID    = 'default'     # For grouping conversations
AI_MODE           = 'gemini'          # 'gemini' | 'groq' | 'ollama'


def UniversalTranslator(text: str) -> str:
    """Translate non-English input to English."""
    try:
        import mtranslate as mt
        return mt.translate(text, 'en', 'auto').capitalize()
    except Exception as e:
        print(f"[Translate] Error: {e}")
        return text


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN EXECUTION — the full pipeline for every command
# ─────────────────────────────────────────────────────────────────────────────

def MainExecution(Query: str):
    global state
    print(f"\n[PIPELINE] Input: '{Query}' | Mode: {AI_MODE}")

    # Translate if non-English
    if 'en' not in InputLanguage.lower():
        Query = UniversalTranslator(Query)

    Query = QueryModifier(Query)

    # Don't run if system is already working
    if state not in ('Available...', 'Listening...'):
        print(f"[PIPELINE] Busy ({state}), ignoring.")
        return

    state = 'Thinking...'

    try:
        print("[PIPELINE] Classifying query...")
        from Backend.AutoModel import Model
        Decision = Model(Query)
        print(f"[PIPELINE] Decision: {Decision}")

        # ── AI conversation ──────────────────────────────────────────────
        if Decision and ('general' in Decision[0] or 'realtime' in Decision[0]):
            if Decision[0] == 'general':
                state  = 'Answering...'
                Answer = AnswerModifier(ChatBotAI(Query, user_id=CURRENT_USER_ID, mode=AI_MODE, session_id=CURRENT_SESSION_ID))
            else:
                state  = 'Searching...'
                Answer = AnswerModifier(RealTimeChatBotAI(Query, user_id=CURRENT_USER_ID, session_id=CURRENT_SESSION_ID))

            print(f"[PIPELINE] Answer: {Answer[:100]}...")
            TTS(Answer)

        # ── System automation ─────────────────────────────────────────────
        else:
            state = 'Working...'

            def _run():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(
                        Automation(Decision, print)
                    )
                    SaveMessage('user', Query, user_id=CURRENT_USER_ID, session_id=CURRENT_SESSION_ID)
                    
                    # If automation returns a specific result, use it, else use a professional fallback
                    response = result if (result and result.strip()) else choice(professional_responses)
                    
                    SaveMessage('assistant', response, user_id=CURRENT_USER_ID, session_id=CURRENT_SESSION_ID)
                    TTS(response)
                    
                    # Force update the state so UI knows we are done
                    global state
                    state = 'Available...'
                except Exception as e:
                    print(f"[PIPELINE] Automation error: {e}")
                    TTS("I ran into an issue with that.")
                finally:
                    new_loop.close()

            _run()

    except Exception as e:
        print(f"[PIPELINE] Error: {e}")
        TTS("I encountered an error. Please try again.")

    finally:
        state = 'Listening...'
        print("[PIPELINE] Done. Ready.")


# ─────────────────────────────────────────────────────────────────────────────
#  EEL EXPOSED FUNCTIONS  (called from JavaScript)
# ─────────────────────────────────────────────────────────────────────────────

@eel.expose
def js_messages():
    """
    Poll for new messages. Returns only messages not yet shown in GUI.
    Called by the frontend every second.
    """
    global js_messageslist
    try:
        with lock:
            messages = LoadMessages(user_id=CURRENT_USER_ID, session_id=CURRENT_SESSION_ID)

        if len(messages) < len(js_messageslist):
            js_messageslist = []

        if js_messageslist != messages:
            new_raw       = messages[len(js_messageslist):]
            new_formatted = GuiMessagesConverter(new_raw)
            js_messageslist = list(messages)
            return new_formatted

    except Exception as e:
        print(f"[eel] js_messages error: {e}")

    return []


@eel.expose
def js_login(username, password):
    """Login a user. Returns success dict with session token if remember_me."""
    global CURRENT_USER_ID, CURRENT_USER_NAME, js_messageslist
    result = verify_user(username, password)
    if result['success']:
        CURRENT_USER_ID   = result['user_id']
        CURRENT_USER_NAME = result['username']
        js_messageslist   = []
        # Load their preferred AI mode
        global AI_MODE
        saved_mode = get_preference(CURRENT_USER_ID, 'ai_mode', 'gemini')
        AI_MODE = saved_mode
        print(f"[Auth] '{CURRENT_USER_NAME}' logged in. Mode: {AI_MODE}")
        return {
            "status":   "success",
            "username": result['username'],
            "ai_mode":  AI_MODE,
        }
    return {"status": "error", "message": result.get('error', 'Login failed.')}


@eel.expose
def js_login_with_token(token):
    """Auto-login using a remember-me token stored in browser localStorage."""
    global CURRENT_USER_ID, CURRENT_USER_NAME, js_messageslist, AI_MODE
    result = verify_session(token)
    if result:
        CURRENT_USER_ID   = result['user_id']
        CURRENT_USER_NAME = result['username']
        js_messageslist   = []
        saved_mode = get_preference(CURRENT_USER_ID, 'ai_mode', 'gemini')
        AI_MODE = saved_mode
        print(f"[Auth] '{CURRENT_USER_NAME}' auto-logged in via token. Mode: {AI_MODE}")
        return {
            "status":   "success",
            "username": result['username'],
            "ai_mode":  AI_MODE,
        }
    return {"status": "error", "message": "Session expired. Please log in again."}


@eel.expose
def js_create_session():
    """Create a persistent session token (remember me for 30 days)."""
    if not CURRENT_USER_ID:
        return None
    token = create_session(CURRENT_USER_ID, days=30)
    return token


@eel.expose
def js_signup(username, password, email=None, phone=None):
    """Register a new user with email/phone validation."""
    result = add_user(username, password, email=email, phone=phone)
    if result['success']:
        print(f"[Auth] User '{username}' registered.")
        migrate_json_data(result['user_id'])
        return {"status": "success", "message": "Account created! Please sign in."}
    return {"status": "error", "message": result.get('error', 'Registration failed.')}


@eel.expose
def js_logout():
    """Log out the current user."""
    global CURRENT_USER_ID, CURRENT_USER_NAME, js_messageslist, AI_MODE
    print(f"[Auth] '{CURRENT_USER_NAME}' logged out.")
    CURRENT_USER_ID   = None
    CURRENT_USER_NAME = None
    js_messageslist   = []
    AI_MODE           = 'gemini'
    return {"status": "success"}


@eel.expose
def js_logout_all_devices():
    """Log out from all devices by deleting all session tokens."""
    if CURRENT_USER_ID:
        delete_all_sessions(CURRENT_USER_ID)
    return js_logout()


@eel.expose
def js_state(stat=None):
    """Get or set the current assistant state."""
    global state
    if stat:
        state = stat
    return state


@eel.expose
def js_mic(transcription: str):
    """
    Called from the browser with the voice transcription.
    Runs MainExecution in a background thread so UI doesn't freeze.
    """
    if not transcription or len(transcription.strip()) < 2:
        return

    text = transcription.strip()
    print(f"[MIC] Captured: '{text}'")

    # ── Interrupt ongoing speech ──
    global state
    try:
        import pygame
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
    except Exception:
        pass

    state = 'Listening...'

    threading.Thread(
        target=MainExecution,
        args=(text,),
        daemon=True
    ).start()


@eel.expose
def js_set_mode(mode: str):
    """Set AI mode: 'gemini', 'groq', or 'ollama'. Persists per user."""
    global AI_MODE
    valid = ('gemini', 'groq', 'ollama')
    if mode not in valid:
        return {"status": "error", "message": f"Invalid mode. Use: {valid}"}
    AI_MODE = mode
    if CURRENT_USER_ID:
        set_preference(CURRENT_USER_ID, 'ai_mode', mode)
    print(f"[Mode] AI mode set to: {mode}")
    return {"status": "success", "mode": mode}


@eel.expose
def js_get_mode():
    """Return current AI mode."""
    return AI_MODE


@eel.expose
def js_db_stats():
    """Return database statistics for the UI."""
    return get_db_stats()


@eel.expose
def js_user_info():
    """Return current user profile info."""
    if not CURRENT_USER_ID:
        return None
    return get_user_by_id(CURRENT_USER_ID)


@eel.expose
def js_page(cpage=None):
    """Navigation between pages."""
    if cpage == 'home':
        try: eel.openHome()()
        except Exception: pass
    elif cpage == 'settings':
        try: eel.openSettings()()
        except Exception: pass


@eel.expose
def js_assistantname():
    return Assistantname


@eel.expose
def js_username():
    return CURRENT_USER_NAME or Username


@eel.expose
def js_language():
    return InputLanguage


@eel.expose
def js_clear_chat():
    """
    Starts a NEW conversation session. 
    Does NOT delete old messages from the database, but clears the UI.
    """
    try:
        global CURRENT_SESSION_ID, js_messageslist
        # Generate a unique session ID based on timestamp
        CURRENT_SESSION_ID = f"session_{int(time.time())}"
        js_messageslist = []
        print(f"[Session] Started new session: {CURRENT_SESSION_ID}")
        return CURRENT_SESSION_ID
    except Exception as e:
        print(f"[eel] New session error: {e}")
        return False


@eel.expose
def js_get_sessions():
    """Get all unique chat sessions for the logged-in user."""
    if not CURRENT_USER_ID:
        return []
    try:
        from Backend.Database import get_user_sessions
        return get_user_sessions(CURRENT_USER_ID)
    except Exception as e:
        print(f"[eel] js_get_sessions error: {e}")
        return []


@eel.expose
def js_load_session(session_id: str):
    """Load a specific chat session."""
    global CURRENT_SESSION_ID, js_messageslist
    try:
        CURRENT_SESSION_ID = session_id
        js_messageslist = []
        print(f"[Session] Switched to session: {CURRENT_SESSION_ID}")
        return True
    except Exception as e:
        print(f"[eel] js_load_session error: {e}")
        return False


@eel.expose
def js_stop_speech():
    """Immediately stop any ongoing TTS speech playback (user interruption)."""
    try:
        import pygame
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            print("[TTS] Speech interrupted by user.")
            return True
    except Exception as e:
        print(f"[eel] js_stop_speech error: {e}")
    return False


# ── Python → JavaScript helpers ───────────────────────────────────────────────

def python_call_to_start_video():
    try: eel.startWebcam()()
    except Exception: pass

def python_call_to_stop_video():
    try: eel.stopWebcam()()
    except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
#  STARTUP
# ─────────────────────────────────────────────────────────────────────────────

# ── Init Database ──
init_db()

eel.init('web')

# Chrome launch settings
eel_kwargs = {
    'mode':         'chrome',
    'port':         44444,
    'size':         (1200, 720),
    'cmdline_args': [
        '--force-device-scale-factor=1',
        '--use-fake-ui-for-media-stream',
        '--disable-infobars',
        '--no-first-run',
    ]
}

print(f"\n{'='*55}")
print(f"  {Assistantname} — Starting up")
print(f"  AI: Gemini (default) → Groq → Ollama (fallback chain)")
print(f"  Current mode: {AI_MODE.upper()}")
print(f"  DB: eklavya.db (SQLite)")
print(f"{'='*55}\n")

# Start system stats pusher
threading.Thread(
    target=lambda: (time.sleep(3), start_stats_pusher(eel)),
    daemon=True
).start()

try:
    eel.start('spider.html', **eel_kwargs)
except (SystemExit, KeyboardInterrupt):
    print(f"\n{Assistantname} stopped.")
except Exception as e:
    print(f"\n[ERROR] Could not start: {e}")
    print("\nTroubleshooting:")
    print("  1. Is Chrome/Chromium installed?")
    print("  2. Try:  pip install eel")
    print("  3. Make sure 'web/' folder exists with spider.html")
