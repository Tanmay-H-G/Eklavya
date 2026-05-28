"""
Backend/TTS.py
Text-to-Speech:
  Primary  → edge-tts  (Microsoft Azure Neural, en-US-BrianNeural)
  Fallback → pyttsx3   (Windows built-in, offline)
"""

import asyncio
import os
import time
import tempfile
import threading
from dotenv import load_dotenv

load_dotenv()
VOICE = os.environ.get('AssistantVoice', 'en-US-BrianNeural')

# Pygame init once
_pygame_ready = False
try:
    import pygame
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=2048)
    pygame.mixer.init()
    _pygame_ready = True
except Exception as e:
    print(f"[TTS] pygame init warning: {e}")


def TTS(text: str):
    """
    Speak text aloud. Tries edge-tts first, falls back to pyttsx3.
    Blocking call — returns when speech is done.
    """
    if not text or not text.strip():
        return

    # Try edge-tts (online, sounds human)
    try:
        _speak_edge(text)
        return
    except Exception as e:
        print(f"[TTS] edge-tts failed ({e}), using pyttsx3 fallback")

    # Fallback: pyttsx3 (offline, robotic but always works)
    _speak_pyttsx3(text)


def _speak_edge(text: str):
    """Microsoft neural TTS — sounds like a real person."""
    import edge_tts

    async def _save_and_play(path: str):
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(path)

    tmp_path = None
    try:
        # Save to temp MP3
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            tmp_path = f.name

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_save_and_play(tmp_path))
        loop.close()

        if not _pygame_ready:
            raise RuntimeError("pygame not available")

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

    finally:
        if tmp_path:
            # Release file before deleting
            try:
                pygame.mixer.music.stop()
                if hasattr(pygame.mixer.music, 'unload'):
                    pygame.mixer.music.unload()
                time.sleep(0.1)
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass


def _speak_pyttsx3(text: str):
    """Windows built-in TTS — always works, sounds robotic."""
    try:
        import pyttsx3
        engine = pyttsx3.init()

        # Prefer David (male) or Zira (female) voice
        voices = engine.getProperty('voices')
        for v in voices:
            if 'david' in v.name.lower() or 'mark' in v.name.lower():
                engine.setProperty('voice', v.id)
                break

        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[TTS] pyttsx3 error: {e}")
