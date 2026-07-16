import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import anthropic

DB_PATH = Path("pte_app.db")

st.set_page_config(page_title="PTE Practice Studio — Get to 90", page_icon="🎓", layout="wide")

# ---------------------------------------------------------------------------
# Styling — warm "exam studio" theme. A broad reset forces every element to
# the ink color first, then specific components (buttons, sidebar, badges,
# stamp) override with their own colors afterward. This ordering matters:
# it's what stops any text from silently inheriting a white/dark default
# from the visitor's system theme, no matter which Streamlit widget it is.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    /* ---- Broad reset: everything defaults to ink-on-paper ---- */
    .stApp, body, .main, [data-testid="stAppViewContainer"] { background-color: #F6F1E4 !important; }
    .main * { color: #24344A; }
    h1, h2, h3, h4 { font-family: 'Fraunces', Georgia, serif !important; color: #1D2B3A !important; letter-spacing: -0.01em; }
    p, span, label, li, div, small { color: #24344A; }

    /* Streamlit-specific containers that often carry their own theme color */
    [data-testid="stMarkdownContainer"] * { color: #24344A !important; }
    [data-testid="stCaptionContainer"] * { color: #6B6355 !important; }
    [data-testid="stExpander"] { background: #FFFFFF !important; border: 1px solid #E3D9BF !important; border-radius: 8px; }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: #1D2B3A !important; }
    [data-testid="stExpander"] div { color: #24344A !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #1D2B3A !important; }
    [data-testid="stAlertContainer"] * { color: inherit !important; }
    [data-testid="stVerticalBlock"] { color: #24344A; }
    code, pre { color: #1D2B3A !important; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #EDE4CB !important; border-right: 1px solid #DDCFA8; }
    [data-testid="stSidebar"] * { color: #1D2B3A !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { color: #6B6355 !important; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #A93226 !important; border-bottom-color: #A93226 !important; }

    /* Inputs */
    .stTextArea textarea { background-color: #1D2B3A !important; color: #F6F1E4 !important; border-radius: 8px; font-size: 15px; }
    .stTextArea textarea::placeholder { color: #93A0AC !important; }
    .stTextInput input { background-color: #FFFFFF !important; color: #1D2B3A !important; border: 1px solid #D8CBA6 !important; border-radius: 6px; }
    .stTextInput label, .stTextArea label { color: #1D2B3A !important; font-weight: 600 !important; }

    /* Buttons */
    .stButton button { background-color: #1D2B3A !important; color: #F6F1E4 !important; border: none !important; border-radius: 6px !important; font-weight: 600; transition: transform 0.1s ease, background 0.15s ease; }
    .stButton button:hover { background-color: #A93226 !important; color: #FFFFFF !important; transform: translateY(-1px); }
    .stButton button p { color: inherit !important; }
    .stButton button[kind="primary"] { background-color: #A93226 !important; }
    .stButton button[kind="primary"]:hover { background-color: #8A281E !important; }

    /* Radio / checkbox */
    .stRadio label, .stCheckbox label { color: #1D2B3A !important; }

    /* Progress bar */
    .stProgress > div > div { background-color: #A93226 !important; }

    /* ---- Brand elements ---- */
    .pte-hero { text-align: center; margin-bottom: 6px; }
    .pte-hero .kicker { font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; color: #A9822E !important; font-weight: 600; }

    .pte-stamp-wrap { display: flex; justify-content: center; margin: 8px 0 6px; }
    .pte-stamp {
        width: 148px; height: 148px; border-radius: 50%;
        border: 3px solid #A93226; display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        background: radial-gradient(circle at 35% 30%, #FFFDF8, #FBF3E3);
        box-shadow: 0 4px 14px rgba(169,50,38,0.18);
        transform: rotate(-5deg); font-family: 'Fraunces', Georgia, serif;
    }
    .pte-stamp .num { font-size: 46px; font-weight: 700; line-height: 1; color: #A93226 !important; }
    .pte-stamp .of90 { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 4px; color: #A93226 !important; }
    .pte-stamp .max { font-size: 10px; color: #9C7A2E !important; margin-top: 2px; }
    .pte-summary { font-family: 'Fraunces', Georgia, serif; font-size: 15.5px; color: #445167 !important; text-align: center; max-width: 560px; margin: 6px auto 0; }

    .pte-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12.5px; font-weight: 600; margin: 2px 4px 2px 0; }
    .pte-badge.great { background: #E4F1E6; color: #2F6B3E !important; }
    .pte-badge.good { background: #FBF0DA; color: #8A6A1E !important; }
    .pte-badge.push { background: #FBEAE7; color: #A44238 !important; }

    .pte-sentence { font-size: 14.5px; line-height: 1.7; margin-bottom: 12px; padding: 10px 14px; border-radius: 8px; }
    .pte-sentence.ok { background: #EAF2EA; }
    .pte-sentence.err { background: #FBEAE7; }
    .pte-sentence .orig-bad { color: #A44238 !important; text-decoration: line-through; }
    .pte-sentence .fixed { color: #2F6B3E !important; font-weight: 600; }
    .pte-sentence .why { display: block; font-size: 12px; color: #6B6355 !important; margin-top: 4px; }
    .pte-sentence .ok-text { color: #1D2B3A !important; }

    .pte-corrected-box { background: #FFFFFF; border: 1px solid #E3D9BF; border-radius: 10px; padding: 18px 20px; font-size: 14.5px; line-height: 1.75; color: #1D2B3A !important; }
    .pte-tip { background: linear-gradient(135deg, #FBF0DA, #F3E4BB); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 14px; color: #4A3B1A !important; border-left: 3px solid #A9822E; }
    .pte-streak { background: #1D2B3A; color: #F6F1E4 !important; border-radius: 10px; padding: 14px 18px; text-align: center; }
    .pte-streak * { color: #F6F1E4 !important; }
    .pte-streak .n { font-size: 28px; font-weight: 700; font-family: 'Fraunces', Georgia, serif; }
    </style>
    """,
    unsafe_allow_html=True,
)


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def word_count(text: str) -> int:
    return len(text.split())


def split_sentences(text: str) -> list:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Task definitions — each PTE task type's official rubric, word target, and
# the labels used to build its form. All three share one JSON result
# contract so grading/rendering/history code stays generic.
# ---------------------------------------------------------------------------
COMMON_TAIL = """
Additionally provide:
- "content_summary": a neutral, brief summary in your own words of what the source material is about and how well the response captures it.
- "examiner_summary": 2-3 direct, specific sentences on performance and the single biggest lever to raise the score.
- "sentence_errors": the response will be given to you as a NUMBERED list of sentences. Return an entry ONLY for sentences with an actual error — skip correct ones entirely. Each: {"index": integer, "corrected": "...", "explanation": "..."}.
- "corrected_response": a full rewritten version of the entire response at a 90-level standard, keeping the original ideas but fixing all errors.
- "tips": an array of 3-6 short, specific, actionable tips based on THIS response's actual recurring weaknesses.

Respond with ONLY raw JSON, no markdown fences, no preamble, in this exact shape:
{"overall": number, "criteria": {<criteria keys>}, "content_summary": "...", "examiner_summary": "...", "sentence_errors": [{"index": 0, "corrected": "...", "explanation": "..."}], "corrected_response": "...", "tips": ["...", "..."]}"""

TASK_CONFIGS = {
    "essay": {
        "label": "Essay",
        "icon": "✍️",
        "context_label": "Essay prompt (optional, improves accuracy)",
        "context_placeholder": "Paste the essay question here...",
        "response_label": "Your essay",
        "response_placeholder": "Write or paste your 200–300 word essay here...",
        "word_range": (200, 300),
        "word_hint": "Aim for 200–300 words.",
        "criteria": [
            ("content", "Content", 3),
            ("form", "Form", 2),
            ("development", "Development, Structure & Coherence", 2),
            ("grammar", "Grammar", 2),
            ("linguistic_range", "General Linguistic Range", 2),
            ("vocabulary", "Vocabulary Range", 2),
            ("spelling", "Spelling", 2),
        ],
        "rubric": """You are an experienced PTE Academic examiner. Score using the OFFICIAL Pearson PTE Academic Writing "Essay" rubric.

OFFICIAL TRAITS AND MAX POINTS (raw total = 15):
- Content (0-3): addresses all aspects of the prompt with relevant, specific, well-explained ideas/examples. If off-topic, not in English, all capitals, no punctuation, or bullet points only, Content = 0 and EVERY other trait must also be 0 (cascade rule).
- Form (0-2): 2 if 200-300 words. 1 if 120-199 or 301-380 words. 0 if under 120 or over 380 words. If Form = 0, every trait except Content must also be 0 (cascade rule).
- Development, Structure & Coherence (0-2): logical organization, clear paragraphing, connective devices.
- Grammar (0-2): grammatical accuracy and control across simple and complex structures.
- General Linguistic Range (0-2): precision and variety of expression, complex structures where appropriate.
- Vocabulary Range (0-2): breadth, precision, appropriateness of word choice.
- Spelling (0-2): consistent, correct spelling (one English variant, not mixed).

Convert raw total (max 15) to a scaled score out of 90: strong 12-13/15 is mid-high 70s to low 80s, near-perfect 14-15/15 is high 80s-90, weak 6-8/15 is 40s-50s, cascaded zero is 10-30.""",
    },
    "swt": {
        "label": "Summarize Written Text",
        "icon": "📄",
        "context_label": "Passage to summarize (up to ~300 words)",
        "context_placeholder": "Paste the reading passage here...",
        "response_label": "Your one-sentence summary",
        "response_placeholder": "Write ONE sentence, 5–75 words, capturing the passage's main idea...",
        "word_range": (5, 75),
        "word_hint": "Must be exactly ONE sentence, 5–75 words.",
        "criteria": [
            ("content", "Content", 2),
            ("form", "Form", 1),
            ("grammar", "Grammar", 2),
            ("vocabulary", "Vocabulary", 2),
        ],
        "rubric": """You are an experienced PTE Academic examiner. Score using the OFFICIAL Pearson PTE Academic "Summarize Written Text" rubric.

OFFICIAL TRAITS AND MAX POINTS (raw total = 7):
- Content (0-2): captures the main point(s) of the passage without misrepresenting its topic or purpose. If the response misrepresents the passage, Content = 0 and every other trait must also be 0 (cascade rule).
- Form (0-1): must be exactly ONE complete sentence, 5-75 words, not written in capitals. If violated, Form = 0 and every trait except Content must also be 0 (cascade rule).
- Grammar (0-2): correct sentence structure, ideally a main clause plus subordinate clause.
- Vocabulary (0-2): relevant, appropriate word choice; effective use of synonyms from the passage.

Convert raw total (max 7) to a scaled score out of 90: 6-7/7 is high 80s-90, 5/7 is high 60s-70s, 3-4/7 is 40s-50s, cascaded zero is 10-20.""",
    },
    "sst": {
        "label": "Summarize Spoken Text",
        "icon": "🎧",
        "context_label": "Lecture transcript (what you'll listen to)",
        "context_placeholder": "Paste or write the lecture/talk transcript here...",
        "response_label": "Your summary (50–70 words)",
        "response_placeholder": "Write a 50–70 word paragraph summarizing the key points of the lecture...",
        "word_range": (50, 70),
        "word_hint": "Aim for 50–70 words. Under 40 or over 100 scores zero.",
        "criteria": [
            ("content", "Content", 2),
            ("form", "Form", 2),
            ("grammar", "Grammar", 2),
            ("vocabulary", "Vocabulary", 2),
            ("spelling", "Spelling", 2),
        ],
        "rubric": """You are an experienced PTE Academic examiner. Score using the OFFICIAL Pearson PTE Academic "Summarize Spoken Text" rubric.

OFFICIAL TRAITS AND MAX POINTS (raw total = 10):
- Content (0-2): addresses all key points of the lecture without misrepresenting its purpose or topic.
- Form (0-2): full credit for 50-70 words. Under 50 or over 70 reduces the score. Under 40 or over 100 words scores zero on ALL traits (cascade rule).
- Grammar (0-2): correct sentence structure, concise and clear.
- Vocabulary (0-2): relevant, academic-appropriate word choice, good use of synonyms.
- Spelling (0-2): consistent, correct spelling.

Convert raw total (max 10) to a scaled score out of 90: 9-10/10 is high 80s-90, 7-8/10 is 70s, 4-6/10 is 40s-60s, cascaded zero is 10-20.""",
    },
}

for _cfg in TASK_CONFIGS.values():
    _cfg["max_raw"] = sum(m for _, _, m in _cfg["criteria"])
    _cfg["system_prompt"] = _cfg["rubric"] + "\n" + COMMON_TAIL


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            task_key TEXT NOT NULL,
            created_at TEXT NOT NULL,
            context_text TEXT,
            response_text TEXT,
            overall INTEGER,
            result_json TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS usage (
            username TEXT NOT NULL,
            day TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (username, day)
        )"""
    )
    conn.commit()
    return conn


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(conn, username: str, password: str) -> bool:
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_pw(password), datetime.now().isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(conn, username: str, password: str) -> bool:
    row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    return bool(row) and row[0] == hash_pw(password)


def save_submission(conn, username: str, task_key: str, context_text: str, response_text: str, result: dict):
    conn.execute(
        "INSERT INTO submissions (username, task_key, created_at, context_text, response_text, overall, result_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, task_key, datetime.now().isoformat(timespec="seconds"), context_text, response_text,
         int(result.get("overall", 0)), json.dumps(result)),
    )
    conn.commit()


def get_history(conn, username: str, task_key: str):
    return conn.execute(
        "SELECT created_at, context_text, response_text, overall, result_json FROM submissions "
        "WHERE username = ? AND task_key = ? ORDER BY id DESC",
        (username, task_key),
    ).fetchall()


def get_all_history(conn, username: str):
    return conn.execute(
        "SELECT task_key, created_at, overall FROM submissions WHERE username = ? ORDER BY id ASC",
        (username,),
    ).fetchall()


def get_usage_count(conn, username: str) -> int:
    today = str(date.today())
    row = conn.execute("SELECT count FROM usage WHERE username = ? AND day = ?", (username, today)).fetchone()
    return row[0] if row else 0


def bump_usage_count(conn, username: str):
    today = str(date.today())
    conn.execute(
        """INSERT INTO usage (username, day, count) VALUES (?, ?, 1)
           ON CONFLICT(username, day) DO UPDATE SET count = count + 1""",
        (username, today),
    )
    conn.commit()


def compute_streak(all_history) -> int:
    days = sorted({row[1][:10] for row in all_history}, reverse=True)
    if not days:
        return 0
    streak = 0
    cursor = date.today()
    day_set = set(days)
    while str(cursor) in day_set:
        streak += 1
        cursor = date.fromordinal(cursor.toordinal() - 1)
    return streak


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------
class GradingError(Exception):
    def __init__(self, message, raw_text=""):
        super().__init__(message)
        self.raw_text = raw_text


def try_repair_json(text: str) -> dict:
    for cutoff in ['"}]}', '"}', '"]', '"']:
        idx = text.rfind(cutoff)
        if idx != -1:
            candidate = text[: idx + len(cutoff)]
            depth_curly = candidate.count("{") - candidate.count("}")
            depth_square = candidate.count("[") - candidate.count("]")
            candidate += "]" * max(0, depth_square) + "}" * max(0, depth_curly)
            try:
                return json.loads(candidate)
            except Exception:
                continue
    raise GradingError("Could not repair truncated response.", raw_text=text)


def call_claude(api_key: str, task_key: str, context_text: str, response_text: str, words: int) -> dict:
    cfg = TASK_CONFIGS[task_key]
    client = anthropic.Anthropic(api_key=api_key)
    sentences = split_sentences(response_text)
    numbered = "\n".join(f"{i}: {s}" for i, s in enumerate(sentences))
    user_msg = (
        (f"Source material:\n{context_text}\n\n" if context_text.strip() else "")
        + f"Response ({words} words), given as a numbered list of sentences:\n{numbered}"
    )
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        system=cfg["system_prompt"],
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    text = re.sub(r"```json|```", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = try_repair_json(text)
        except GradingError:
            raise
        except Exception:
            raise GradingError("The examiner's response was malformed.", raw_text=text)

    errors_by_index = {}
    for e in parsed.get("sentence_errors", []):
        try:
            errors_by_index[int(e.get("index"))] = e
        except (TypeError, ValueError):
            continue

    sentence_analysis = []
    for i, s in enumerate(sentences):
        e = errors_by_index.get(i)
        if e:
            sentence_analysis.append({"original": s, "has_error": True, "corrected": e.get("corrected", s), "explanation": e.get("explanation", "")})
        else:
            sentence_analysis.append({"original": s, "has_error": False, "corrected": s, "explanation": ""})
    parsed["sentence_analysis"] = sentence_analysis
    return parsed


def score_badge(overall: int) -> str:
    if overall >= 79:
        return '<span class="pte-badge great">🌟 On track for 79+</span>'
    if overall >= 65:
        return '<span class="pte-badge good">👍 Solid, keep pushing</span>'
    return '<span class="pte-badge push">💪 Room to grow — you\'ve got this</span>'


def tts_button(text: str, key: str):
    safe_text = json.dumps(text)
    components.html(
        f"""
        <div style="font-family:Inter,sans-serif;">
        <button id="playBtn_{key}" style="background:#1D2B3A;color:#F6F1E4;border:none;border-radius:6px;
            padding:10px 18px;font-weight:600;cursor:pointer;">🔊 Play lecture aloud</button>
        <button id="stopBtn_{key}" style="background:transparent;color:#A93226;border:1px solid #A93226;border-radius:6px;
            padding:10px 18px;font-weight:600;cursor:pointer;margin-left:8px;">⏹ Stop</button>
        <script>
        const text_{key} = {safe_text};
        document.getElementById('playBtn_{key}').onclick = function() {{
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance(text_{key});
            u.rate = 0.95;
            window.speechSynthesis.speak(u);
        }};
        document.getElementById('stopBtn_{key}').onclick = function() {{
            window.speechSynthesis.cancel();
        }};
        </script>
        </div>
        """,
        height=60,
    )


def render_result(result: dict, task_key: str):
    cfg = TASK_CONFIGS[task_key]
    overall = max(10, min(90, round(result.get("overall", 0))))
    st.markdown(
        f'<div class="pte-stamp-wrap"><div class="pte-stamp"><span class="num">{overall}</span>'
        f'<span class="of90">out of 90</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div style="text-align:center;">{score_badge(overall)}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="pte-summary">{esc(result.get("examiner_summary", ""))}</p>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Criteria breakdown")
    criteria = result.get("criteria", {})
    for key, name, max_score in cfg["criteria"]:
        score = criteria.get(key, 0)
        col1, col2 = st.columns([4, 1])
        with col1:
            st.progress(min(1.0, score / max_score if max_score else 0))
        with col2:
            st.write(f"{score} / {max_score}")
        st.caption(name)

    st.markdown("---")
    st.subheader("What this response covers")
    st.write(result.get("content_summary", ""))

    st.markdown("---")
    st.subheader("Sentence-by-sentence review")
    for item in result.get("sentence_analysis", []):
        has_error = item.get("has_error", False)
        css_class = "err" if has_error else "ok"
        if has_error:
            body = (
                f'<span class="orig-bad">{esc(item.get("original",""))}</span><br>'
                f'→ <span class="fixed">{esc(item.get("corrected",""))}</span>'
                f'<span class="why">{esc(item.get("explanation",""))}</span>'
            )
        else:
            body = f'<span class="ok-text">✓ {esc(item.get("original",""))}</span>'
        st.markdown(f'<div class="pte-sentence {css_class}">{body}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Corrected 90-level version")
    st.markdown(f'<div class="pte-corrected-box">{esc(result.get("corrected_response",""))}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Tips to work on")
    for tip in result.get("tips", []):
        st.markdown(f'<div class="pte-tip">💡 {esc(tip)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
conn = get_db()

if "user" not in st.session_state:
    st.session_state["user"] = None

if not st.session_state["user"]:
    st.markdown(
        '<div class="pte-hero"><div class="kicker">PTE Practice Studio</div>'
        '<h1>🎓 Write. Get scored. Improve.</h1></div>',
        unsafe_allow_html=True,
    )
    st.caption("Log in or create a free account to save your work and track your score history over time.")
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        lu = st.text_input("Username", key="login_user")
        lp = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log in"):
            if verify_user(conn, lu.strip(), lp):
                st.session_state["user"] = lu.strip()
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    with tab_signup:
        su = st.text_input("Choose a username", key="signup_user")
        sp = st.text_input("Choose a password", type="password", key="signup_pass")
        if st.button("Create account"):
            if not su.strip() or not sp:
                st.error("Enter a username and password.")
            elif create_user(conn, su.strip(), sp):
                st.session_state["user"] = su.strip()
                st.rerun()
            else:
                st.error("That username is already taken.")

    st.stop()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
DAILY_LIMIT = int(st.secrets.get("DAILY_LIMIT", 20))
secret_key = st.secrets.get("ANTHROPIC_API_KEY", "")

with st.sidebar:
    st.write(f"👋 Logged in as **{st.session_state['user']}**")
    if st.button("Log out"):
        st.session_state["user"] = None
        st.rerun()

    api_key = secret_key if secret_key else st.text_input("Anthropic API key", type="password")

    usage_today = get_usage_count(conn, st.session_state["user"])
    st.markdown("---")
    st.caption(f"Responses graded today: **{usage_today} / {DAILY_LIMIT}**")
    st.progress(min(1.0, usage_today / DAILY_LIMIT if DAILY_LIMIT else 0))

    all_hist = get_all_history(conn, st.session_state["user"])
    streak = compute_streak(all_hist)
    if streak > 0:
        st.markdown("---")
        st.markdown(
            f'<div class="pte-streak">🔥 <span class="n">{streak}</span><br>day streak</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="pte-hero"><div class="kicker">PTE Practice Studio</div>'
    '<h1>🎓 Write. Get scored. Improve.</h1></div>',
    unsafe_allow_html=True,
)
st.caption("Examiner-style scoring against the official Pearson rubric, powered by Claude.")

task_tab_labels = [f"{cfg['icon']} {cfg['label']}" for cfg in TASK_CONFIGS.values()]
main_tabs = st.tabs(task_tab_labels + ["📊 My Progress"])

for tab, task_key in zip(main_tabs[:-1], TASK_CONFIGS.keys()):
    cfg = TASK_CONFIGS[task_key]
    with tab:
        sub_new, sub_history = st.tabs(["New attempt", "History"])

        with sub_new:
            left, right = st.columns([1.3, 1])
            with left:
                context_text = st.text_area(cfg["context_label"], height=140,
                                             placeholder=cfg["context_placeholder"], key=f"ctx_{task_key}")
                if task_key == "sst" and context_text.strip():
                    tts_button(context_text, key=task_key)
                response_text = st.text_area(cfg["response_label"], height=220,
                                              placeholder=cfg["response_placeholder"], key=f"resp_{task_key}")
                wc = word_count(response_text)
                lo, hi = cfg["word_range"]
                wc_color = "green" if lo <= wc <= hi else ("orange" if wc else "gray")
                st.markdown(f":{wc_color}[**{wc} words**] · {cfg['word_hint']}")
                submit = st.button("Mark my response", type="primary", key=f"submit_{task_key}",
                                    disabled=not response_text.strip())

            with right:
                if not response_text.strip():
                    st.info(f"Write your response on the left, then click **Mark my response**.")
                elif submit:
                    if not api_key:
                        st.error("Enter your Anthropic API key in the sidebar first.")
                    elif get_usage_count(conn, st.session_state["user"]) >= DAILY_LIMIT:
                        st.error(f"Daily limit of {DAILY_LIMIT} responses reached. Please try again tomorrow.")
                    else:
                        with st.spinner("Marking carefully against the official rubric… this can take a little while."):
                            try:
                                result = call_claude(api_key, task_key, context_text, response_text, wc)
                                bump_usage_count(conn, st.session_state["user"])
                                save_submission(conn, st.session_state["user"], task_key, context_text, response_text, result)
                                render_result(result, task_key)
                            except GradingError as e:
                                st.error("The examiner's response didn't come back in a readable format. Please try again.")
                                with st.expander("Technical details"):
                                    st.code(e.raw_text[-2000:] if e.raw_text else str(e))
                            except Exception as e:
                                st.error(f"Something went wrong marking your response: {e}")
                else:
                    st.info("Click **Mark my response** to get your score.")

        with sub_history:
            history = get_history(conn, st.session_state["user"], task_key)
            if not history:
                st.info("No attempts yet. Your history for this task will appear here.")
            else:
                scores = [row[3] for row in history][::-1]
                if len(scores) > 1:
                    st.line_chart(scores)
                for created_at, hcontext, hresponse, hoverall, hresult_json in history:
                    with st.expander(f"{created_at[:16].replace('T',' ')} — Score: {hoverall}/90"):
                        if hcontext:
                            st.caption(f"Source: {hcontext[:300]}{'…' if len(hcontext) > 300 else ''}")
                        st.write(hresponse)
                        try:
                            render_result(json.loads(hresult_json), task_key)
                        except Exception:
                            st.write("(Could not load detailed breakdown for this entry.)")

with main_tabs[-1]:
    all_hist = get_all_history(conn, st.session_state["user"])
    if not all_hist:
        st.info("Grade a few responses across the tabs above and your overall progress will show up here.")
    else:
        total = len(all_hist)
        avg = round(sum(r[2] for r in all_hist) / total)
        best = max(r[2] for r in all_hist)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total attempts", total)
        c2.metric("Average score", f"{avg}/90")
        c3.metric("Best score", f"{best}/90")
        c4.metric("Day streak", streak)

        st.markdown("---")
        for task_key, cfg in TASK_CONFIGS.items():
            task_scores = [r[2] for r in all_hist if r[0] == task_key]
            if task_scores:
                st.subheader(f"{cfg['icon']} {cfg['label']}")
                st.caption(f"{len(task_scores)} attempts · average {round(sum(task_scores)/len(task_scores))}/90 · latest {task_scores[-1]}/90")
                if len(task_scores) > 1:
                    st.line_chart(task_scores)
