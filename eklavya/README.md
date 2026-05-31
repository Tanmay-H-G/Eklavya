# Eklavya AI Assistant
AI desktop assistant built with Python, Gemini AI, Groq LLMs, voice recognition, automation, and real-time web search.

## Features
* Voice-controlled AI assistant
* Gemini AI integration
* Groq LLM fallback
* Real-time web search
* Windows automation
* Text-to-speech responses
* System monitoring
* Notes and reminders

## Screenshots
### Home Screen
![Home Screen](Assets/home-screen.png) 

## Demo Video

(Add YouTube demo link)

## Technologies Used

* Python
* Gemini API
* Groq API
* Eel
* Edge-TTS
* PyAudio
* DuckDuckGo Search
* WMI
* SQLite

## Installation

(paste your existing installation steps)

## Project Structure
eklavya/
│
├── main.py                  ← ENTRY POINT — run this
├── .env                     ← Your API keys (EDIT THIS)
├── requirements.txt         ← pip packages
├── install.bat              ← Windows auto-installer
├── ChatLog.json             ← Auto-created: conversation history
├── notes.json               ← Auto-created: saved notes
│
├── Backend/
│   ├── __init__.py          ← Package marker
│   ├── AutoModel.py         ← Query classifier (pattern match + Groq)
│   ├── Chatbot.py           ← Gemini 1.5 Flash — general conversation
│   ├── ChatGpt.py           ← Groq Llama 3.1 — fast AI + Gemini fallback
│   ├── RSE.py               ← Real-time search (DuckDuckGo + Groq synthesis)
│   ├── Automation.py        ← All Windows OS actions
│   ├── TTS.py               ← edge-tts (neural) + pyttsx3 (fallback)
│   ├── Extra.py             ← Message helpers, formatters, file I/O
│   └── StatsPusher.py       ← Pushes CPU/RAM/battery to UI every 8s
│
└── web/
    ├── spider.html          ← Full premium UI (HTML/CSS/JS)
    └── eel.js               ← WebSocket bridge (do not edit)

## Voice Commands

(paste your existing commands section)

## License
MIT License


## ⚡ How to Run

### Step 1 — Prerequisites
- **Python 3.10+** → https://python.org/downloads (check "Add to PATH")
- **Google Chrome** → must be installed (eel uses it as the UI window)

### Step 2 — Set your API keys
Open `.env` and fill in your keys:
```
GeminiApi=AIza_your_key_here
GroqAPI=gsk_your_key_here
AssistantName=Eklavya
NickName=YourName
AssistantVoice=en-US-BrianNeural
```

| Key | Get it free at |
|-----|---------------|
| `GeminiApi` | https://aistudio.google.com/app/apikey |
| `GroqAPI`   | https://console.groq.com → API Keys |

### Step 3 — Install dependencies
```batch
# Double-click install.bat
# OR manually:
pip install -r requirements.txt
```

If PyAudio fails:
```batch
pip install pipwin
pipwin install pyaudio
```

### Step 4 — Run
python main.py
Chrome opens automatically with the Eklavya UI.

---

## 📁 File Structure (every file explained)

```
eklavya/
│
├── main.py                  ← ENTRY POINT — run this
├── .env                     ← Your API keys (EDIT THIS)
├── requirements.txt         ← pip packages
├── install.bat              ← Windows auto-installer
├── ChatLog.json             ← Auto-created: conversation history
├── notes.json               ← Auto-created: saved notes
│
├── Backend/
│   ├── __init__.py          ← Package marker
│   ├── AutoModel.py         ← Query classifier (pattern match + Groq)
│   ├── Chatbot.py           ← Gemini 1.5 Flash — general conversation
│   ├── ChatGpt.py           ← Groq Llama 3.1 — fast AI + Gemini fallback
│   ├── RSE.py               ← Real-time search (DuckDuckGo + Groq synthesis)
│   ├── Automation.py        ← All Windows OS actions
│   ├── TTS.py               ← edge-tts (neural) + pyttsx3 (fallback)
│   ├── Extra.py             ← Message helpers, formatters, file I/O
│   └── StatsPusher.py       ← Pushes CPU/RAM/battery to UI every 8s
│
└── web/
    ├── spider.html          ← Full premium UI (HTML/CSS/JS)
    └── eel.js               ← WebSocket bridge (do not edit)
```

---

## 💾 Where Data Is Stored

| File | Contents |
|------|----------|
| `ChatLog.json` | All conversations (user + assistant messages) |
| `notes.json`   | Saved notes from "make a note..." commands |
| `.env`         | Your API keys and settings |

---

## 🎤 How to Use

### Voice (two ways)
1. **Wake word** — just say **"Eklavya"** (or "Jarvis"), then your command
2. **Mic button** — click 🎤 in the UI, then speak

> Chrome must allow microphone access. If the yellow banner appears, click "Allow access".

### Text
Type in the bottom bar. Press **Enter** to send.

### Quick chips
Click any suggestion chip on the welcome screen.

---

## 🧠 How Commands Are Processed

```
Your input (voice or text)
         │
         ▼
   Pattern Matcher  ←─── Instant, zero AI, works offline
   (Backend/AutoModel.py)
         │
   Known pattern?
   YES ──►  Execute via Automation.py  ──► Speak result
         │
   NO  ──►  Is it real-time? (weather, news)
              YES ──► RSE.py (DuckDuckGo search + Groq synthesis)
              NO  ──► Chatbot.py (Gemini 1.5 Flash)
                        │ fails? ──► ChatGpt.py (Groq fallback)
```

**Pattern-matched (instant, no AI cost):**
open/close apps · volume up/down/mute · time & date · screenshot ·
battery · system info · lock screen · shutdown · restart ·
Google search · open URLs · YouTube · Spotify · notes · reminders

**Everything else → AI:**
Any question, conversation, explanation, math, coding help, etc.

---

## 🗣️ Voice Commands Reference

| Say | What happens |
|-----|-------------|
| "Eklavya, open Chrome" | Launches Chrome |
| "Eklavya, close Spotify" | Kills Spotify process |
| "Eklavya, what time is it?" | Tells the time instantly |
| "Eklavya, take a screenshot" | Saves PNG to Desktop |
| "Eklavya, volume up 20" | Raises volume 20% |
| "Eklavya, mute" | Mutes system audio |
| "Eklavya, battery status" | Reads battery level |
| "Eklavya, system status" | CPU/RAM/Disk report |
| "Eklavya, search Python tutorials" | Google search opens |
| "Eklavya, play lofi on YouTube" | YouTube search opens |
| "Eklavya, play Drake on Spotify" | Spotify search opens |
| "Eklavya, lock the screen" | Locks Windows |
| "Eklavya, shutdown" | Shuts down in 10s |
| "Eklavya, make a note: call doctor" | Saves note |
| "Eklavya, remind me to eat in 30 minutes" | Reminder |
| "Eklavya, what is quantum computing?" | Full AI response |
| "Eklavya, what's the weather in Mumbai?" | Live web search |
| "Eklavya, who won the IPL 2024?" | Real-time search |

---

## ⚙️ Settings (.env)

| Variable | Default | What it does |
|----------|---------|-------------|
| `AssistantName` | `Eklavya` | Name shown in UI + wake word |
| `NickName` | `Admin` | How the AI addresses you |
| `AssistantVoice` | `en-US-BrianNeural` | Microsoft neural TTS voice |
| `InputLanguage` | `en` | Your language (auto-translates if not English) |

### Other Neural Voices
| Voice | Style |
|-------|-------|
| `en-US-BrianNeural` | American male (clear, professional) |
| `en-GB-RyanNeural`  | British male (very JARVIS-like!) |
| `en-US-AndrewNeural`| American male (warm) |
| `en-US-JennyNeural` | American female |
| `en-IN-NeerjaNeural`| Indian English female |

---

## 🔧 Troubleshooting

**Chrome doesn't open / black window**
```batch
pip install eel --upgrade
```
Make sure Google Chrome is installed at the default location.

**"PyAudio not found"**
```batch
pip install pipwin && pipwin install pyaudio
```

**Mic not working / yellow banner in UI**
- Chrome asks for mic permission — click Allow when prompted
- Or go to: chrome://settings/content/microphone → Allow localhost

**"Gemini API error"**
- Check your key in `.env` — no quotes, no spaces
- Visit: https://aistudio.google.com to check quota

**"Groq error"**
- Get a free key at: https://console.groq.com
- Paste it in `.env` as `GroqAPI=gsk_...`

**Volume control not working**
```batch
pip install pycaw comtypes
```

**pycaw fails on install**
Volume will automatically fall back to keyboard keys (still works).

**App "open X" not working**
Add the app to `APP_MAP` in `Backend/Automation.py`:
```python
'my app': 'myapp.exe',
```

---

## 🆓 Free API Tier Limits

| Service | Free limit |
|---------|-----------|
| Gemini 1.5 Flash | 1,500 requests/day, 15/min |
| Groq (Llama 3.1) | 14,400 requests/day, 30/min |
| edge-tts | Unlimited (Microsoft's service) |
| DuckDuckGo search | Unlimited |

For personal daily use you will never come close to hitting any limit.

---

## 🔑 Which API Does What

| Module | API Used | Purpose |
|--------|----------|---------|
| `Chatbot.py` | Gemini 1.5 Flash | General conversation, questions |
| `ChatGpt.py` | Groq Llama-3.1 | Fast responses + Gemini fallback |
| `RSE.py`      | DuckDuckGo + Groq | Real-time info (weather, news) |
| `AutoModel.py`| Groq (for ambiguous queries) | Query classification |
| `TTS.py`      | edge-tts / pyttsx3 | Voice output |
