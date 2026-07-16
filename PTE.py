import json
import re
from datetime import date
from pathlib import Path

import streamlit as st
import anthropic

USAGE_FILE = Path("usage_log.json")

st.set_page_config(page_title="PTE Essay Marker — Get to 90", page_icon="✏️", layout="wide")

# ---------------------------------------------------------------------------
# Styling — exam-script theme: warm paper, ink, red examiner's pen
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #F3EEE1; }
    h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif; color: #1D2B3A; }
    .pte-stamp {
        width: 140px; height: 140px; border-radius: 50%;
        border: 3px solid #A93226; display: flex; flex-direction: column;
        align-items: center; justify-content: center; margin: 0 auto 18px auto;
        transform: rotate(-6deg); color: #A93226; font-family: Georgia, serif;
    }
    .pte-stamp .num { font-size: 42px; font-weight: 700; line-height: 1; }
    .pte-stamp .of90 { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; margin-top: 4px; }
    .pte-note { font-size: 14px; margin-bottom: 10px; line-height: 1.5; }
    .pte-note .strike { color: #A44238; text-decoration: line-through; opacity: 0.8; }
    .pte-note .fixed { color: #3F6B4A; font-weight: 600; }
    .pte-note .why { color: #8A8272; display: block; font-size: 12.5px; margin-top: 1px; }
    .pte-summary { font-family: Georgia, serif; font-size: 15px; color: #445167; text-align: center; }
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

SYSTEM_PROMPT = """You are a strict, experienced PTE Academic examiner scoring a Writing "Essay" response.
Score using the real PTE Essay rubric, with these exact criteria and max points:
Content (0-3), Form (0-2), Development, Structure & Coherence (0-2), Grammar (0-2), General Linguistic Range (0-2), Vocabulary Range (0-2), Spelling (0-2). Max raw total = 15.
Convert the raw total to a scaled score out of 90 the way PTE reports it (roughly proportional; a strong 12-13/15 essay is usually mid-high 70s to low 80s, a near-perfect 15/15 is high 80s-90, a weak 6-8/15 is 40s-50s).
Word count for Form: 200-300 words is ideal; under 120 or over 380 loses more.
Also identify the 4-6 most important corrections (grammar, word choice, or structure), each as {"original": exact short phrase from the essay, "fixed": corrected phrase, "why": one short reason}. Keep each "original" under 12 words.
Respond with ONLY raw JSON, no markdown fences, no preamble, in this exact shape:
{"overall": number, "criteria": {"content": number, "form": number, "development": number, "grammar": number, "linguistic_range": number, "vocabulary": number, "spelling": number}, "summary": "2-3 sentence overall examiner comment, direct and specific", "corrections": [{"original": "...", "fixed": "...", "why": "..."}]}"""


def word_count(text: str) -> int:
    return len(text.split())


def read_usage() -> dict:
    today = str(date.today())
    if USAGE_FILE.exists():
        try:
            data = json.loads(USAGE_FILE.read_text())
        except Exception:
            data = {}
    else:
        data = {}
    if data.get("date") != today:
        data = {"date": today, "count": 0}
    return data


def bump_usage() -> int:
    data = read_usage()
    data["count"] = data.get("count", 0) + 1
    USAGE_FILE.write_text(json.dumps(data))
    return data["count"]


def check_password() -> bool:
    """Returns True if the visitor is allowed through. Shows a login box if a
    password is configured in secrets; if no APP_PASSWORD secret is set, the
    gate is skipped entirely (useful for local testing)."""
    app_password = st.secrets.get("APP_PASSWORD", "")
    if not app_password:
        return True
    if st.session_state.get("authed"):
        return True

    st.title("✏️ PTE Essay Marker")
    entered = st.text_input("Enter access password", type="password")
    if st.button("Enter"):
        if entered == app_password:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()


def call_claude(api_key: str, prompt: str, essay: str, words: int) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (f"Essay prompt: {prompt}\n\n" if prompt.strip() else "") + f"Essay ({words} words):\n{essay}"
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


def render_result(result: dict):
    overall = max(10, min(90, round(result.get("overall", 0))))
    st.markdown(
        f'<div class="pte-stamp"><span class="num">{overall}</span>'
        f'<span class="of90">out of 90</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<p class="pte-summary">{result.get("summary", "")}</p>', unsafe_allow_html=True)
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
    st.subheader("Examiner's margin notes")
    corrections = result.get("corrections", [])
    if not corrections:
        st.write("No major corrections flagged.")
    for corr in corrections:
        st.markdown(
            f'<div class="pte-note">§ <span class="strike">{corr.get("original","")}</span> '
            f'→ <span class="fixed">{corr.get("fixed","")}</span>'
            f'<span class="why">{corr.get("why","")}</span></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Sidebar — API key + usage limit status
# ---------------------------------------------------------------------------
DAILY_LIMIT = int(st.secrets.get("DAILY_LIMIT", 20))

with st.sidebar:
    st.header("Setup")
    secret_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if secret_key:
        api_key = secret_key
        st.success("API key loaded from app secrets.")
    else:
        api_key = st.text_input(
            "Anthropic API key",
            type="password",
            help="Get one at console.anthropic.com. Stored only for this session, never saved to disk.",
        )
        st.caption(
            "This app calls the Claude API directly from your machine/session. "
            "Your key is not sent anywhere except api.anthropic.com."
        )

    usage_today = read_usage().get("count", 0)
    st.markdown("---")
    st.caption(f"Essays graded today: **{usage_today} / {DAILY_LIMIT}**")
    st.progress(min(1.0, usage_today / DAILY_LIMIT if DAILY_LIMIT else 0))

# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------
st.title("✏️ PTE Essay Marker")
st.caption("Get examiner-style scoring against the real PTE Writing rubric — free, powered by Claude.")

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
        elif read_usage().get("count", 0) >= DAILY_LIMIT:
            st.error(
                f"Daily limit of {DAILY_LIMIT} essays reached. Please try again tomorrow."
            )
        else:
            with st.spinner("Marking your script…"):
                try:
                    result = call_claude(api_key, prompt, essay, wc)
                    bump_usage()
                    render_result(result)
                except Exception as e:
                    st.error(f"Something went wrong marking your essay: {e}")
    else:
        st.info("Click **Mark my essay** to get your score.")
