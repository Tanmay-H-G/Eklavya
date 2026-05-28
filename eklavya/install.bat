@echo off
title Eklavya JARVIS - Installer
color 0b
echo.
echo  ============================================
echo   Eklavya JARVIS  ^|  Windows Setup
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Download Python 3.10+ from https://python.org
    pause & exit /b 1
)
python --version

echo.
echo  [1/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo  [2/5] Installing main packages...
pip install -r requirements.txt

echo  [3/5] PyAudio (microphone - may need special install)...
pip install pyaudio >nul 2>&1
if errorlevel 1 (
    echo  Trying pipwin fallback...
    pip install pipwin --quiet
    pipwin install pyaudio
)

echo  [4/5] pycaw (Windows volume control)...
pip install pycaw comtypes --quiet

echo  [5/5] Verifying eel...
pip install eel --quiet

echo.
echo  ============================================
echo   Done! Now set your .env file:
echo.
echo   GeminiApi=YOUR_KEY_HERE
echo   GroqAPI=YOUR_GROQ_KEY_HERE
echo   AssistantName=Eklavya
echo   NickName=Admin
echo   AssistantVoice=en-US-BrianNeural
echo.
echo   Get Gemini key FREE: aistudio.google.com
echo   Get Groq key FREE:   console.groq.com
echo.
echo   Then run:  python main.py
echo  ============================================
echo.
pause
