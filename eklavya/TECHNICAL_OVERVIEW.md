# Technical Documentation: Eklavya AI Assistant

## 🚀 Overview
**Eklavya** is a modular, JARVIS-inspired AI Desktop Assistant built using Python and Eel. It combines intent classification (Regex + LLMs), system-level automation, and multi-model AI logic to provide a seamless voice and text-based interface for Windows OS management and general conversation.

---

## 🏗️ Architecture
Eklavya follows a hybrid architecture combining a high-performance Python backend with a lightweight Chrome-based local web frontend.

### 1. **Core Components**
- **Frontend**: Eel + HTML/CSS/JS (Spider UI).
- **Backend**: Python 3.10+.
- **Database**: SQLite (`eklavya.db`) for user management, preferences, and session persistence.
- **Decision Engine**: `AutoModel.py` — orchestrates query routing.

### 2. **The Execution Pipeline**
1. **Input**: User speaks (Voice via Browser Speech API) or types.
2. **Translation**: Non-English input is translated via `mtranslate`.
3. **Modification**: Queries are normalized (removing filler words like "hey jarvis").
4. **Classification**:
   - **Regex Matcher**: Instant matching for common commands (apps, volume, etc.).
   - **LLM Classifier (Groq)**: Fuzzy classification for ambiguous or complex queries.
5. **Execution**:
   - **Automation**: System actions (apps, music, power) executed via `Automation.py`.
   - **Real-time Search**: Live web synthesis via `RSE.py` (DuckDuckGo + Groq).
   - **General AI**: Conversation via `Chatbot.py` (Gemini Flash → Groq → Ollama chain).
6. **Output**: Resulting text is saved to DB and spoken via `TTS.py` (edge-tts).

---

## 🔧 Subsystems Detailed

### 🤖 Intent Classification (`Backend/AutoModel.py`)
Uses a cascading priority system:
1. **Complex Query Detection**: Identifies "and", "then", etc., to trigger LLM splitting.
2. **Real-time Patterns**: Hardcoded regex for news, weather, and politics to ensure up-to-date data routing.
3. **Action Patterns**: Regex for system controls (e.g., `open *`, `volume up *`).
4. **LLM Fallback**: Sends the query to `llama-3.1-8b-instant` on Groq for a structured intent response in ~300ms.

### 🛠️ Automation System (`Backend/Automation.py`)
- **App Management**: Opens/Closes apps via an internal `APP_MAP` or fuzzy matching with `AppOpener`.
- **System Control**: `psutil` for stats, `pycaw` for volume, `pyautogui` for media keys/typing.
- **Media**: Precise Spotify control via Spotipy API (searching URIs) and YouTube searches.
- **Social**: WhatsApp messaging using `whatsapp://` URI and GUI automation.
- **Persistence**: Notes and temporary reminders using JSON and async threads.

### 💬 AI & Knowledge (`Backend/Chatbot.py` & `RSE.py`)
- **Default (Gemini)**: Uses `gemini-1.5-flash` for high-speed, cost-effective reasoning.
- **Offline (Ollama)**: Local Llama 3/Mistral fallback for privacy and connectivity-loss scenarios.
- **RSE (Search)**: Scrapes DuckDuckGo and uses LLM to synthesize fresh information (bypasses training knowledge cutoffs).

### 🗄️ Database Schema
- **`users`**: Encrypted credentials (bcrypt/PBKDF2).
- **`conversations`**: Full chat history with user-specific session IDs.
- **`preferences`**: Key-value store for individual user settings (AI mode, voices).
- **`sessions`**: Secure tokens for "Remember Me" functionality.

---

## 🛠️ Tech Stack
| Category | Technology |
| :--- | :--- |
| **Language** | Python 3.10+, JavaScript |
| **Framework** | Eel (WebSocket bridge) |
| **Speech** | Browser Speech API (STT), edge-tts (TTS) |
| **AI APIs** | Google Gemini 1.5, Groq (Llama 3.1), Ollama |
| **Database** | SQLite 3 |
| **Utilities** | psutil, pycaw, pyautogui, AppOpener, Spotipy |

---

## 📈 Database Viewer
The project includes a standalone utility `db_viewer.py` to inspect and manage the SQLite database via a clean interface.
