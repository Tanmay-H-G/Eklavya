"""
Backend/Automation.py
Executes all system-level actions:
  - Open / close applications
  - Volume control (pycaw, with keyboard fallback)
  - Screenshots
  - System info (CPU, RAM, battery, disk)
  - Web search, open URLs
  - YouTube, Spotify
  - Notes (saved to notes.json)
  - Reminders
  - Power (lock, shutdown, restart)
"""

import os
import re
import json
import subprocess
import webbrowser
import datetime
import psutil
import platform
from random import choice

# ── Volume control (pycaw) ────────────────────────────────────────────────────
_vol_interface = None
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _devices = AudioUtilities.GetSpeakers()
    if hasattr(_devices, 'Activate'):
        _iface   = _devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        _vol_interface = cast(_iface, POINTER(IAudioEndpointVolume))
    else:
        print("[Automation] pycaw device has no Activate method. Volume via keyboard fallback.")
except Exception as e:
    print(f"[Automation] pycaw not available ({e}). Volume via keyboard fallback.")

# ── Screenshot ────────────────────────────────────────────────────────────────
try:
    from PIL import ImageGrab
    _PIL = True
except ImportError:
    _PIL = False
    try:
        import pyautogui as _pag
    except ImportError:
        _pag = None

# ── Professional responses for completed actions ───────────────────────────────
PROFESSIONAL_RESPONSES = [
    "Done. Anything else?",
    "Task completed.",
    "Consider it done.",
    "I've taken care of that.",
    "All done.",
    "Sure thing. Done.",
    "Got it.",
    "Executed successfully.",
]

# ── App name → executable (Windows) ──────────────────────────────────────────
APP_MAP = {
    # Browsers
    'chrome': 'chrome.exe', 'google chrome': 'chrome.exe',
    'firefox': 'firefox.exe', 'mozilla firefox': 'firefox.exe',
    'edge': 'msedge.exe', 'microsoft edge': 'msedge.exe',
    'brave': 'brave.exe', 'opera': 'opera.exe',
    # Communication
    'discord': 'discord.exe', 'slack': 'slack.exe',
    'skype': 'skype.exe', 'teams': 'teams.exe',
    'microsoft teams': 'teams.exe', 'zoom': 'zoom.exe',
    'telegram': 'telegram.exe', 'whatsapp': 'whatsapp.exe',
    # Office
    'word': 'winword.exe', 'excel': 'excel.exe',
    'powerpoint': 'powerpnt.exe', 'outlook': 'outlook.exe',
    'onenote': 'onenote.exe', 'notepad': 'notepad.exe',
    'notepad++': 'notepad++.exe',
    # Dev
    'vscode': 'code.exe', 'visual studio code': 'code.exe',
    'code': 'code.exe', 'pycharm': 'pycharm64.exe',
    'cmd': 'cmd.exe', 'command prompt': 'cmd.exe',
    'powershell': 'powershell.exe', 'terminal': 'wt.exe',
    # Media
    'spotify': 'spotify.exe', 'vlc': 'vlc.exe',
    # System
    'task manager': 'taskmgr.exe', 'taskmgr': 'taskmgr.exe',
    'explorer': 'explorer.exe', 'file explorer': 'explorer.exe',
    'calculator': 'calc.exe', 'paint': 'mspaint.exe',
    'settings': 'ms-settings:',
    'control panel': 'control.exe',
    'snipping tool': 'snippingtool.exe',
    # Web shortcuts
    'netflix': 'https://netflix.com',
    'youtube': 'https://youtube.com',
    'gmail': 'https://mail.google.com',
    'github': 'https://github.com',
    'twitter': 'https://twitter.com',
    'instagram': 'https://instagram.com',
    'whatsapp web': 'https://web.whatsapp.com',
    'whatsapp': 'whatsapp:',
    'chatgpt': 'https://chat.openai.com',
    'claude': 'https://claude.ai',
    'perplexity': 'https://perplexity.ai',
    'grok': 'https://grok.com',
}

NOTES_FILE = 'notes.json'


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_automation(decisions: list, callback=print) -> str:
    """
    Execute a list of decisions returned by AutoModel.
    Each decision is a string like 'open chrome', 'screenshot', etc.
    """
    if not decisions:
        return choice(PROFESSIONAL_RESPONSES)

    results = []
    for decision in decisions:
        if not decision or not decision.strip():
            continue
        result = _execute(decision.strip(), callback)
        if result:
            results.append(result.strip())

    if not results:
        return choice(PROFESSIONAL_RESPONSES)

    # Convert distinct responses into a more human-like combined string
    openings = [r.replace('Opening ', '').replace('.', '').strip() for r in results if r.startswith('Opening ')]
    others = [r for r in results if not r.startswith('Opening ')]

    final_str = ""
    if openings:
        if len(openings) > 1:
            opened_str = ", ".join(openings[:-1]) + ", and " + openings[-1]
            final_str += f"Opening {opened_str}. "
        else:
            final_str += f"Opening {openings[0]}. "
        
    for o in others:
        final_str += o + " "

    return final_str.strip()


def _execute(decision: str, callback=print) -> str:
    """Route a single decision to the right handler."""
    d = decision.lower().strip()
    callback(f"[Automation] → {decision}")

    try:
        # ── App open ────────────────────────────────────────────────────────
        if d.startswith('open ') and not d.startswith('open_url'):
            return _open_app(d[5:].strip())

        # ── App close ───────────────────────────────────────────────────────
        if d.startswith('close '):
            return _close_app(d[6:].strip())

        # ── Exit Eklavya ────────────────────────────────────────────────────
        if d == 'exit_eklavya':
            return _exit_eklavya()

        # ── YouTube ─────────────────────────────────────────────────────────
        if 'on youtube' in d or d.startswith('play_youtube ') or d.startswith('play ') and 'youtube' in d:
            query = re.sub(r'^play_youtube\s+|play\s+|on youtube.*', '', d).strip()
            query = re.sub(r'\s+on\s+youtube.*', '', query, flags=re.IGNORECASE).strip()
            url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Searching YouTube for {query}. Press Enter on the first result to play."

        # ── Spotify ─────────────────────────────────────────────────────────
        if d.startswith('play_spotify ') or ('on spotify' in d and 'play' in d):
            query = re.sub(r'^play_spotify\s+', '', d).strip()
            query = re.sub(r'\s+on\s+spotify.*', '', query, flags=re.IGNORECASE).strip()
            return _play_spotify(query)

        # ── Media Controls ──
        if d.startswith('media '):
            action = d.split(' ')[1]
            import pyautogui
            if action in ['pause', 'stop', 'play', 'resume']:
                pyautogui.press('playpause')
                return f"Toggled playback."
            elif action == 'next':
                pyautogui.press('nexttrack')
                return "Skipped to next track."
            elif action == 'previous':
                pyautogui.press('prevtrack')
                return "Went to previous track."

        # ── WhatsApp Message ────────────────────────────────────────────────
        if d.startswith('send_whatsapp '):
            raw = d[14:].strip()
            parts = raw.split('|', 1)
            if len(parts) < 2:
                return "I couldn't understand who to message or what to say."
            contact_name = parts[0].strip()
            msg_text = parts[1].strip()
            return _send_whatsapp_message(contact_name, msg_text)

        # ── Web search ──────────────────────────────────────────────────────
        if d.startswith('search_web '):
            query = d[11:].strip()
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            return f"Searching Google for: {query}"

        # ── Open URL ────────────────────────────────────────────────────────
        if d.startswith('open_url '):
            url = d[9:].strip()
            if not url.startswith('http'):
                url = 'https://' + url
            webbrowser.open(url)
            return f"Opening {url}"

        # ── Screenshot ──────────────────────────────────────────────────────
        if d == 'screenshot':
            return _take_screenshot()

        # ── Volume ──────────────────────────────────────────────────────────
        if d.startswith('volume up'):
            n = _extract_number(d) or 10
            return _adjust_volume(n)

        if d.startswith('volume down'):
            n = _extract_number(d) or 10
            return _adjust_volume(-n)

        if d.startswith('set_volume '):
            n = _extract_number(d) or 50
            return _set_volume_abs(n)

        if d in ('mute', 'unmute'):
            return _toggle_mute()

        # ── Time / Date ─────────────────────────────────────────────────────
        if d == 'get_time':
            return datetime.datetime.now().strftime("The time is %I:%M %p.")

        if d == 'get_date':
            return datetime.datetime.now().strftime("Today is %A, %B %d, %Y.")

        # ── Battery ─────────────────────────────────────────────────────────
        if d == 'battery':
            bat = psutil.sensors_battery()
            if bat:
                pct     = bat.percent
                plugged = bat.power_plugged
                secs    = bat.secsleft
                if plugged:
                    return f"Battery at {pct:.0f}% and currently charging."
                mins = secs // 60 if secs > 0 else 0
                t    = f", about {mins} minutes remaining" if mins else ""
                return f"Battery at {pct:.0f}%{t}."
            return "No battery detected. This appears to be a desktop PC."

        # ── System info ─────────────────────────────────────────────────────
        if d == 'system_info':
            cpu  = psutil.cpu_percent(interval=0.5)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            bat  = psutil.sensors_battery()
            bat_str = f", battery at {bat.percent:.0f}%" if bat else ""
            return (f"CPU at {cpu:.0f}%, "
                    f"RAM {ram.percent:.0f}% used "
                    f"({ram.used // 1024**3}GB of {ram.total // 1024**3}GB), "
                    f"disk {disk.percent:.0f}% used{bat_str}.")

        # ── Lock screen ─────────────────────────────────────────────────────
        if d == 'lock':
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Screen locked."

        # ── Shutdown ────────────────────────────────────────────────────────
        if d == 'shutdown':
            os.system("shutdown /s /t 10")
            return "Shutting down in 10 seconds."

        # ── Restart ─────────────────────────────────────────────────────────
        if d == 'restart':
            os.system("shutdown /r /t 10")
            return "Restarting in 10 seconds."

        # ── Create note ─────────────────────────────────────────────────────
        if d.startswith('create_note '):
            content = decision[12:].strip()
            nid = _save_note(content)
            return f"Note saved."

        # ── Set reminder ────────────────────────────────────────────────────
        if d.startswith('set_reminder '):
            raw    = decision[13:].strip()
            parts  = raw.split('|', 1)
            msg    = parts[0].strip()
            tspec  = parts[1].strip() if len(parts) > 1 else 'in 5 minutes'
            return _schedule_reminder(msg, tspec)

        # ── Calling ─────────────────────────────────────────────────────────
        if d.startswith('call '):
            name = decision[5:].strip()
            return _make_call(name)

        # ── Fallback: try opening as app ────────────────────────────────────
        callback(f"[Automation] Unknown decision: '{decision}', attempting open...")
        return _open_app(d)

    except Exception as e:
        err = f"Action failed: {e}"
        callback(f"[Automation] Exception: {e}")
        return err


# ── Helper functions ──────────────────────────────────────────────────────────


def _play_spotify(query: str) -> str:
    """
    Play a song/artist/playlist on Spotify.
    Strategy:
      1. Use Spotipy (Official API) to find the exact track/album/artist URI.
      2. Open the URI directly via OS (spotify:track:<id>), which is 100% reliable.
      3. Falls back to keyword-based URI or browser if API keys missing.
    """
    import threading, os, webbrowser, re
    from random import choice as _choice

    # Handle random/vague queries
    random_triggers = ['any', 'any music', 'some music', 'a song', 'whichever',
                       'random', 'phir se', 'whatever', 'something']
    if not query or any(t in query.lower() for t in random_triggers):
        query = _choice(['Top Hits 2024', 'Lofi Chill', 'Pop Mix',
                         'Chill Vibes', 'Bollywood Hits', 'Global Top 50'])

    query = re.sub(r'\s+(song|music|track)$', '', query, flags=re.IGNORECASE).strip()

    def _open_and_play():
        try:
            client_id = os.environ.get('SPOTIPY_CLIENT_ID')
            client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET')
            redirect_uri = os.environ.get('SPOTIPY_REDIRECT_URI')

            if client_id and client_secret and "your_client_id" not in client_id:
                try:
                    import spotipy
                    from spotipy.oauth2 import SpotifyClientCredentials
                    
                    auth_manager = SpotifyClientCredentials(
                        client_id=client_id,
                        client_secret=client_secret
                    )
                    sp = spotipy.Spotify(auth_manager=auth_manager)
                    
                    results = sp.search(q=query, limit=1, type='track')
                    if results['tracks']['items']:
                        track_uri = results['tracks']['items'][0]['uri']
                        print(f"[Automation] Spotify API found URI: {track_uri}")
                        os.startfile(track_uri) # Direct URI launch is most reliable for desktop
                        return
                except Exception as e:
                    print(f"[Automation] Spotipy search failed: {e}")

            # Fallback 1: Use spotify:search:<query> URI
            print(f"[Automation] Spotify API blocked (requires Premium). Using Desktop Search fallback for: {query}")
            os.startfile(f"spotify:search:{query}")
            
            # Automated playback attempt for Free users
            import time
            try:
                import pygetwindow as gw
                import pyautogui
                
                # Wait up to 5 seconds for Spotify to appear
                for _ in range(10):
                    time.sleep(0.5)
                    windows = [w for w in gw.getWindowsWithTitle('Spotify') if w.title == 'Spotify']
                    if windows:
                        win = windows[0]
                        try:
                            if not win.isActive:
                                win.activate()
                        except: pass
                        
                        # Wait for search results to load from the internet
                        time.sleep(2.5) 
                        
                        # In Spotify, pressing Tab moves focus from the search bar to the results
                        pyautogui.press('tab')
                        time.sleep(0.2)
                        pyautogui.press('tab')
                        time.sleep(0.2)
                        pyautogui.press('enter') # Play Top Result
                        
                        print("[Automation] Attempted to trigger playback via keyboard navigation.")
                        return
            except Exception as e:
                print(f"[Automation] Keyboard fallback failed: {e}")

        except Exception:
            webbrowser.open(f"https://open.spotify.com/search/{query.replace(' ', '%20')}")

    threading.Thread(target=_open_and_play, daemon=True).start()
    return f"Playing {query} on Spotify."


def _open_app(name: str) -> str:

    key = name.lower().strip()
    exe = APP_MAP.get(key)

    if exe:
        if isinstance(exe, str) and (exe.startswith('http') or exe.startswith('whatsapp:')):
            if exe.startswith('http'):
                webbrowser.open(exe)
            else:
                os.startfile(exe)
            return f"Opening {name}."
        try:
            # Use 'start' in Windows to properly locate and launch the exe/app
            subprocess.Popen(f'start "" "{exe}"', shell=True)
            return f"Opening {name}."
        except Exception as e:
            pass  # Fall through to AppOpener

    # Try AppOpener (handles most installed apps)
    try:
        import AppOpener
        AppOpener.open(name, match_closest=True, output=False)
        return f"Opening {name}."
    except Exception:
        pass

    # Direct shell execution
    try:
        subprocess.Popen(name, shell=True)
        return f"Trying to open {name}."
    except Exception as e:
        return f"Could not open '{name}'. Make sure it's installed."


def _close_app(name: str) -> str:
    key  = name.lower().strip()
    exe  = APP_MAP.get(key, name)
    
    # Check if it's a known URL/PWA
    if isinstance(exe, str) and exe.startswith('http'):
        # For URLs we cannot simply taskkill the browser, but we can try AppOpener's fuzzy close
        # or just fallback to browser kill if user specifically said close perplexity
        try:
            import AppOpener
            AppOpener.close(key, match_closest=True, output=False)
            return f"Attempted to close {name}."
        except:
            return f"Could not easily close website/PWA: {name}. Please close the tab manually."

    proc = os.path.basename(exe)

    # taskkill by image name
    r = subprocess.run(['taskkill', '/F', '/IM', proc], capture_output=True, text=True)
    if r.returncode == 0:
        return f"{name} closed."

    # Fuzzy process search
    killed = False
    for p in psutil.process_iter(['name', 'pid']):
        try:
            p_name = p.info['name'].lower()
            if key in p_name and p_name not in ['cmd.exe', 'powershell.exe', 'explorer.exe']:
                p.kill()
                killed = True
        except Exception:
            pass
            
    if killed:
        return f"{name} terminated."

    # AppOpener close
    try:
        import AppOpener
        AppOpener.close(name, match_closest=True, output=False)
        return f"Closed {name}."
    except Exception:
        pass

    return f"Could not find '{name}' running."

def _exit_eklavya() -> str:
    import eel
    try: eel.js_state("Offline")()
    except: pass
    import time, sys
    time.sleep(1)
    os._exit(0)


def _take_screenshot() -> str:
    ts  = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(os.path.expanduser('~'), 'Desktop', f'screenshot_{ts}.png')
    try:
        if _PIL:
            img = ImageGrab.grab()
        elif _pag:
            img = _pag.screenshot()
        else:
            import pyautogui
            img = pyautogui.screenshot()
        img.save(dst)
        return f"Screenshot saved to Desktop: screenshot_{ts}.png"
    except Exception as e:
        return f"Screenshot failed: {e}"


def _adjust_volume(delta: int) -> str:
    if _vol_interface:
        try:
            current = int(_vol_interface.GetMasterVolumeLevelScalar() * 100)
            new_vol = max(0, min(100, current + delta))
            _vol_interface.SetMasterVolumeLevelScalar(new_vol / 100, None)
            direction = 'increased' if delta > 0 else 'decreased'
            return f"Volume {direction} to {new_vol}%."
        except Exception as e:
            return f"Volume adjust error: {e}"
    # Keyboard fallback
    import pyautogui
    key = 'volumeup' if delta > 0 else 'volumedown'
    for _ in range(abs(delta) // 2):
        pyautogui.press(key)
    return f"Volume {'increased' if delta > 0 else 'decreased'}."


def _set_volume_abs(level: int) -> str:
    level = max(0, min(100, level))
    if _vol_interface:
        try:
            _vol_interface.SetMasterVolumeLevelScalar(level / 100, None)
            return f"Volume set to {level}%."
        except Exception as e:
            return f"Volume set error: {e}"
    return f"Volume control unavailable. Tried to set {level}%."


def _toggle_mute() -> str:
    if _vol_interface:
        try:
            muted = _vol_interface.GetMute()
            _vol_interface.SetMute(not muted, None)
            return "Muted." if not muted else "Unmuted."
        except Exception as e:
            return f"Mute error: {e}"
    import pyautogui
    pyautogui.press('volumemute')
    return "Toggled mute."


def _extract_number(text: str) -> int | None:
    m = re.search(r'\d+', text)
    return int(m.group()) if m else None


def _save_note(content: str) -> int:
    notes = []
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, 'r') as f:
                notes = json.load(f)
        except Exception:
            notes = []
    notes.append({'id': len(notes) + 1,
                  'ts': datetime.datetime.now().isoformat(),
                  'content': content})
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f, indent=2)
    return notes[-1]['id']


def _schedule_reminder(message: str, time_str: str) -> str:
    """Parse and schedule a reminder. Stores to reminders.json."""
    import threading

    remind_at = _parse_time(time_str)
    if remind_at is None:
        return f"Couldn't parse time '{time_str}'. Try 'in 5 minutes' or '14:30'."

    delay = (remind_at - datetime.datetime.now()).total_seconds()
    if delay <= 0:
        return f"That time has already passed."

    def _fire():
        import time
        time.sleep(delay)
        from Backend.TTS import TTS
        TTS(f"Reminder: {message}")
        print(f"[REMINDER] 🔔 {message}")

    t = threading.Thread(target=_fire, daemon=True)
    t.start()

    friendly = remind_at.strftime('%I:%M %p')
    return f"Reminder set for {friendly}: {message}"


def _parse_time(s: str) -> datetime.datetime | None:
    s   = s.lower().strip()
    now = datetime.datetime.now()

    m = re.search(r'in\s+(\d+)\s+min', s)
    if m:
        return now + datetime.timedelta(minutes=int(m.group(1)))

    m = re.search(r'in\s+(\d+)\s+hour', s)
    if m:
        return now + datetime.timedelta(hours=int(m.group(1)))

    m = re.search(r'in\s+(\d+)\s+sec', s)
    if m:
        return now + datetime.timedelta(seconds=int(m.group(1)))

    for fmt in ['%H:%M', '%I:%M %p', '%I:%M%p', '%I %p']:
        try:
            t  = datetime.datetime.strptime(s, fmt)
            dt = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if dt <= now:
                dt += datetime.timedelta(days=1)
            return dt
        except ValueError:
            pass

    return None

def _send_whatsapp_message(name: str, message: str) -> str:
    contacts_file = 'contacts.json'
    contacts = {}
    if os.path.exists(contacts_file):
        try:
            with open(contacts_file, 'r') as f:
                contacts = json.load(f)
        except Exception:
            pass
    
    target_num = None
    for k, v in contacts.items():
        if name.lower() in k.lower():
            target_num = str(v)
            break
            
    if not target_num:
        return f"I don't have {name}'s number in your contacts configuration file."
        
    try:
        import urllib.parse
        import threading
        
        # Clean the target number
        clean_num = ''.join(c for c in target_num if c.isdigit() or c == '+')
        
        def _send():
            import time, pyautogui, os
            try:
                print(f"[Automation] Opening WhatsApp desktop for {clean_num}: {message}")
                encoded_msg = urllib.parse.quote(message)
                url = f"whatsapp://send?phone={clean_num}&text={encoded_msg}"
                os.startfile(url)
                
                # Wait for WhatsApp Desktop to open and load the chat securely
                time.sleep(8)
                pyautogui.press('enter')
                print("[Automation] Message sent via WhatsApp Desktop.")
            except Exception as e:
                print(f"[Automation] WhatsApp desktop error: {e}")

        t = threading.Thread(target=_send, daemon=True)
        t.start()
        return f"Opening WhatsApp to message {name}."
    except Exception as e:
        return f"Failed to prepare WhatsApp message: {e}"
def _make_call(name: str) -> str:
    contacts_file = 'contacts.json'
    contacts = {}
    if os.path.exists(contacts_file):
        try:
            with open(contacts_file, 'r') as f:
                contacts = json.load(f)
        except Exception:
            pass
    
    target_num = None
    for k, v in contacts.items():
        if name.lower() in k.lower():
            target_num = str(v)
            break
            
    if not target_num:
        return f"I don't have {name}'s number in your contacts configuration file."
        
    try:
        # Clean the target number
        clean_num = ''.join(c for c in target_num if c.isdigit() or c == '+')
        print(f"[Automation] Dialing {name}: {clean_num}")
        
        # 'tel:' protocol triggers the default Windows dialer (Phone Link / Skype)
        os.startfile(f"tel:{clean_num}")
        return f"Initiating call to {name}."
    except Exception as e:
        return f"Failed to initiate call: {e}"
