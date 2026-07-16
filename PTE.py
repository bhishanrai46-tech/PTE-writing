import hashlib
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st
import anthropic

DB_PATH = Path("pte_app.db")

st.set_page_config(page_title="PTE Essay Marker — Get to 90", page_icon="✏️", layout="wide")

# ---------------------------------------------------------------------------
# Styling — exam-script theme. Every text-bearing element gets an explicit
# color so nothing can render invisible regardless of a visitor's system
# theme (the light/dark mismatch bug from before).
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp, body { background-color: #F3EEE1 !important; color: #1D2B3A !important; }
    h1, h2, h3, h4 { font-family: Georgia, 'Times New Roman', serif; color: #1D2B3A !important; }
    p, span, label, li, div { color: #1D2B3A; }
    .stMarkdown, .stCaption, .stText, .stTextInput label, .stTextArea label { color: #1D2B3A !important; }
    [data-testid="stSidebar"] { background-color: #EFE7D3 !important; }
    [data-testid="stSidebar"] * { color: #1D2B3A !important; }
    .stTextArea textarea { background-color: #1D2B3A !important; color: #F3EEE1 !important; }
    .stTextArea textarea::placeholder { color: #B8AF98 !important; }
    .stTextInput input { background-color: #FFFFFF !important; color: #1D2B3A !important; }
    .stButton button { background-color: #1D2B3A !important; color: #F3EEE1 !important; border: none; }
    .stButton button:hover { background-color: #A93226 !important; color: #FFFFFF !important; }
    .stTabs [data-baseweb="tab"] { color: #1D2B3A !important; }

    .pte-stamp {
        width: 140px; height: 140px; border-radius: 50%;
        border: 3px solid #A93226; display: flex; flex-direction: column;
        align-items: center; justify-content: center; margin: 0 auto 18px auto;
        transform: rotate(-6deg); color: #A93226 !important; font-family: Georgia, serif;
    }
    .pte-stamp .num { font-size: 42px; font-weight: 700; line-height: 1; color: #A93226 !important; }
    .pte-stamp .of90 { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; margin-top: 4px; color: #A93226 !important; }
    .pte-summary { font-family: Georgia, serif; font-size: 15px; color: #445167 !important; text-align: center; }

    .pte-sentence { font-size: 14.5px; line-height: 1.7; margin-bottom: 14px; padding: 10px 14px; border-radius: 6px; }
    .pte-sentence.ok { background: #E7EFE7; }
    .pte-sentence.err { background: #FBEAE7; }
    .pte-sentence .orig-bad { color: #A44238 !important; text-decoration: line-through; }
    .pte-sentence .fixed { color: #2F6B3E !important; font-weight: 600; }
    .pte-sentence .why { display: block; font-size: 12px; color: #6B6355 !important; margin-top: 4px; }
    .pte-sentence .ok-text { color: #1D2B3A !important; }

    .pte-corrected-box { background: #FFFFFF; border: 1px solid #D8D0BC; border-radius: 6px; padding: 16px 18px; font-size: 14.5px; line-height: 1.7; color: #1D2B3A !important; }
    .pte-tip { background: #EFE3C0; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; font-size: 14px; color: #4A3B1A !important; }
    .pte-history-card { border: 1px solid #D8D0BC; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px; background: #FFFFFF; }
    </style>
    """,
    unsafe_allow_html=True,
)

CRITERIA_META = [
    ("content", "Content", 3),
    ("form", "Form", 2),
    ("development", "Development, Structure & Coherence", 2),
    ("grammar", "Grammar", 2),
    ("linguistic_range", "General Linguistic Range", 2),
    ("vocabulary", "Vocabulary Range", 2),
    ("spelling", "Spelling", 2),
]

SYSTEM_PROMPT = """You are an experienced PTE Academic examiner. Score the essay using the OFFICIAL Pearson PTE Academic Writing "Essay" rubric exactly as Pearson defines it, not a simplified version.

OFFICIAL TRAITS AND MAX POINTS (raw total = 15):
- Content (0-3): Does the response address all aspects of the prompt with relevant, specific, well-explained ideas and examples? If the essay is off-topic, not in English, written entirely in capitals, contains no punctuation, or is only bullet points/a list, Content = 0 and EVERY other trait must also be scored 0 (cascade rule).
- Form (0-2): 2 if 200-300 words. 1 if 120-199 or 301-380 words. 0 if under 120 or over 380 words. If Form = 0, every trait except Content must also be scored 0 (cascade rule).
- Development, Structure & Coherence (0-2): logical organization, clear paragraphing (intro/body/conclusion), connective devices linking ideas.
- Grammar (0-2): grammatical accuracy and control across simple and complex sentence structures.
- General Linguistic Range (0-2): precision and variety of expression; does the language clearly and subtly convey the intended meaning, using complex structures where appropriate.
- Vocabulary Range (0-2): breadth, precision, and appropriateness of word choice; avoids repetition.
- Spelling (0-2): consistent, correct spelling (one English variant used consistently — US or UK, not mixed).

Convert the raw total (max 15) to a scaled score out of 90 the way PTE reports it: a strong 12-13/15 is typically mid-high 70s to low 80s, a near-perfect 14-15/15 is high 80s-90, a weak 6-8/15 is 40s-50s, and 0-3/15 or a cascaded zero is 10-30.

Additionally provide:
1. "content_summary": a neutral 2-sentence paraphrase, in your own words, of what the essay actually argues (not a judgment, just what it says).
2. "examiner_summary": 2-3 direct, specific sentences on overall performance and the single biggest lever to raise the score.
3. "sentence_errors": the person's essay will be given to you as a NUMBERED list of sentences. Return an entry ONLY for sentences that contain an actual error — skip correct sentences entirely, do not list them. Each entry: {"index": the integer number of that sentence from the numbered list, "corrected": corrected version of that sentence, "explanation": short reason}. Keep this list to genuine errors only.
4. "corrected_essay": a full rewritten version of the entire essay at a 90-level standard, keeping the person's original ideas and structure but fixing all errors and elevating vocabulary/grammar naturally.
5. "tips": an array of 4-6 short, specific, actionable improvement tips based on THIS essay's actual recurring weaknesses (not generic advice).

Respond with ONLY raw JSON, no markdown fences, no preamble, in this exact shape:
{"overall": number, "criteria": {"content": number, "form": number, "development": number, "grammar": number, "linguistic_range": number, "vocabulary": number, "spelling": number}, "content_summary": "...", "examiner_summary": "...", "sentence_errors": [{"index": 0, "corrected": "...", "explanation": "..."}], "corrected_essay": "...", "tips": ["...", "..."]}"""


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
            created_at TEXT NOT NULL,
            prompt TEXT,
            essay TEXT,
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
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    return bool(row) and row[0] == hash_pw(password)


def save_submission(conn, username: str, prompt: str, essay: str, result: dict):
    conn.execute(
        "INSERT INTO submissions (username, created_at, prompt, essay, overall, result_json) VALUES (?, ?, ?, ?, ?, ?)",
        (username, datetime.now().isoformat(timespec="seconds"), prompt, essay,
         int(result.get("overall", 0)), json.dumps(result)),
    )
    conn.commit()


def get_history(conn, username: str):
    rows = conn.execute(
        "SELECT created_at, prompt, essay, overall, result_json FROM submissions WHERE username = ? ORDER BY id DESC",
        (username,),
    ).fetchall()
    return rows


def get_usage_count(conn, username: str) -> int:
    today = str(date.today())
    row = conn.execute(
        "SELECT count FROM usage WHERE username = ? AND day = ?", (username, today)
    ).fetchone()
    return row[0] if row else 0


def bump_usage_count(conn, username: str):
    today = str(date.today())
    conn.execute(
        """INSERT INTO usage (username, day, count) VALUES (?, ?, 1)
           ON CONFLICT(username, day) DO UPDATE SET count = count + 1""",
        (username, today),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------
class GradingError(Exception):
    def __init__(self, message, raw_text=""):
        super().__init__(message)
        self.raw_text = raw_text


def try_repair_json(text: str) -> dict:
    """If the JSON was truncated mid-string/object (hit max_tokens), try a
    best-effort repair by closing off the last complete field."""
    # Cut back to the last place a value cleanly ended, then close braces.
    for cutoff in ["\"}]}", "\"}", "\"]", "\""]:
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


def word_count(text: str) -> int:
    return len(text.split())


def split_sentences(text: str) -> list:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def call_claude(api_key: str, prompt: str, essay: str, words: int, model: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    sentences = split_sentences(essay)
    numbered = "\n".join(f"{i}: {s}" for i, s in enumerate(sentences))
    user_msg = (
        (f"Essay prompt: {prompt}\n\n" if prompt.strip() else "")
        + f"Essay ({words} words), given below as a numbered list of sentences:\n{numbered}"
    )
    response = client.messages.create(
        model=model,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
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
            sentence_analysis.append({
                "original": s,
                "has_error": True,
                "corrected": e.get("corrected", s),
                "explanation": e.get("explanation", ""),
            })
        else:
            sentence_analysis.append({"original": s, "has_error": False, "corrected": s, "explanation": ""})
    parsed["sentence_analysis"] = sentence_analysis
    return parsed


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_result(result: dict):
    overall = max(10, min(90, round(result.get("overall", 0))))
    st.markdown(
        f'<div class="pte-stamp"><span class="num">{overall}</span>'
        f'<span class="of90">out of 90</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<p class="pte-summary">{esc(result.get("examiner_summary", ""))}</p>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Criteria breakdown")
    criteria = result.get("criteria", {})
    for key, name, max_score in CRITERIA_META:
        score = criteria.get(key, 0)
        col1, col2 = st.columns([4, 1])
        with col1:
            st.progress(min(1.0, score / max_score if max_score else 0))
        with col2:
            st.write(f"{score} / {max_score}")
        st.caption(name)

    st.markdown("---")
    st.subheader("What your essay says")
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
    st.markdown(f'<div class="pte-corrected-box">{esc(result.get("corrected_essay",""))}</div>', unsafe_allow_html=True)

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
    st.title("✏️ PTE Essay Marker")
    st.caption("Log in or create an account to save your essays and track your score history.")
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
    st.write(f"Logged in as **{st.session_state['user']}**")
    if st.button("Log out"):
        st.session_state["user"] = None
        st.rerun()

    if not secret_key:
        api_key = st.text_input("Anthropic API key", type="password")
    else:
        api_key = secret_key

    usage_today = get_usage_count(conn, st.session_state["user"])
    st.markdown("---")
    st.caption(f"Essays graded today: **{usage_today} / {DAILY_LIMIT}**")
    st.progress(min(1.0, usage_today / DAILY_LIMIT if DAILY_LIMIT else 0))

    st.markdown("---")
    speed_choice = st.radio(
        "Grading speed",
        ["Fast", "Thorough"],
        help="Fast uses a quicker model — good for a quick check. Thorough takes longer but reasons more carefully, worth it before a real test.",
    )
    MODEL = "claude-haiku-4-5-20251001" if speed_choice == "Fast" else "claude-sonnet-5"

# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------
st.title("✏️ PTE Essay Marker")
st.caption("Get examiner-style scoring against the real PTE Writing rubric — powered by Claude.")

tab_new, tab_history = st.tabs(["Grade an essay", "My history"])

with tab_new:
    left, right = st.columns([1.3, 1])

    with left:
        prompt = st.text_area("Essay prompt (optional, improves accuracy)", height=70,
                               placeholder="Paste the essay question here...")
        essay = st.text_area("Your essay", height=340,
                              placeholder="Write or paste your 200–300 word essay here...")
        wc = word_count(essay)
        wc_color = "green" if 200 <= wc <= 300 else ("orange" if wc else "gray")
        st.markdown(f":{wc_color}[**{wc} words**]")
        submit = st.button("Mark my essay", type="primary", disabled=not essay.strip())

    with right:
        if not essay.strip():
            st.info("Write your essay on the left, then click **Mark my essay**.")
        elif submit:
            if not api_key:
                st.error("Enter your Anthropic API key in the sidebar first.")
            elif get_usage_count(conn, st.session_state["user"]) >= DAILY_LIMIT:
                st.error(f"Daily limit of {DAILY_LIMIT} essays reached. Please try again tomorrow.")
            else:
                with st.spinner("Marking your script…"):
                    try:
                        result = call_claude(api_key, prompt, essay, wc, MODEL)
                        bump_usage_count(conn, st.session_state["user"])
                        save_submission(conn, st.session_state["user"], prompt, essay, result)
                        render_result(result)
                    except GradingError as e:
                        st.error("The examiner's response didn't come back in a readable format. Please try again — this usually resolves on a retry.")
                        with st.expander("Technical details"):
                            st.code(e.raw_text[-2000:] if e.raw_text else str(e))
                    except Exception as e:
                        st.error(f"Something went wrong marking your essay: {e}")
        else:
            st.info("Click **Mark my essay** to get your score.")

with tab_history:
    history = get_history(conn, st.session_state["user"])
    if not history:
        st.info("No essays graded yet. Your history will appear here.")
    else:
        scores = [row[3] for row in history][::-1]
        if len(scores) > 1:
            st.line_chart(scores)
        for created_at, hprompt, hessay, hoverall, hresult_json in history:
            with st.expander(f"{created_at[:16].replace('T',' ')} — Score: {hoverall}/90"):
                if hprompt:
                    st.caption(f"Prompt: {hprompt}")
                st.write(hessay)
                try:
                    render_result(json.loads(hresult_json))
                except Exception:
                    st.write("(Could not load detailed breakdown for this entry.)")
