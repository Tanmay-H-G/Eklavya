"""
Backend/Extra.py
Utilities: load/save messages, format AI responses for TTS and GUI
"""

import json
import re
import os
from threading import Lock

import socket
from Backend.Database import load_chats, save_chat

CHATLOG_PATH = 'ChatLog.json'
_file_lock = Lock()


def is_online(host="8.8.8.8", port=53, timeout=2) -> bool:
    """
    Check if the system has internet access using a fast socket connection.
    Timeout is set to 2s to prevent hanging.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.error, Exception):
        return False


def LoadMessages(user_id=None, session_id=None) -> list:
    """Load chat messages from SQL database (falls back to JSON if no user_id)."""
    if user_id is not None:
        return load_chats(user_id, session_id=session_id)
    
    # Legacy JSON fallback
    if not os.path.exists(CHATLOG_PATH):
        return []
    try:
        with open(CHATLOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list): return []
            if session_id:
                # Filter JSON messages by session so 'Clear Chat' works for non-logged-in users
                return [m for m in data if m.get('session_id') == session_id]
            return data
    except Exception:
        return []


def SaveMessage(role: str, content: str, user_id=None, session_id='default'):
    """Save a message to SQL database (or JSON if no user_id)."""
    if user_id is not None:
        save_chat(user_id, role, content, session_id=session_id)
        return

    # Legacy JSON fallback
    with _file_lock:
        # Load all messages to append new one
        if not os.path.exists(CHATLOG_PATH):
            messages = []
        else:
            try:
                with open(CHATLOG_PATH, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            except: messages = []

        new_msg = {'role': role, 'content': content, 'session_id': session_id}
        
        # Deduplicate
        if messages and messages[-1].get('content') == content and messages[-1].get('role') == role:
            return
            
        messages.append(new_msg)
        with open(CHATLOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4, ensure_ascii=False)


def AnswerModifier(answer: str) -> str:
    """
    Clean up AI response for TTS:
    - Remove markdown (bold, italic, headers, code blocks, links)
    - Collapse multiple newlines
    - Strip whitespace
    """
    if not answer:
        return ""

    # Code blocks
    answer = re.sub(r'```[\s\S]*?```', 'Code block omitted.', answer)
    answer = re.sub(r'`([^`]+)`', r'\1', answer)

    # Markdown formatting
    answer = re.sub(r'\*\*(.+?)\*\*', r'\1', answer)
    answer = re.sub(r'\*(.+?)\*',     r'\1', answer)
    answer = re.sub(r'__(.+?)__',     r'\1', answer)
    answer = re.sub(r'_(.+?)_',       r'\1', answer)

    # Headers
    answer = re.sub(r'#{1,6}\s+', '', answer)

    # Links
    answer = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', answer)

    # Bullet points → natural text
    answer = re.sub(r'^\s*[-*•]\s+', '', answer, flags=re.MULTILINE)
    answer = re.sub(r'^\s*\d+\.\s+', '', answer, flags=re.MULTILINE)

    # Collapse whitespace
    answer = re.sub(r'\n{3,}', '\n\n', answer)
    answer = answer.strip()

    return answer


def QueryModifier(query: str) -> str:
    """Clean up user query."""
    return query.strip().capitalize()


def GuiMessagesConverter(messages: list) -> list:
    """Convert raw message dicts to GUI-safe format."""
    result = []
    seen = set()
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role    = msg.get('role', 'user')
        content = msg.get('content', '').strip()
        if not content:
            continue
        # Deduplicate consecutive same-content messages
        key = f"{role}:{content}"
        if key in seen:
            continue
        seen.add(key)
        result.append({'role': role, 'content': content})
    return result
