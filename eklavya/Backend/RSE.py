"""
Backend/RSE.py
Real-time Search Engine — DuckDuckGo search + Groq for fast synthesis
Used for: weather, news, stock prices, current events, live scores,
          political leaders, recent elections — anything with a knowledge cutoff.
Now supports user_id for full conversation history persistence.
"""

import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq
from Backend.Extra import SaveMessage

load_dotenv()
GROQ_API_KEY   = os.environ.get('GroqAPI', '')
ASSISTANT_NAME = os.environ.get('AssistantName', 'Eklavya')
USERNAME       = os.environ.get('NickName', 'Admin')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}


def _search_ddg(query: str, max_results: int = 5) -> str:
    """Scrape DuckDuckGo HTML search for snippets."""
    try:
        url  = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        resp = requests.get(url, headers=HEADERS, timeout=7)
        soup = BeautifulSoup(resp.text, 'html.parser')

        snippets = []
        for item in soup.select('.result__body')[:max_results]:
            title   = item.select_one('.result__title')
            snippet = item.select_one('.result__snippet')
            if snippet:
                t = title.get_text(strip=True)   if title   else ''
                s = snippet.get_text(strip=True)
                snippets.append(f"{t}: {s}" if t else s)

        return '\n'.join(snippets)
    except Exception as e:
        print(f"[RSE] DuckDuckGo search error: {e}")
        return ""


def _search_google_news(query: str) -> str:
    """Try Google News as alternative source."""
    try:
        url  = f"https://news.google.com/search?q={query.replace(' ', '+')}&hl=en"
        resp = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(resp.text, 'html.parser')

        headlines = []
        for article in soup.select('article')[:5]:
            h3 = article.select_one('h3, h4')
            if h3:
                headlines.append(h3.get_text(strip=True))

        return '\n'.join(headlines)
    except Exception:
        return ""


def RealTimeChatBotAI(query: str, user_id: int = None, session_id: str = 'default') -> str:
    """
    Search the web for current information and use Groq to synthesize a natural spoken answer.
    Properly saves conversation with user_id and session_id for history persistence.
    """
    print(f"[RSE] Searching for: '{query}'")

    # Get search results
    search_data = _search_ddg(query)
    if not search_data:
        search_data = _search_google_news(query)
        if not search_data:
            print("[RSE] No search results found.")

    try:
        client = Groq(api_key=GROQ_API_KEY)

        # Build system context
        system = f"""You are {ASSISTANT_NAME}, a smart AI assistant giving real-time information.
Use the provided search results to answer accurately with UP-TO-DATE information.
Speak naturally and concisely — your answer will be read aloud.
No markdown. No bullet points. Use plain conversational sentences.
If the search results contain current information, use it and state it confidently.
If unsure, acknowledge it honestly.
Address the user as {USERNAME}."""

        user_content = query
        if search_data:
            user_content = (
                f"User question: {query}\n\n"
                f"Current web search results:\n{search_data}\n\n"
                f"Based on these CURRENT search results, give a concise spoken answer. "
                f"Be confident if the results clearly answer the question."
            )

        response = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[
                {"role": "system",  "content": system},
                {"role": "user",    "content": user_content},
            ],
            max_tokens=350,
            temperature=0.4,
        )

        answer = response.choices[0].message.content.strip()
        SaveMessage('user',      query,  user_id=user_id, session_id=session_id)
        SaveMessage('assistant', answer, user_id=user_id, session_id=session_id)
        return answer

    except Exception as e:
        print(f"[RSE] Groq synthesis error: {e}")
        # Fallback to Gemini
        try:
            from Backend.Chatbot import ChatBotAI
            return ChatBotAI(query, user_id=user_id, session_id=session_id)
        except Exception:
            err = f"I had trouble searching for that right now, {USERNAME}. Please try again."
            SaveMessage('user',      query, user_id=user_id, session_id=session_id)
            SaveMessage('assistant', err,   user_id=user_id, session_id=session_id)
            return err
