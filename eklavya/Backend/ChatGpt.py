"""
Backend/ChatGpt.py
Fast conversation using Groq API (Llama 3.1 — very low latency)
Used as: primary fast AI OR fallback when Gemini is unavailable
Now supports user_id for persistent conversation history.
"""

import os
from dotenv import load_dotenv
from groq import Groq
from Backend.Extra import LoadMessages, SaveMessage

load_dotenv()
GROQ_API_KEY   = os.environ.get('GroqAPI', '')
ASSISTANT_NAME = os.environ.get('AssistantName', 'Eklavya')
USERNAME       = os.environ.get('NickName', 'Admin')

SYSTEM_PROMPT = f"""You are {ASSISTANT_NAME}, a smart and concise AI assistant like JARVIS.
Be helpful, direct, and natural. Address the user as {USERNAME}.
Your responses will be spoken aloud, so use plain text — no markdown, no bullet points.
Keep responses brief (1-3 sentences) unless the question clearly needs detail."""


def ChatBotAI(query: str, user_id: int = None) -> str:
    """
    Fast AI response using Groq (Llama-3.1-8b-instant).
    Typically responds in under 1 second.
    Supports user_id for per-user conversation history.
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)

        # Build message history — use user's DB history if available
        history = LoadMessages(user_id=user_id) if user_id else LoadMessages()

        system_msg = [{"role": "system", "content": SYSTEM_PROMPT}]
        history_msgs = []
        for msg in history[-10:]:    # Last 5 exchanges
            role    = msg.get('role', 'user')
            content = msg.get('content', '').strip()
            if not content:
                continue
            api_role = 'assistant' if role == 'assistant' else 'user'
            history_msgs.append({"role": api_role, "content": content})

        history_msgs.append({"role": "user", "content": query})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=system_msg + history_msgs,
            max_tokens=400,
            temperature=0.7,
        )

        answer = response.choices[0].message.content.strip()
        SaveMessage('user',      query,  user_id=user_id)
        SaveMessage('assistant', answer, user_id=user_id)
        return answer

    except Exception as e:
        print(f"[ChatGpt/Groq] Error: {e}")
        err = f"I ran into a connection issue, {USERNAME}. Please try again."
        SaveMessage('user',      query,  user_id=user_id)
        SaveMessage('assistant', err,    user_id=user_id)
        return err
