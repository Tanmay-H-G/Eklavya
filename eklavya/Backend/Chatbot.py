"""
Backend/Chatbot.py
General conversation AI — supports Gemini, Groq, or Ollama based on user-selected mode.
No more auto online/offline detection — mode is chosen by the user in the UI.
Full conversation history via user_id → Database.py.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from Backend.Extra import LoadMessages, SaveMessage

load_dotenv()
GEMINI_API_KEY = os.environ.get('GeminiApi', '')
ASSISTANT_NAME = os.environ.get('AssistantName', 'Eklavya')
USERNAME       = os.environ.get('NickName', 'Admin')

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = f"""You are {ASSISTANT_NAME}, a smart and concise AI assistant like JARVIS.
Be helpful, direct, and natural. Address the user as {USERNAME}.
Your responses will be spoken aloud, so use plain text — no markdown, no bullet points.
Keep responses brief (1-3 sentences) unless the question clearly needs detail.
You maintain full context of the ongoing conversation."""


def ChatBotAI(query: str, user_id: int = None, mode: str = 'gemini', session_id: str = 'default') -> str:
    """
    Send a query to the AI model specified by 'mode'.
    mode: 'gemini' | 'groq' | 'ollama'
    Loads full conversation history from DB for context continuity.
    """
    # Load history from DB (or JSON fallback if no user_id)
    history = LoadMessages(user_id=user_id, session_id=session_id) if user_id else LoadMessages()
    print(f"[Chatbot] Mode={mode} | History={len(history)} msgs | User={user_id} | Session={session_id}")

    # ── Route by mode ─────────────────────────────────────────────
    if mode == 'ollama':
        return _use_ollama(query, history, user_id, session_id)
    elif mode == 'groq':
        return _use_groq(query, history, user_id, session_id)
    else:
        # Default: Gemini with Groq → Ollama fallback chain
        return _use_gemini(query, history, user_id, session_id)


# ── Gemini ────────────────────────────────────────────────────────────────────

def _use_gemini(query: str, history: list, user_id: int, session_id: str) -> str:
    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=512,
                temperature=0.75,
                top_p=0.95,
            )
        )

        gemini_history = []
        for msg in history[-20:]:   # last 10 exchanges for context
            role    = 'user' if msg.get('role') == 'user' else 'model'
            content = msg.get('content', '').strip()
            if content:
                gemini_history.append({'role': role, 'parts': [content]})

        chat     = model.start_chat(history=gemini_history)
        response = chat.send_message(query)
        answer   = response.text.strip()

        SaveMessage('user',      query,  user_id=user_id, session_id=session_id)
        SaveMessage('assistant', answer, user_id=user_id, session_id=session_id)
        return answer

    except Exception as e:
        print(f"[Chatbot] Gemini failed: {e} — falling back to Groq")
        return _use_groq(query, history, user_id, session_id)


# ── Groq ──────────────────────────────────────────────────────────────────────

def _use_groq(query: str, history: list, user_id: int, session_id: str) -> str:
    try:
        from Backend.ChatGpt import ChatBotAI as GroqChat
        # ChatGpt.py already handles save, so just call and return
        # But we need to avoid double-saving — call the Groq client directly
        from groq import Groq
        client = Groq(api_key=os.environ.get('GroqAPI', ''))

        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-20:]:
            role    = msg.get('role', 'user')
            content = msg.get('content', '').strip()
            if content:
                msgs.append({"role": 'assistant' if role == 'assistant' else 'user', "content": content})
        msgs.append({"role": "user", "content": query})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=msgs,
            max_tokens=400,
            temperature=0.7,
        )
        answer = response.choices[0].message.content.strip()
        SaveMessage('user',      query,  user_id=user_id, session_id=session_id)
        SaveMessage('assistant', answer, user_id=user_id, session_id=session_id)
        return answer

    except Exception as e:
        print(f"[Chatbot] Groq failed: {e} — falling back to Ollama")
        return _use_ollama(query, history, user_id, session_id)


# ── Ollama (Offline) ──────────────────────────────────────────────────────────

def _use_ollama(query: str, history: list, user_id: int, session_id: str) -> str:
    try:
        from Backend.Ollama import OllamaChat
        answer = OllamaChat(query, history[-20:])
        SaveMessage('user',      query,  user_id=user_id, session_id=session_id)
        SaveMessage('assistant', answer, user_id=user_id, session_id=session_id)
        return answer
    except Exception as e:
        print(f"[Chatbot] Ollama failed: {e}")
        err = "I'm having trouble connecting to any AI model right now. Please check your connection."
        SaveMessage('user',      query, user_id=user_id, session_id=session_id)
        SaveMessage('assistant', err,   user_id=user_id, session_id=session_id)
        return err
