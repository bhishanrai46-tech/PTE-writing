import hashlib
import json
import re
import secrets
import random
from datetime import date, datetime

import streamlit as st
import streamlit.components.v1 as components
import anthropic
import altair as alt
import pandas as pd
from supabase import create_client

APP_NAME = "Write90 PTE"
APP_TAGLINE = "Flawless Grammar. Perfect Logic. Target 90."

st.set_page_config(page_title=APP_NAME, layout="wide")

# ---------------------------------------------------------------------------
# Styling — "Write90 PTE" theme. Deep slate/charcoal for header and sidebar,
# clean light canvas for the workspace, royal blue accent throughout. A
# broad reset still forces every element to a dark ink color on light
# backgrounds first; specific components override on top so nothing can
# render invisible regardless of Streamlit's internal markup.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --bg: #F8FAFC; --surface: #FFFFFF; --border: #E2E8F0;
        --text: #0F172A; --text-secondary: #475569;
        --accent: #2563EB; --accent-hover: #1D4ED8;
        --slate: #0F172A; --charcoal: #1E293B;
        --success: #15803D; --success-bg: #F0FDF4;
        --warning: #B45309; --warning-bg: #FFFBEB;
        --danger: #B91C1C; --danger-bg: #FEF2F2;
        --guide-bg: #EFF6FF;
        --sidebar-bg: #0F172A;
    }

    /* Hide standard Streamlit chrome: hamburger menu, footer, header bar */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; height: 0; }
    [data-testid="stToolbar"] { visibility: hidden; }

    .stApp, body, .main, [data-testid="stAppViewContainer"] { background-color: var(--bg) !important; }
    .main * { color: var(--text); }
    h1, h2, h3, h4 { font-family: 'Inter', -apple-system, sans-serif !important; color: var(--text) !important; font-weight: 600 !important; letter-spacing: -0.01em; }
    p, span, label, li, div, small { color: var(--text); }

    [data-testid="stMarkdownContainer"] * { color: var(--text) !important; }
    [data-testid="stCaptionContainer"] * { color: var(--text-secondary) !important; }
    [data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px; }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * { color: var(--text) !important; }
    [data-testid="stExpander"] div { color: var(--text) !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: var(--text) !important; }
    code, pre { color: var(--text) !important; background: #F1F5F9 !important; }

    /* Sidebar — dark slate blueprint */
    [data-testid="stSidebar"] { background-color: var(--sidebar-bg) !important; border-right: 1px solid #1E293B; }
    [data-testid="stSidebar"] * { color: #E2E8F0 !important; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: #94A3B8 !important; }
    [data-testid="stSidebar"] .stButton > button { background-color: #1E293B !important; border: 1px solid #334155 !important; color: #E2E8F0 !important; }
    [data-testid="stSidebar"] .stButton > button:hover { border-color: var(--accent) !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stTextInput input { background-color: #1E293B !important; color: #E2E8F0 !important; border: 1px solid #334155 !important; }
    [data-testid="stSidebar"] .stProgress > div > div { background-color: var(--accent) !important; }
    [data-testid="stSidebar"] .stProgress { background-color: #1E293B !important; border-radius: 4px; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { color: var(--text-secondary) !important; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }

    .stTextArea textarea { background-color: #FFFFFF !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 8px; font-size: 14.5px; padding: 12px 14px !important; }
    .stTextArea textarea:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.15) !important; }
    .stTextArea textarea::placeholder { color: #94A3B8 !important; }
    .stTextInput input { background-color: #FFFFFF !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 6px; }
    .stTextInput input:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.15) !important; }
    .stTextInput label, .stTextArea label { color: var(--text) !important; font-weight: 600 !important; }
    .stSelectbox label { color: var(--text) !important; font-weight: 600 !important; }

    /* Buttons */
    .stButton > button, .stButton > button * { color: var(--text) !important; }
    .stButton > button { background-color: #FFFFFF !important; border: 1px solid var(--border) !important; border-radius: 8px !important; font-weight: 500; transition: all 0.15s ease; }
    .stButton > button:hover, .stButton > button:hover * { color: var(--accent) !important; }
    .stButton > button:hover { border-color: var(--accent) !important; }
    .stButton > button[kind="primary"], .stButton > button[kind="primary"] * { color: #FFFFFF !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #2563EB, #1D4ED8) !important;
        border-color: #1D4ED8 !important;
        font-weight: 700 !important;
        text-shadow: 0 1px 1px rgba(0,0,0,0.15);
        box-shadow: 0 2px 8px rgba(37,99,235,0.35);
    }
    .stButton > button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover * { color: #FFFFFF !important; }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(180deg, #3B72F0, #2563EB) !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.5);
        transform: translateY(-1px);
    }

    .stRadio label, .stCheckbox label { color: var(--text) !important; }
    .stProgress > div > div { background-color: var(--accent) !important; }

    /* ---- Write90 brand elements ---- */
    .w90-banner {
        background: linear-gradient(120deg, #0F172A, #1E293B);
        border-radius: 12px;
        padding: 22px 28px;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    }
    .w90-banner .w90-title { font-family: 'Inter', sans-serif; font-size: 26px; font-weight: 700; color: #FFFFFF !important; margin: 0; }
    .w90-banner .w90-tag { font-size: 13.5px; color: #94A3B8 !important; margin-top: 4px; }
    .w90-banner .w90-badge {
        background: linear-gradient(180deg, #2563EB, #1D4ED8);
        color: #FFFFFF !important;
        font-size: 12.5px; font-weight: 700; letter-spacing: 0.04em;
        padding: 8px 16px; border-radius: 20px;
        box-shadow: 0 2px 8px rgba(37,99,235,0.4);
        white-space: nowrap;
    }

    .w90-profile-card {
        background: #1E293B; border: 1px solid #334155; border-radius: 10px;
        padding: 14px 16px; margin-bottom: 4px;
    }
    .w90-profile-card .w90-name { font-size: 14.5px; font-weight: 700; color: #FFFFFF !important; }
    .w90-profile-card .w90-role { font-size: 11.5px; color: #94A3B8 !important; letter-spacing: 0.04em; text-transform: uppercase; }

    .w90-metric-stack {
        font-family: 'Inter', monospace; font-size: 12.5px; font-weight: 600;
        letter-spacing: 0.03em; color: var(--text-secondary) !important;
        background: #F1F5F9; border: 1px solid var(--border); border-radius: 6px;
        padding: 6px 12px; display: inline-block; margin-top: 6px;
    }

    .w90-guide-box {
        background: var(--guide-bg); border-left: 4px solid var(--accent);
        border-radius: 8px; padding: 16px 18px;
    }
    .w90-guide-box h4 { margin-top: 0 !important; color: #1E3A8A !important; font-size: 15px !important; }
    .w90-guide-item { font-size: 13.5px; color: #1E3A8A !important; margin-bottom: 8px; padding-left: 6px; border-left: 2px solid #BFDBFE; }
    .w90-guide-item b { color: #1E3A8A !important; }

    .pte-badge { display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .pte-badge.great { background: var(--success-bg); color: var(--success) !important; }
    .pte-badge.good { background: var(--warning-bg); color: var(--warning) !important; }
    .pte-badge.push { background: var(--danger-bg); color: var(--danger) !important; }

    .pte-sentence { font-size: 14px; line-height: 1.6; margin-bottom: 10px; padding: 9px 12px; border-radius: 6px; border-left: 3px solid var(--border); }
    .pte-sentence.ok { border-left-color: var(--success); background: #FAFDFB; }
    .pte-sentence.err { border-left-color: var(--danger); background: #FFFBFA; }
    .pte-sentence .orig-bad { color: var(--danger) !important; text-decoration: line-through; }
    .pte-sentence .fixed { color: var(--success) !important; font-weight: 600; }
    .pte-sentence .why { display: block; font-size: 12px; color: var(--text-secondary) !important; margin-top: 3px; }
    .pte-sentence .ok-text { color: var(--text) !important; }

    .pte-corrected-box { background: #FAFAFA; border: 1px solid var(--border); border-radius: 6px; padding: 14px 16px; font-size: 14px; line-height: 1.7; color: var(--text) !important; }
    .pte-tip { background: #F8FAFC; border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 4px; padding: 8px 12px; margin-bottom: 6px; font-size: 13.5px; color: var(--text) !important; }
    .pte-streak { background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; text-align: center; }
    .pte-streak .n { font-size: 22px; font-weight: 700; color: #FFFFFF !important; }

    .pte-score-box { text-align: center; padding: 18px 0 6px; }
    .pte-score-box .num { font-size: 48px; font-weight: 700; color: var(--text) !important; line-height: 1; }
    .pte-score-box .of90 { font-size: 12px; color: var(--text-secondary) !important; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 2px; }
    .pte-summary { font-size: 14.5px; color: var(--text-secondary) !important; text-align: center; max-width: 560px; margin: 8px auto 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_top_banner():
    st.markdown(
        f"""
        <div class="w90-banner">
            <div>
                <p class="w90-title">{APP_NAME}</p>
                <p class="w90-tag">{APP_TAGLINE}</p>
            </div>
            <div class="w90-badge">AIMING FOR 90/90</div>
        </div>
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

# ---------------------------------------------------------------------------
# Built-in practice question bank.
#
# IMPORTANT HONESTY NOTE: Pearson does not publish an official public bank of
# PTE exam questions — the real exam pool is confidential and rotates. These
# are original practice prompts/passages written to match the common topic
# areas and format of the real Essay and Summarize Written Text tasks, not
# reproductions of actual exam content. They exist so you can start practicing
# immediately without needing to paste your own material.
# ---------------------------------------------------------------------------
ESSAY_QUESTIONS = [
    "Some people believe that technology has made our lives more complicated, while others think it has simplified daily life. Discuss both views and give your own opinion.",
    "In many countries, the gap between the rich and the poor is increasing. What are the causes of this trend, and what measures can be taken to address it?",
    "Some people think that governments should invest more in public transportation rather than building new roads. To what extent do you agree or disagree?",
    "Many universities now offer online degrees alongside traditional campus-based programs. Do the benefits of online education outweigh the drawbacks?",
    "Some argue that social media has strengthened human relationships, while others believe it has made people more isolated. Discuss both sides and give your opinion.",
    "As cities grow, urban green spaces are often reduced to make way for housing and infrastructure. Should governments prioritize green spaces over development?",
    "Some people believe that employees should be allowed to work from home permanently, while others think office attendance is essential for productivity. Discuss both views and give your opinion.",
    "Many people believe that success is primarily determined by hard work, while others argue that natural talent plays a bigger role. Discuss both views and give your own opinion.",
    "Some argue that international tourism benefits local economies, while others believe it damages local culture and the environment. Discuss both views and give your opinion.",
    "In several countries, schools are reducing the amount of homework given to students. Do you think this is a positive or negative development?",
]

SWT_PASSAGES = [
    "Renewable energy sources such as solar and wind power have grown rapidly over the past decade, driven by falling technology costs and increasing government support. Unlike fossil fuels, these sources produce little to no greenhouse gas emissions during operation, making them central to global efforts to combat climate change. However, their reliance on weather conditions creates challenges for maintaining a stable electricity supply, prompting significant investment in battery storage and smart grid technologies. Many energy analysts now predict that renewables will overtake coal and gas as the dominant source of global electricity generation within the next two decades, provided that storage costs continue to decline at their current pace.",
    "Remote work, once a rare arrangement limited mainly to freelancers, became mainstream during the global disruptions of the early 2020s and has remained widespread ever since. Proponents argue that it increases employee flexibility, reduces commuting time, and can improve productivity for tasks requiring deep concentration. Critics, however, point to challenges in maintaining team cohesion, onboarding new employees, and separating work from personal life. As a result, many organizations have adopted hybrid models that combine in-office collaboration with remote flexibility, attempting to capture the benefits of both approaches while minimizing their respective drawbacks.",
    "Urban planners increasingly recognize that poorly designed cities contribute to problems ranging from traffic congestion to social isolation. Compact, walkable neighborhoods with mixed residential and commercial zoning tend to reduce reliance on private vehicles, lower emissions, and foster stronger community interaction. In contrast, sprawling suburban developments often require long commutes and limit spontaneous social contact between residents. Several cities have begun redesigning neighborhoods around this principle, incorporating wider footpaths, dedicated cycling lanes, and public spaces intended to encourage walking and casual interaction rather than car dependency.",
    "The rapid advancement of artificial intelligence has raised significant ethical questions about accountability, bias, and transparency. Because many AI systems learn from historical data, they can inadvertently reproduce or amplify existing societal biases, particularly in areas such as hiring, lending, and law enforcement. Researchers and policymakers are now exploring frameworks for auditing algorithms before deployment and requiring companies to disclose how automated decisions are made. Some experts argue that without such oversight, the benefits of AI could be undermined by a loss of public trust and an increase in unintended discriminatory outcomes.",
    "Biodiversity loss has accelerated markedly over the past century, driven primarily by habitat destruction, pollution, and climate change. Scientists warn that the current rate of species extinction is significantly higher than the natural background rate observed throughout most of Earth's history. Conservation efforts, including protected reserves and species reintroduction programs, have shown localized success, but many experts argue that addressing the root causes, particularly deforestation and unsustainable agriculture, is essential for any long-term recovery. International cooperation remains difficult, as conservation priorities often conflict with short-term economic development goals in many regions.",
    "Sleep researchers have found that chronic sleep deprivation is associated with a wide range of negative health outcomes, including impaired memory, weakened immune function, and increased risk of cardiovascular disease. Despite this evidence, modern lifestyles characterized by long working hours, late-night screen use, and irregular schedules continue to erode average sleep duration in many industrialized countries. Some employers have begun experimenting with flexible start times and nap facilities in response to growing awareness of sleep's role in productivity and wellbeing, though such initiatives remain far from universal across industries.",
    "Financial literacy, the ability to understand and effectively use various financial skills such as budgeting and investing, remains uneven across populations despite its growing importance in an increasingly complex economic environment. Studies have shown that individuals with stronger financial literacy tend to save more, carry less high-interest debt, and plan more effectively for retirement. In response, some education systems have begun incorporating personal finance education into secondary school curricula, though critics argue that such programs are often too brief or theoretical to meaningfully change long-term financial behavior.",
    "Space exploration has entered a new era characterized by increasing involvement from private companies alongside traditional government space agencies. This shift has substantially reduced the cost of launching satellites and cargo, enabling more frequent missions and opening possibilities for commercial activities such as space tourism and asteroid mining. Critics caution that the growing number of private launches raises concerns about space debris and regulatory oversight, as no single international body currently has comprehensive authority over commercial space activity. Proponents counter that competition among private firms has accelerated innovation at a pace government agencies alone could not match.",
]


TASK_CONFIGS = {
    "essay": {
        "label": "Essay",
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
# Database (Supabase)
# ---------------------------------------------------------------------------
def get_db():
    url = st.secrets.get("SUPABASE_URL", "").strip()
    key = st.secrets.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        st.error("Supabase credentials missing. Add SUPABASE_URL and SUPABASE_KEY to your app's secrets.")
        st.stop()
    # Defensive: a URL pasted with a trailing slash or an accidental
    # /rest/v1 suffix causes PostgREST error PGRST125 (duplicated path,
    # e.g. .../rest/v1/rest/v1/users). Normalize it down to the bare
    # project URL Supabase expects (https://xxxx.supabase.co).
    url = url.rstrip("/")
    for suffix in ("/rest/v1", "/rest"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return create_client(url, key)


def db_healthy(conn):
    """Runs a harmless read against the users table so we can fail with a
    clear, actionable message instead of an uncaught crash deep inside some
    other function (e.g. if Supabase's Row Level Security is blocking access)."""
    try:
        conn.table("users").select("username").limit(1).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(conn, username: str, password: str):
    """Returns (success, error). error is None on success, 'duplicate' if the
    username is genuinely taken, or the raw error string for anything else
    (permissions, missing table, etc.) so it isn't misreported as 'taken'."""
    try:
        conn.table("users").insert({"username": username, "password_hash": hash_pw(password)}).execute()
        return True, None
    except Exception as e:
        msg = str(e)
        if "duplicate key" in msg.lower() or "23505" in msg or "already exists" in msg.lower():
            return False, "duplicate"
        return False, msg


def verify_user(conn, username: str, password: str) -> bool:
    try:
        res = conn.table("users").select("password_hash").eq("username", username).execute()
    except Exception:
        return False
    rows = res.data or []
    return bool(rows) and rows[0]["password_hash"] == hash_pw(password)


def create_session(conn, username: str) -> str:
    token = secrets.token_urlsafe(32)
    conn.table("sessions").insert({"token": token, "username": username}).execute()
    return token


def get_session_user(conn, token: str):
    try:
        res = conn.table("sessions").select("username").eq("token", token).execute()
        rows = res.data or []
        return rows[0]["username"] if rows else None
    except Exception:
        return None


def delete_session(conn, token: str):
    try:
        conn.table("sessions").delete().eq("token", token).execute()
    except Exception:
        pass


def save_submission(conn, username: str, task_key: str, context_text: str, response_text: str, result: dict):
    conn.table("submissions").insert({
        "username": username,
        "task_key": task_key,
        "context_text": context_text,
        "response_text": response_text,
        "overall": int(result.get("overall", 0)),
        "result_json": result,
    }).execute()


def get_history(conn, username: str, task_key: str):
    res = (
        conn.table("submissions")
        .select("created_at,context_text,response_text,overall,result_json")
        .eq("username", username)
        .eq("task_key", task_key)
        .order("created_at", desc=True)
        .execute()
    )
    rows = []
    for r in res.data or []:
        rj = r.get("result_json")
        rj_str = rj if isinstance(rj, str) else json.dumps(rj or {})
        rows.append((r["created_at"], r.get("context_text"), r.get("response_text"), r.get("overall"), rj_str))
    return rows


def get_all_history(conn, username: str):
    res = (
        conn.table("submissions")
        .select("task_key,created_at,overall")
        .eq("username", username)
        .order("created_at")
        .execute()
    )
    return [(r["task_key"], r["created_at"], r["overall"]) for r in (res.data or [])]


def get_usage_count(conn, username: str) -> int:
    today = str(date.today())
    res = conn.table("usage").select("count").eq("username", username).eq("day", today).execute()
    rows = res.data or []
    return rows[0]["count"] if rows else 0


def bump_usage_count(conn, username: str):
    today = str(date.today())
    current = get_usage_count(conn, username)
    if current == 0:
        try:
            conn.table("usage").insert({"username": username, "day": today, "count": 1}).execute()
            return
        except Exception:
            pass  # row already exists (race condition) — fall through to update
    conn.table("usage").update({"count": current + 1}).eq("username", username).eq("day", today).execute()


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


def fixed_score_chart(scores: list):
    """A plain, static line chart — no scroll-zoom, no drag-pan, fixed 0-90 axis."""
    df = pd.DataFrame({"Attempt": list(range(1, len(scores) + 1)), "Score": scores})
    chart = (
        alt.Chart(df)
        .mark_line(point=True, color="#2563EB")
        .encode(
            x=alt.X("Attempt:O", title="Attempt"),
            y=alt.Y("Score:Q", title="Score", scale=alt.Scale(domain=[0, 90])),
            tooltip=["Attempt", "Score"],
        )
        .properties(height=220)
        .interactive(False)
    )
    st.altair_chart(chart, use_container_width=True)


def get_criteria_averages(conn, username: str, task_key: str) -> dict:
    history = get_history(conn, username, task_key)
    sums, counts = {}, {}
    for row in history:
        try:
            result = json.loads(row[4])
        except Exception:
            continue
        for k, v in result.get("criteria", {}).items():
            sums[k] = sums.get(k, 0) + v
            counts[k] = counts.get(k, 0) + 1
    return {k: sums[k] / counts[k] for k in sums if counts.get(k)}


def get_recent_tips(conn, username: str, task_key: str, limit: int = 3) -> list:
    history = get_history(conn, username, task_key)
    tips = []
    for row in history[:limit]:
        try:
            result = json.loads(row[4])
        except Exception:
            continue
        for t in result.get("tips", []):
            if t not in tips:
                tips.append(t)
    return tips


TIP_LIBRARY = {
    "content": "Before writing, list every sub-point the prompt or passage raises, and check each one appears in your response.",
    "form": "Count your words as you write. Aim for the middle of the target range rather than just barely inside it.",
    "development": "Give each paragraph one clear topic sentence, and connect ideas explicitly with words like however, therefore, in addition.",
    "grammar": "Reread each sentence in isolation, backward if needed — it makes subject-verb agreement and article errors easier to spot.",
    "linguistic_range": "Practice rewriting the same idea two ways (active vs passive, simple vs complex) to build sentence variety.",
    "vocabulary": "Keep a running list of synonyms for words you overuse (important, believe, show) and rotate them in.",
    "spelling": "Pick one English variant (US or UK) and use it consistently — mixing color/colour or organize/organise costs points.",
}


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
        return '<span class="pte-badge great">On track for 79+</span>'
    if overall >= 65:
        return '<span class="pte-badge good">Solid, keep pushing</span>'
    return '<span class="pte-badge push">Room to grow</span>'


def tts_button(text: str, key: str):
    safe_text = json.dumps(text)
    components.html(
        f"""
        <div style="font-family:Inter,sans-serif;">
        <button id="playBtn_{key}" style="background:#2563EB;color:#FFFFFF;border:1px solid #2563EB;border-radius:6px;
            padding:10px 18px;font-weight:500;cursor:pointer;">Play lecture aloud</button>
        <button id="stopBtn_{key}" style="background:#FFFFFF;color:#0F172A;border:1px solid #E2E8F0;border-radius:6px;
            padding:10px 18px;font-weight:500;cursor:pointer;margin-left:8px;">Stop</button>
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
        f'<div class="pte-score-box"><span class="num">{overall}</span><br>'
        f'<span class="of90">out of 90</span></div>',
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
            body = f'<span class="ok-text">{esc(item.get("original",""))}</span>'
        st.markdown(f'<div class="pte-sentence {css_class}">{body}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Corrected 90-level version")
    st.markdown(f'<div class="pte-corrected-box">{esc(result.get("corrected_response",""))}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Tips to work on")
    for tip in result.get("tips", []):
        st.markdown(f'<div class="pte-tip">{esc(tip)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
conn = get_db()

healthy, health_error = db_healthy(conn)
if not healthy:
    render_top_banner()
    st.error(
        "Can't reach the database. Common causes: the Supabase tables haven't been "
        "created yet, Row Level Security is blocking access, or SUPABASE_URL in your "
        "secrets has an extra '/rest/v1' or trailing slash on it (it should be just "
        "https://xxxxx.supabase.co)."
    )
    with st.expander("Technical details"):
        st.code(health_error or "Unknown error")
    st.stop()

if "user" not in st.session_state:
    st.session_state["user"] = None

# Restore login after a page refresh using a session token stored in the URL.
if not st.session_state["user"]:
    token = st.query_params.get("t")
    if token:
        restored_user = get_session_user(conn, token)
        if restored_user:
            st.session_state["user"] = restored_user
            st.session_state["session_token"] = token

if not st.session_state["user"]:
    render_top_banner()
    st.caption("Log in or create a free account to save your work and track your score history over time.")
    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        lu = st.text_input("Username", key="login_user")
        lp = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log in"):
            db_error = None
            try:
                ok = verify_user(conn, lu.strip(), lp)
            except Exception as e:
                ok = False
                db_error = str(e)
            if ok:
                token = create_session(conn, lu.strip())
                st.session_state["user"] = lu.strip()
                st.session_state["session_token"] = token
                st.query_params["t"] = token
                st.rerun()
            elif db_error:
                st.error("Could not reach the database.")
                with st.expander("Technical details"):
                    st.code(db_error)
            else:
                st.error("Incorrect username or password.")

    with tab_signup:
        su = st.text_input("Choose a username", key="signup_user")
        sp = st.text_input("Choose a password", type="password", key="signup_pass")
        if st.button("Create account"):
            if not su.strip() or not sp:
                st.error("Enter a username and password.")
            else:
                ok, err = create_user(conn, su.strip(), sp)
                if ok:
                    token = create_session(conn, su.strip())
                    st.session_state["user"] = su.strip()
                    st.session_state["session_token"] = token
                    st.query_params["t"] = token
                    st.rerun()
                elif err == "duplicate":
                    st.error("That username is already taken.")
                else:
                    st.error("Could not create the account — a database error occurred.")
                    with st.expander("Technical details"):
                        st.code(err)

    st.stop()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
DAILY_LIMIT = int(st.secrets.get("DAILY_LIMIT", 20))
secret_key = st.secrets.get("ANTHROPIC_API_KEY", "")

with st.sidebar:
    st.markdown(
        f"""
        <div class="w90-profile-card">
            <div class="w90-name">{esc(st.session_state['user'])}</div>
            <div class="w90-role">WRITE90 CANDIDATE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Log out"):
        token = st.session_state.get("session_token")
        if token:
            delete_session(conn, token)
        st.session_state["user"] = None
        st.session_state.pop("session_token", None)
        if "t" in st.query_params:
            del st.query_params["t"]
        st.rerun()

    api_key = secret_key if secret_key else st.text_input("Anthropic API key", type="password")

    usage_today = get_usage_count(conn, st.session_state["user"])
    st.markdown("---")
    st.caption(f"DAILY DIAGNOSTIC EVALUATIONS: {usage_today} / {DAILY_LIMIT}")
    st.progress(min(1.0, usage_today / DAILY_LIMIT if DAILY_LIMIT else 0))

    all_hist = get_all_history(conn, st.session_state["user"])
    streak = compute_streak(all_hist)
    if streak > 0:
        st.markdown("---")
        st.markdown(
            f'<div class="pte-streak"><span class="n">{streak}</span><br>day streak</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------
render_top_banner()


task_tab_labels = [cfg["label"] for cfg in TASK_CONFIGS.values()]
main_tabs = st.tabs(task_tab_labels + ["My Progress"])

for tab, task_key in zip(main_tabs[:-1], TASK_CONFIGS.keys()):
    cfg = TASK_CONFIGS[task_key]
    with tab:
        sub_new, sub_history = st.tabs(["New attempt", "History"])

        with sub_new:
            left, right = st.columns([1.3, 1])

            with left:
                # Built-in question bank — essay and SWT only, so users don't
                # need to supply their own prompt/passage to start practicing.
                if task_key in ("essay", "swt"):
                    bank = ESSAY_QUESTIONS if task_key == "essay" else SWT_PASSAGES
                    labels = ["Write your own..."] + [f"Q{i+1}: {q[:65]}..." for i, q in enumerate(bank)]
                    bank_col1, bank_col2, bank_col3 = st.columns([3, 1, 1])
                    with bank_col1:
                        choice = st.selectbox("Practice question bank", labels, key=f"bankchoice_{task_key}")
                    with bank_col2:
                        st.write("")
                        use_clicked = st.button("Use", key=f"usebank_{task_key}")
                    with bank_col3:
                        st.write("")
                        if st.button("Random", key=f"random_{task_key}"):
                            st.session_state[f"ctx_{task_key}"] = random.choice(bank)
                            st.rerun()
                    if use_clicked and choice != "Write your own...":
                        idx = labels.index(choice) - 1
                        st.session_state[f"ctx_{task_key}"] = bank[idx]
                        st.rerun()

                context_text = st.text_area(cfg["context_label"], height=110,
                                             placeholder=cfg["context_placeholder"], key=f"ctx_{task_key}")
                if task_key == "sst" and context_text.strip():
                    tts_button(context_text, key=task_key)
                response_text = st.text_area(cfg["response_label"], height=220,
                                              placeholder=cfg["response_placeholder"], key=f"resp_{task_key}")
                wc = word_count(response_text)
                char_count = len(response_text)
                lo, hi = cfg["word_range"]
                wc_color = "green" if lo <= wc <= hi else ("orange" if wc else "gray")
                st.markdown(
                    f'<div class="w90-metric-stack">METRIC STACK: {wc} WORDS | CHARACTER BLOCKS: {char_count}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(cfg["word_hint"])
                submit = st.button("Mark My Response Against Rubric", type="primary", key=f"submit_{task_key}",
                                    disabled=not response_text.strip())

            with right:
                guide_html = f'<div class="w90-guide-box"><h4>Verification Guide</h4>'
                for key, name, max_score in cfg["criteria"]:
                    guide_html += f'<div class="w90-guide-item"><b>{esc(name)}</b> — up to {max_score} pts</div>'
                guide_html += "</div>"
                st.markdown(guide_html, unsafe_allow_html=True)

            st.markdown("---")
            if not response_text.strip():
                st.info("Write your response above, then click **Mark My Response Against Rubric**.")
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
                st.info("Click **Mark My Response Against Rubric** to get your score.")

        with sub_history:
            history = get_history(conn, st.session_state["user"], task_key)
            if not history:
                st.info("No attempts yet. Your history for this task will appear here.")
            else:
                scores = [row[3] for row in history][::-1]
                if len(scores) > 1:
                    fixed_score_chart(scores)
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

        for task_key, cfg in TASK_CONFIGS.items():
            task_scores = [r[2] for r in all_hist if r[0] == task_key]
            if not task_scores:
                continue

            st.markdown("---")
            st.subheader(cfg["label"])
            st.caption(f"{len(task_scores)} attempts · average {round(sum(task_scores)/len(task_scores))}/90 · latest {task_scores[-1]}/90")
            if len(task_scores) > 1:
                fixed_score_chart(task_scores)

            col_weak, col_tips = st.columns(2)

            with col_weak:
                st.markdown("**What to improve**")
                averages = get_criteria_averages(conn, st.session_state["user"], task_key)
                if not averages:
                    st.caption("Not enough data yet.")
                else:
                    crit_lookup = {key: (name, max_score) for key, name, max_score in cfg["criteria"]}
                    ranked = sorted(
                        averages.items(),
                        key=lambda kv: kv[1] / crit_lookup[kv[0]][1] if kv[0] in crit_lookup else 1,
                    )
                    for key, avg_score in ranked[:2]:
                        if key not in crit_lookup:
                            continue
                        name, max_score = crit_lookup[key]
                        st.write(f"{name} — averaging {avg_score:.1f} / {max_score}")
                        st.progress(min(1.0, avg_score / max_score if max_score else 0))
                        st.caption(TIP_LIBRARY.get(key, "Focus extra practice on this area."))

            with col_tips:
                st.markdown("**Tips from your recent work**")
                recent_tips = get_recent_tips(conn, st.session_state["user"], task_key, limit=3)
                if not recent_tips:
                    st.caption("Not enough data yet.")
                else:
                    for tip in recent_tips:
                        st.markdown(f'<div class="pte-tip">{esc(tip)}</div>', unsafe_allow_html=True)
