"""
Backend/AutoModel.py
Query Decision Engine:
  1. Pattern matcher first  → instant, zero AI cost, zero network
  2. Groq classifier        → for ambiguous queries (~0.3s)

Returns a list of decisions, e.g.:
  ['general']             → send to Chatbot.py
  ['realtime']            → send to RSE.py
  ['open chrome']         → send to Automation.py
  ['screenshot']          → send to Automation.py
  ['open chrome', 'play music on spotify']  → multiple actions
"""

import re
import os
from dotenv import load_dotenv

load_dotenv()


# ── Realtime query keywords/patterns ──────────────────────────────────────────
REALTIME_PATTERNS = [
    r'\b(?:weather|temperature|forecast|rain|humid)\b.*\b(?:in|at|for|today|tomorrow)\b',
    r'\b(?:news|headlines|breaking|latest)\b',
    r'\b(?:stock|share price|crypto|bitcoin|ethereum|market)\b',
    r'\b(?:score|match result|who won|live score)\b',
    r'\b(?:currently happening|right now|as of today|this week)\b',
    r"what(?:'s| is) (?:the )?(?:weather|temperature|news)\b",
    r'\b(?:trending|viral|popular right now)\b',

    # ── Political / Leadership (CRITICAL FIX: these have knowledge-cutoff answers) ──
    r'\b(?:who is|who\'s|who are)\b.{0,40}\b(?:president|prime minister|pm|chancellor|king|queen|emperor|vicepresident|vice.president|head of state|leader)\b',
    r'\b(?:current|now|today|latest|new|newly)\b.{0,30}\b(?:president|prime minister|pm|chancellor|ceo|head of)\b',
    r'\b(?:president|prime minister|pm)\b.{0,30}\b(?:of|in)\b.{0,30}\b(?:america|usa|us|india|uk|france|germany|russia|china|japan|pakistan|canada)\b',
    r'\b(?:who(?:\'s| is) (?:the )?(?:new|current|latest))\b',
    r'\b(?:ceo|chief executive|chairman|managing director)\b.{0,40}\b(?:of|at)\b',
    r'\b(?:election result|who won the election|election winner)\b',
    r'\b(?:inauguration|sworn in|took office|came to power)\b',

    # ── Tech / Business current events ───────────────────────────
    r'\b(?:latest (?:iphone|android|samsung|apple|google|microsoft|tesla))\b',
    r'\b(?:new (?:model|version|update|release|product|phone|laptop))\b',
    r'\b(?:just (?:announced|released|launched|revealed))\b',
]

# ── Pure conversation patterns (definitely general AI) ─────────────────────────
GENERAL_PATTERNS = [
    r'^(?:hi+|hello+|hey+|howdy|yo)\b',
    r'^good (?:morning|afternoon|evening|night)\b',
    r"\bhow are you\b",
    r"\bwho are you\b|\bwhat are you\b|\btell me about yourself\b",
    r"^(?:thanks?|thank you|okay|ok|sure|got it|nice|cool|great|awesome)[\.!]?$",
    r"\b(?:tell me a joke|make me laugh|funny)\b",
    r"\b(?:tell me a story|write a poem|create a)\b",
    r"\b(?:explain|what is|what are|how does|how do|why does|why is|define)\b",
    r"\b(?:meaning of|definition of|difference between)\b",
    r"\b(?:can you|could you|would you|please)\b.*\b(?:help|tell|explain|show|teach)\b",
    r"\b(?:calculate|what is \d|solve|equation)\b",
    r"\b(?:recommend|suggest|advise)\b",
    r"^(?:yes|no|maybe|perhaps|not sure)\b",
]

# ── Action patterns: (regex, lambda returning list of decisions) ─────────────
ACTION_PATTERNS = [
    # ── App open ──
    (r'^(?:open|launch|start|run|bring up)\s+(.+?)(?:\s+(?:for me|now|please|app|application))?$',
     lambda m: [f'open {m.group(1).strip().lower()}']),

    # ── App close / Eklavya close ──
    (r'^(?:close|quit|exit|kill|terminate|shut down|stop|bye)$',
     lambda m: ['exit_eklavya']),
    (r'^(?:close|quit|exit|kill|terminate|shut down|stop)\s+(?:eklavya|jarvis|yourself)$',
     lambda m: ['exit_eklavya']),
    (r'^(?:close|quit|exit|kill|terminate|shut down|stop)\s+(?!the\s+computer)(?!pc)(.+?)(?:\s+(?:for me|now|please|app))?$',
     lambda m: [f'close {m.group(1).strip().lower()}']),

    # ── YouTube (explicit) ──
    (r'(?:play|search|watch|find|look up)\s+(.+?)\s+(?:on\s+)?(?:youtube|yt)\b',
     lambda m: [f'play {m.group(1).strip()} on youtube']),

    # ── Spotify (explicit) ──
    (r'(?:play|put on|listen to)\s+(.+?)\s+(?:on\s+)?spotify\b',
     lambda m: [f'play_spotify {m.group(1).strip()}']),

    # ── Generic play (defaults to Spotify) ──
    (r'^play\s+(?!on\s)(.+?)$',
     lambda m: [f'play_spotify {m.group(1).strip()}']),

    # ── Web search ──
    (r'(?:^search|^google)\s+(?:for\s+)?(.+?)(?:\s+on\s+(?:google|the web|internet))?$',
     lambda m: [f'search_web {m.group(1).strip()}']),

    # ── Open URL ──
    (r'(?:open|go to|visit|navigate to)\s+(https?://\S+)',
     lambda m: [f'open_url {m.group(1).strip()}']),

    # ── Quick URL shortcuts ──
    (r'^open youtube$',                    lambda m: ['open_url https://youtube.com']),
    (r'^open (?:google|chrome browser)$',  lambda m: ['open_url https://google.com']),
    (r'^open gmail$',                      lambda m: ['open_url https://mail.google.com']),
    (r'^open github$',                     lambda m: ['open_url https://github.com']),
    (r'^open twitter(?:\s+or\s+x)?$',      lambda m: ['open_url https://twitter.com']),
    (r'^open reddit$',                     lambda m: ['open_url https://reddit.com']),
    (r'^open (?:whatsapp web|whatsapp)$',  lambda m: ['open_url https://web.whatsapp.com']),
    (r'^open netflix$',                    lambda m: ['open_url https://netflix.com']),
    (r'^open chatgpt$',                    lambda m: ['open_url https://chat.openai.com']),
    (r'^open grok$',                       lambda m: ['open_url https://grok.com']),

    # ── Screenshot ──
    (r'(?:take a?\s+)?screenshot|capture(?: my)? screen',
     lambda m: ['screenshot']),

    # ── Volume ──
    (r'(?:volume up|increase(?: the)? volume|(?:turn|make) (?:it |volume )?(?:up|louder))(?:\s+(?:by\s+)?(\d+))?',
     lambda m: [f'volume up {m.group(1) or "10"}']),
    (r'(?:volume down|decrease(?: the)? volume|(?:turn|make) (?:it |volume )?(?:down|quieter|lower|softer))(?:\s+(?:by\s+)?(\d+))?',
     lambda m: [f'volume down {m.group(1) or "10"}']),
    (r'^(?:mute|silence)(?:\s+(?:audio|sound|volume|the))?',
     lambda m: ['mute']),
    (r'^unmute(?:\s+(?:audio|sound|volume))?',
     lambda m: ['unmute']),
    (r'(?:set\s+)?(?:the\s+)?volume\s+(?:to\s+)?(\d+)',
     lambda m: [f'set_volume {m.group(1)}']),

    # ── Time / Date ──
    (r'(?:what(?:\'s| is)(?: the)? time|current time|time (?:is it|now)|tell me the time)',
     lambda m: ['get_time']),
    (r'(?:what(?:\'s| is)(?: the)? date|today(?:\'s date)?|what day (?:is it|is today)|current date)',
     lambda m: ['get_date']),

    # ── System info ──
    (r'(?:battery(?: (?:status|level|life))?|how(?:\'s| is)(?: my)? battery)',
     lambda m: ['battery']),
    (r'(?:system (?:info|status|stats|report)|cpu(?: usage)?|ram(?: usage)?|memory usage)',
     lambda m: ['system_info']),

    # ── Power / OS ──
    (r'(?:lock(?: the)? (?:screen|computer|pc)|lock screen|lock it)',
     lambda m: ['lock']),
    (r'(?:shut ?down|power(?: the)?(?: pc| computer)? off|turn(?: the)? (?:pc|computer) off)',
     lambda m: ['shutdown']),
    (r'(?:restart|reboot)(?: the (?:pc|computer))?',
     lambda m: ['restart']),

    # ── Notes ──
    (r'(?:make|create|add|save|write)(?: a)? note[:\s]+(.+)',
     lambda m: [f'create_note {m.group(1).strip()}']),

    # ── Reminders ──
    (r'(?:remind me(?: to)?|set (?:a )?reminder)\s+(.+?)\s+(?:at|in)\s+(.+)',
     lambda m: [f'set_reminder {m.group(1).strip()}|{m.group(2).strip()}']),

    # ── WhatsApp Messaging ──
    (r'(?:open whatsapp and )?(?:message|whatsapp|send(?: a)? message(?: to)?|msg|dm|text)\s+(.+?)(?:\s+(?:say(?:ing)?|that|with|to|and say)?\s+(.+))?',
     lambda m: [f'send_whatsapp {m.group(1).strip()}|{m.group(2).strip() if m.group(2) else "Hi"}']),

    # ── Media Player Controls ──
    (r'(?:pause|stop|halt)(?: the)? (?:music|song|spotify|video|audio|playback)?',
     lambda m: ['media pause']),
    (r'(?:play|resume|start|unpause)(?: the)? (?:music|song|spotify|video|audio|playback)(?! on)',
     lambda m: ['media play']),
    (r'(?:next|skip)(?: the)? (?:music|song|track|video)?',
     lambda m: ['media next']),
    (r'(?:previous|last|back|go back)(?: the)? (?:music|song|track|video)?',
     lambda m: ['media previous']),

    # ── Calling ──
    (r'(?:call|dial|phone|ring)\s+(.+?)(?:\s+please)?$',
     lambda m: [f'call {m.group(1).strip()}']),
]


def Model(query: str) -> list:
    """
    Classify user query into decision list.
    """
    if not query or not query.strip():
        return ['general']

    q = query.lower().strip()
    q = re.sub(r'^(?:hey\s+|okay\s+|ok\s+)?(?:jarvis|eklavya)[,.]?\s*', '', q).strip()
    if not q:
        return ['general']

    # 1. Multi-intent / Complex query detection (Short-circuit to LLM)
    complex_triggers = [r'\band\b', r'\bthen\b', r'\balso\b', r'\bmeantime\b', r'\bconcurrently\b']
    if any(re.search(p, q) for p in complex_triggers):
        print(f"[AutoModel] Complex query detected, forcing LLM classification.")
        return _llm_classify(query)

    # 2. Realtime check (FIRST — before general, so current events override LLM)
    for pattern in REALTIME_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            print(f"[AutoModel] Realtime pattern matched: {pattern[:50]}")
            return ['realtime']

    # 3. General conversation check
    for pattern in GENERAL_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return ['general']

    # 4. Action patterns
    for pattern, handler in ACTION_PATTERNS:
        m = re.search(pattern, q, re.IGNORECASE)
        if m:
            try:
                result = handler(m)
                if result:
                    if ' ' in result[0] and result[0].count(' ') > 3:
                        continue
                    return result
            except Exception as e:
                print(f"[AutoModel] Pattern handler error: {e}")
                continue

    # 5. Fallback: LLM classifier
    return _llm_classify(query)


def _llm_classify(query: str) -> list:
    """Use Groq for fast classification of ambiguous queries (~300ms)."""
    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get('GroqAPI', ''))

        prompt = """Classify the user command into exactly ONE category per intent. If there are multiple actions, separate them with a '|'.
Reply with ONLY the category string(s), nothing else.

Categories (use these exact formats):
  general                    → for conversation, questions, knowledge, explanations
  realtime                   → for weather, news, stock prices, live scores, current political leaders, who is president/PM/CEO
  open <app name>            → to open an app (e.g. "open chrome")
  close <app name>           → to close an app (e.g. "close spotify")
  exit_eklavya               → to quit or shutdown this AI assistant
  play <query> on youtube    → to play/search on YouTube
  play_spotify <query>       → to play on Spotify
  search_web <query>         → for Google search
  open_url <url>             → open a specific URL
  screenshot                 → take screenshot
  volume up <n>              → increase volume by n%
  volume down <n>            → decrease volume by n%
  mute                       → mute audio
  get_time                   → current time
  get_date                   → current date
  battery                    → battery status
  system_info                → system stats
  lock                       → lock screen
  shutdown                   → shutdown PC
  restart                    → restart PC
  create_note <text>         → save a note
  set_reminder <msg>|<time>  → set a reminder
  send_whatsapp <name>|<msg> → send a whatsapp message
  call <name>                → make a phone call

IMPORTANT: ANY question about current political leaders, presidents, prime ministers, CEOs,
election results, or recent events MUST be classified as 'realtime' not 'general'.

Examples:
"Launch vs code"       → open vs code
"Play Bollywood hits"  → play_spotify Bollywood hits
"Who is the president of USA" → realtime
"What's the weather"   → realtime
"shutdown laptop"      → shutdown"""

        response = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": query},
            ],
            max_tokens=60,
            temperature=0.1,
        )
        result = response.choices[0].message.content.strip().lower()
        if result:
            return [cmd.strip() for cmd in result.split('|')]

    except Exception as e:
        print(f"[AutoModel] LLM classify error: {e}")

    return ['general']
