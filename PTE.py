import difflib
import hashlib
import json
import re
import secrets
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
        --success: #15803D; --success-bg: #F0FDF4;
        --warning: #B45309; --warning-bg: #FFFBEB;
        --danger: #B91C1C; --danger-bg: #FEF2F2;
        --guide-bg: #EFF6FF;
        --sidebar-bg: #FFFFFF;
    }

    /* Hide standard Streamlit chrome: hamburger menu, footer, deploy toolbar.
       IMPORTANT: we do NOT zero out or hide the header itself, because the
       sidebar expand/collapse arrow lives inside it — doing so was the cause
       of the sidebar becoming permanently inaccessible on both desktop and
       mobile. Only the menu/toolbar contents are hidden; the header stays
       present (transparent) so its arrow control keeps working. */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stToolbar"] { visibility: hidden; height: 0; }

    /* The sidebar expand arrow (shown when the sidebar is collapsed) and the
       collapse arrow (shown when it's open) use different data-testids across
       Streamlit versions — style both explicitly so the control is always
       visible and legible on the light theme, on desktop and mobile alike. */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        z-index: 999999 !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: var(--text) !important;
    }
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {
        visibility: visible !important;
        display: flex !important;
    }

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

    /* Sidebar — light theme, matching the rest of the app */
    [data-testid="stSidebar"] { background-color: var(--sidebar-bg) !important; border-right: 1px solid var(--border); }
    [data-testid="stSidebar"] * { color: var(--text) !important; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: var(--text-secondary) !important; }
    [data-testid="stSidebar"] .stButton > button { background-color: #FFFFFF !important; border: 1px solid var(--border) !important; color: var(--text) !important; }
    [data-testid="stSidebar"] .stButton > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
    [data-testid="stSidebar"] .stTextInput input { background-color: #FFFFFF !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
    [data-testid="stSidebar"] .stProgress > div > div { background-color: var(--accent) !important; }
    [data-testid="stSidebar"] .stProgress { background-color: var(--border) !important; border-radius: 4px; }

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

    /* Selectbox — the closed control */
    [data-baseweb="select"] > div { background-color: #FFFFFF !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
    [data-baseweb="select"] * { color: var(--text) !important; background-color: transparent !important; }
    [data-baseweb="select"] svg { fill: var(--text-secondary) !important; }
    [data-baseweb="select"] [data-baseweb="tag"] { background-color: var(--guide-bg) !important; }
    [data-testid="stSelectbox"] { background-color: transparent !important; }
    [data-testid="stSelectbox"] label { color: var(--text) !important; }

    /* Selectbox dropdown popover — this renders in a portal attached to
       <body>, OUTSIDE the app's main container, so none of the rules above
       reach it. Without explicit styling here it falls back to a dark
       default, which is the "unreadable dark dropdown" bug. */
    [data-baseweb="popover"] { background-color: #FFFFFF !important; }
    [data-baseweb="popover"] * { color: var(--text) !important; }
    [data-baseweb="menu"] { background-color: #FFFFFF !important; }
    ul[role="listbox"] { background-color: #FFFFFF !important; }
    li[role="option"] { background-color: #FFFFFF !important; color: var(--text) !important; }
    li[role="option"]:hover { background-color: var(--guide-bg) !important; color: var(--accent) !important; }
    li[aria-selected="true"] { background-color: var(--guide-bg) !important; color: var(--accent) !important; }

    /* Buttons — solid colors, no gradients */
    .stButton > button, .stButton > button * { color: var(--text) !important; }
    .stButton > button { background-color: #FFFFFF !important; border: 1px solid var(--border) !important; border-radius: 8px !important; font-weight: 500; transition: all 0.15s ease; }
    .stButton > button:hover, .stButton > button:hover * { color: var(--accent) !important; }
    .stButton > button:hover { border-color: var(--accent) !important; }
    .stButton > button[kind="primary"], .stButton > button[kind="primary"] * { color: #FFFFFF !important; }
    .stButton > button[kind="primary"] {
        background-color: var(--accent) !important;
        border-color: var(--accent) !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 6px rgba(37,99,235,0.25);
    }
    .stButton > button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover * { color: #FFFFFF !important; }
    .stButton > button[kind="primary"]:hover {
        background-color: var(--accent-hover) !important;
        box-shadow: 0 4px 10px rgba(37,99,235,0.35);
        transform: translateY(-1px);
    }

    .stRadio label, .stCheckbox label { color: var(--text) !important; }
    .stProgress > div > div { background-color: var(--accent) !important; }

    /* ---- Write90 brand elements — solid color, no gradients ---- */
    .w90-banner {
        background-color: var(--accent);
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
    .w90-banner .w90-tag { font-size: 13.5px; color: #DBEAFE !important; margin-top: 4px; }
    .w90-banner .w90-badge {
        background-color: #FFFFFF;
        color: var(--accent) !important;
        font-size: 12.5px; font-weight: 700; letter-spacing: 0.04em;
        padding: 8px 16px; border-radius: 20px;
        white-space: nowrap;
    }

    .w90-profile-card {
        background: var(--guide-bg); border: 1px solid #BFDBFE; border-radius: 10px;
        padding: 14px 16px; margin-bottom: 4px;
    }
    .w90-profile-card .w90-name { font-size: 14.5px; font-weight: 700; color: var(--text) !important; }
    .w90-profile-card .w90-role { font-size: 11.5px; color: var(--accent) !important; letter-spacing: 0.04em; text-transform: uppercase; }

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
    .pte-streak { background: var(--guide-bg); border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px 14px; text-align: center; }
    .pte-streak .n { font-size: 22px; font-weight: 700; color: var(--accent) !important; }

    .pte-score-box { text-align: center; padding: 18px 0 6px; }
    .pte-score-box .num { font-size: 48px; font-weight: 700; color: var(--text) !important; line-height: 1; }
    .pte-score-box .of90 { font-size: 12px; color: var(--text-secondary) !important; letter-spacing: 0.06em; text-transform: uppercase; margin-top: 2px; }
    .pte-summary { font-size: 14.5px; color: var(--text-secondary) !important; text-align: center; max-width: 560px; margin: 8px auto 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


def inject_sidebar_toggle():
    """A permanent, self-built toggle button pinned to the top-left corner of
    the screen (desktop and mobile). Streamlit's own collapse/expand control
    has changed data-testid names across versions (collapsedControl in older
    releases, stSidebarCollapseButton in 1.38+, etc.), so a pure-CSS fix can
    silently stop working after a Streamlit upgrade. This button doesn't
    guess a single name — it searches a list of known selectors for
    Streamlit's native control and clicks it directly, with a manual
    show/hide fallback if none are found. It only injects itself once per
    page load, so it's safe to call on every rerun."""
    components.html(
        """
        <script>
        (function() {
            try {
                var doc = window.parent.document;
                if (doc.getElementById('write90-sidebar-toggle')) return;

                var btn = doc.createElement('button');
                btn.id = 'write90-sidebar-toggle';
                btn.innerHTML = '&#9776;';
                btn.title = 'Show/hide menu';
                btn.style.cssText = [
                    'position:fixed', 'top:12px', 'left:12px', 'z-index:2147483647',
                    'background:#2563EB', 'color:#FFFFFF', 'border:none',
                    'border-radius:8px', 'width:38px', 'height:38px',
                    'font-size:18px', 'line-height:1', 'cursor:pointer',
                    'box-shadow:0 2px 8px rgba(0,0,0,0.3)', 'display:flex',
                    'align-items:center', 'justify-content:center'
                ].join(';');
                doc.body.appendChild(btn);

                function findNativeToggle() {
                    var selectors = [
                        '[data-testid="stSidebarCollapseButton"] button',
                        '[data-testid="stSidebarCollapseButton"]',
                        '[data-testid="collapsedControl"] button',
                        '[data-testid="collapsedControl"]',
                        '[data-testid="stSidebarCollapsedControl"] button',
                        '[data-testid="stSidebarCollapsedControl"]',
                        'header[data-testid="stHeader"] button'
                    ];
                    for (var i = 0; i < selectors.length; i++) {
                        var el = doc.querySelector(selectors[i]);
                        if (el) return el;
                    }
                    return null;
                }

                btn.addEventListener('click', function() {
                    var native = findNativeToggle();
                    if (native) {
                        native.click();
                        return;
                    }
                    // Last-resort fallback: flip the sidebar's own visibility
                    // directly if no known native control could be found.
                    var sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (sidebar) {
                        var hidden = sidebar.style.display === 'none';
                        sidebar.style.display = hidden ? '' : 'none';
                    }
                });
            } catch (e) {}
        })();
        </script>
        """,
        height=0,
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
- "corrected_response": a rewritten version of the PERSON'S OWN response, keeping their original ideas/structure/argument but fixing every error to reach a 90-level standard. This must stay recognizably their essay, just corrected.
- "model_response": a COMPLETELY INDEPENDENT, freshly composed response to the same prompt, written entirely by you as an ideal 90-scoring example. Do not base this on the person's content, ideas, or structure — write the best possible original response a top scorer would produce, meeting the exact word/sentence requirements for this task.
- "tips": an array of 3-6 short, specific, actionable tips based on THIS response's actual recurring weaknesses.

Respond with ONLY raw JSON, no markdown fences, no preamble, in this exact shape:
{"overall": number, "criteria": {<criteria keys>}, "content_summary": "...", "examiner_summary": "...", "sentence_errors": [{"index": 0, "corrected": "...", "explanation": "..."}], "corrected_response": "...", "model_response": "...", "tips": ["...", "..."]}"""

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
    "Some people believe that children should begin learning a foreign language as early as possible, while others think it is better to focus on their native language first. Discuss both views and give your opinion.",
    "Advances in artificial intelligence are expected to replace many jobs currently done by humans. Do the benefits of this technology outweigh the risks to employment?",
    "Some believe that university education should be free for all students, while others think students should pay for their own education. Discuss both views and give your opinion.",
    "In many workplaces, older and younger employees often have different attitudes toward work. What are the reasons for this, and how can organizations manage these differences effectively?",
    "Some people think that celebrities have too much influence on young people's behavior and attitudes. To what extent do you agree or disagree?",
    "Many governments are increasing taxes on unhealthy foods to reduce obesity rates. Do you think this is an effective solution?",
    "Some argue that space exploration is a waste of money that could be better spent solving problems on Earth, while others believe it is essential for humanity's future. Discuss both views and give your opinion.",
    "In some countries, the voting age has been lowered to 16. Do you think this is a positive change?",
    "Some people believe that traditional classroom learning is more effective than distance learning, while others disagree. Discuss both views and give your own opinion.",
    "Many people argue that zoos are cruel and should be banned, while others believe they play an important role in conservation and education. Discuss both views and give your opinion.",
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
    "Antibiotic resistance has emerged as one of the most pressing challenges in modern medicine, driven by decades of overuse and misuse of antibiotics in both healthcare and agriculture. Bacteria that survive exposure to these drugs can pass resistant traits to future generations, gradually rendering once-effective treatments useless. Public health officials warn that without coordinated global action to reduce unnecessary prescriptions and develop new classes of antibiotics, routine infections and surgical procedures could become significantly more dangerous within a generation.",
    "The gig economy, characterized by short-term contracts and freelance work facilitated by digital platforms, has expanded rapidly over the past fifteen years. Supporters argue it offers workers greater flexibility and access to income opportunities that traditional employment structures do not provide. Critics counter that gig workers often lack the job security, benefits, and legal protections afforded to full-time employees, creating a growing segment of the workforce vulnerable to economic instability. Several jurisdictions have begun experimenting with new classifications of employment to address this gap.",
    "Coral reefs, though covering less than one percent of the ocean floor, support roughly a quarter of all marine species, making them among the most biodiverse ecosystems on the planet. Rising ocean temperatures have triggered widespread coral bleaching events, in which corals expel the algae that provide them with nutrients and color, often leading to mass die-offs if conditions do not improve quickly. Marine biologists are experimenting with heat-resistant coral strains in an effort to preserve reef ecosystems as ocean temperatures continue to rise.",
    "Microplastics, tiny fragments of plastic less than five millimeters in size, have been detected in nearly every corner of the globe, from remote mountain snow to deep ocean trenches. These particles originate from the breakdown of larger plastic waste as well as from products such as synthetic clothing fibers and cosmetic microbeads. Although research into the health effects of microplastic ingestion in humans is still in its early stages, scientists have already documented their presence in human blood and organ tissue, prompting calls for stricter regulation of plastic production and waste management.",
    "Telemedicine, the practice of providing clinical healthcare remotely through video calls and digital monitoring tools, expanded dramatically in the wake of global health disruptions and has continued to grow since. Advocates highlight its potential to improve healthcare access in rural and underserved areas where specialists are scarce, while critics note limitations in diagnosing conditions that require physical examination or specialized equipment. Many healthcare systems have settled on hybrid models that combine remote consultations for routine matters with in-person visits reserved for more complex cases.",
    "The concept of a four-day work week has gained traction among employers and policymakers seeking to improve worker wellbeing without sacrificing productivity. Pilot programs conducted across several industries have generally reported that employees maintain or even increase their output when given a shorter working week, attributing this to reduced burnout and improved focus during working hours. Skeptics caution that the model may not translate easily to sectors requiring continuous staffing, such as healthcare and manufacturing, where reducing hours could necessitate costly increases in hiring.",
    "Vertical farming, the practice of growing crops in stacked layers within controlled indoor environments, has been proposed as a solution to the challenges of feeding a growing urban population with limited arable land. These systems use significantly less water than traditional agriculture and can operate year-round regardless of external weather conditions, but the high energy costs associated with artificial lighting and climate control have so far limited the technology's profitability outside of high-value crops such as leafy greens and herbs.",
    "Digital privacy has become an increasingly contentious issue as companies collect vast amounts of personal data to power targeted advertising and personalized services. Consumer advocates argue that current regulations have not kept pace with the scale and sophistication of modern data collection practices, leaving individuals with limited meaningful control over how their information is used. Some governments have introduced stricter data protection laws requiring explicit consent and greater transparency, though enforcement across international borders remains a persistent challenge.",
    "The rise of electric vehicles has prompted significant investment in charging infrastructure, though availability remains uneven between urban and rural areas. While city dwellers increasingly have access to public charging stations, drivers in more remote regions often face long detours to find a compatible charger, a factor that continues to discourage adoption outside metropolitan centers. Automakers and governments alike have pledged substantial funding toward expanding charging networks, aiming to eliminate this disparity within the next decade.",
    "Museums around the world are increasingly using augmented reality technology to enhance visitor engagement, allowing patrons to view historical reconstructions or additional context simply by pointing a smartphone at an exhibit. Early studies suggest that these tools can meaningfully improve information retention among younger visitors, though some curators worry that an overreliance on digital enhancement may distract from the direct experience of viewing original artifacts and artworks.",
    "Water scarcity is projected to affect an increasing share of the global population as climate change alters precipitation patterns and population growth strains existing supplies, particularly in arid and semi-arid regions. Engineers have proposed a range of solutions, from large-scale desalination plants to more efficient irrigation techniques, but the high energy costs and infrastructure investment required mean that many of the most affected regions remain the least equipped to implement these technologies at scale.",
    "The popularity of plant-based diets has grown substantially in recent years, driven by concerns about environmental sustainability, animal welfare, and personal health. Food manufacturers have responded by developing an expanding range of meat and dairy alternatives designed to replicate the taste and texture of traditional animal products. Nutritionists generally agree that well-planned plant-based diets can meet all necessary dietary requirements, though they caution that highly processed plant-based substitutes are not automatically healthier than the animal products they replace.",
]

DICTATION_SENTENCES = [
    "The committee will announce its final decision next Monday morning.",
    "Researchers discovered a new species of frog in the rainforest.",
    "Please submit your application before the end of the month.",
    "The museum's new exhibit attracted thousands of visitors last week.",
    "Scientists warn that the glacier is melting faster than expected.",
    "The company plans to open three new offices next year.",
    "Local farmers rely heavily on rainfall during the growing season.",
    "The library extended its opening hours for exam preparation week.",
    "Volunteers spent the weekend cleaning up the coastal shoreline.",
    "The professor postponed the lecture due to a scheduling conflict.",
    "Air pollution levels dropped significantly during the public holiday.",
    "The airline canceled several flights because of the severe storm.",
    "Her research paper was published in an international journal.",
    "The government introduced new regulations to protect small businesses.",
    "Engineers tested the bridge's structural integrity before it opened.",
    "The city council approved funding for a new public park.",
    "Students must register for the exam by the given deadline.",
    "The documentary explores the history of ancient trade routes.",
    "A sudden power outage delayed the start of the concert.",
    "The hospital introduced a new system for scheduling appointments.",
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
        "time_limit_min": 20,
        "context_height": 110,
        "criteria": [
            ("content", "Content", 6),
            ("form", "Form", 2),
            ("development", "Development, Structure & Coherence", 6),
            ("grammar", "Grammar", 2),
            ("linguistic_range", "General Linguistic Range", 6),
            ("vocabulary", "Vocabulary Range", 2),
            ("spelling", "Spelling", 2),
        ],
        "rubric": """You are an experienced PTE Academic examiner. Score this Essay response using the same trait structure and point scale as Pearson's official PTE Academic Score Guide (raw total = 26).

CASCADE RULE: if Content = 0 or Form = 0, every trait for this response scores 0.

Content (0-6): how fully and precisely the essay addresses every part of the prompt.
6 = fully addresses the prompt in depth with a nuanced, well-supported argument throughout.
5 = adequately addresses the prompt with a persuasive argument and relevant supporting detail, minor exceptions only.
4 = addresses the main point with a generally convincing argument, but supporting detail is inconsistent.
3 = relevant to the prompt but doesn't develop the main points adequately; detail often missing.
2 = superficial attempt with mostly generic statements or heavy reliance on prompt language; few relevant details.
1 = incomplete understanding of the prompt; generic/repetitive phrasing; supporting detail (if any) disjointed.
0 = does not properly address the prompt.

Form (0-2): 2 = 200-300 words. 1 = 120-199 or 301-380 words. 0 = under 120 or over 380 words, all-caps, no punctuation, or bullet points/very short sentences only.

Development, Structure & Coherence (0-6): organization and flow of the argument.
6 = effective logical structure throughout, flows smoothly; clear intro/conclusion; paragraphs logically sequenced; varied connectives used consistently.
5 = conventional appropriate structure, follows logically if not always smoothly; intro/conclusion/paragraphs present; connectives link ideas with occasional gaps.
4 = structure mostly present but some elements missing or hard to follow; simple paragraphing not always effective.
3 = only traces of structure; mostly simple or disconnected points; a position is present but underdeveloped; minimal paragraphing; only simple linear connectives.
2 = little recognizable structure; ideas disorganized and hard to follow; only very basic connectives (and/but/because).
1 = disconnected ideas with no hierarchy or coherence; no clear position; only the most basic linear connectives (and/then).
0 = no recognizable structure.

Grammar (0-2): 2 = consistent control of complex language, errors rare and hard to spot. 1 = relatively high control, no mistakes that would cause misunderstanding. 0 = mainly simple structures and/or several basic mistakes.

General Linguistic Range (0-6): precision and variety of expression.
6 = wide variety of expression used with ease and precision throughout; no restriction; any errors rare/minor, meaning always clear.
5 = variety of expression used appropriately throughout; ideas clear; occasional errors don't obscure meaning.
4 = sufficient range for basic ideas; limitations appear with complex/abstract ideas causing repetition or circumlocution; errors cause occasional lapses but main idea still followable.
3 = narrow range, repeated simple expressions; communication restricted to simple ideas; errors cause some disruption.
2 = limited vocabulary/simple expressions dominate; communication compromised, some ideas unclear; frequent basic errors.
1 = highly restricted expression; significant limitations, ideas generally unclear; pervasive errors impeding meaning.
0 = meaning not accessible.

Vocabulary Range (0-2): 2 = broad lexical repertoire including idiomatic/colloquial expressions used well. 1 = good range for general academic topics; some lexical shortcomings cause circumlocution or imprecision. 0 = mainly basic vocabulary, insufficient for the topic at this level.

Spelling (0-2): 2 = correct spelling throughout. 1 = one spelling error. 0 = more than one spelling error.

Convert the raw total (max 26) to a scaled practice score out of 90, proportionally: roughly 22-26/26 is high 80s-90, 17-21/26 is 70s-80s, 10-16/26 is 50s-60s, cascaded zero is 10-20. This is a simplified per-response practice estimate, not the official multi-question overall PTE score.""",
    },
    "swt": {
        "label": "Summarize Written Text",
        "context_label": "Passage to summarize (up to ~300 words)",
        "context_placeholder": "Paste the reading passage here...",
        "response_label": "Your one-sentence summary",
        "response_placeholder": "Write ONE sentence, 5–75 words, capturing the passage's main idea...",
        "word_range": (5, 75),
        "word_hint": "Must be exactly ONE sentence, 5–75 words.",
        "time_limit_min": 10,
        "context_height": 220,
        "criteria": [
            ("content", "Content", 4),
            ("form", "Form", 1),
            ("grammar", "Grammar", 2),
            ("vocabulary", "Vocabulary", 2),
        ],
        "rubric": """You are an experienced PTE Academic examiner. Score this Summarize Written Text response using the same trait structure and point scale as Pearson's official PTE Academic Score Guide (raw total = 9).

CASCADE RULE: if Content = 0 or Form = 0, every trait for this response scores 0.

Content (0-4): how well the summary captures the source passage.
4 = comprehensive, accurate summary showing full comprehension; effective paraphrasing, extraneous detail removed, main ideas synthesized concisely and coherently, smooth flow with varied connectives.
3 = adequate summary showing good comprehension; paraphrasing inconsistent, some extraneous detail, main ideas mostly correct with minor omissions, connected but not tightly synthesized.
2 = partial summary showing basic comprehension; no clear distinction between main points and details, relies heavily on repeating source wording rather than paraphrasing, followable only with effort.
1 = relevant but not meaningfully summarized; limited comprehension; disconnected excerpts without synthesis; main ideas omitted or misrepresented.
0 = too limited to score higher; shows no comprehension of the source.

Form (0-1): 1 = written as one single complete sentence, 5-75 words, not in capitals. 0 = not one single sentence, under 5 or over 75 words, or written in capitals.

Grammar (0-2): 2 = correct grammatical structure. 1 = grammatical errors present but don't hinder communication. 0 = defective grammatical structure that could hinder communication.

Vocabulary (0-2): 2 = appropriate word choice. 1 = lexical errors present but don't hinder communication. 0 = defective word choice that could hinder communication.

Convert the raw total (max 9) to a scaled practice score out of 90, proportionally: 8-9/9 is high 80s-90, 6-7/9 is 60s-70s, 3-5/9 is 40s-50s, cascaded zero is 10-20. This is a simplified per-response practice estimate, not the official multi-question overall PTE score.""",
    },
    "sst": {
        "label": "Summarize Spoken Text",
        "context_label": "Lecture transcript (what you'll listen to)",
        "context_placeholder": "Paste or write the lecture/talk transcript here...",
        "response_label": "Your summary (50–70 words)",
        "response_placeholder": "Write a 50–70 word paragraph summarizing the key points of the lecture...",
        "word_range": (50, 70),
        "word_hint": "Aim for 50–70 words. Under 40 or over 100 scores zero.",
        "time_limit_min": 10,
        "context_height": 180,
        "criteria": [
            ("content", "Content", 4),
            ("form", "Form", 2),
            ("grammar", "Grammar", 2),
            ("vocabulary", "Vocabulary", 2),
            ("spelling", "Spelling", 2),
        ],
        "rubric": """You are an experienced PTE Academic examiner. Score this Summarize Spoken Text response using the same trait structure and point scale as Pearson's official PTE Academic Score Guide (raw total = 12).

CASCADE RULE: if Content = 0 or Form = 0, every trait for this response scores 0.

Content (0-4): how well the summary captures the lecture.
4 = comprehensive, accurate summary showing full comprehension; effective paraphrasing, extraneous detail removed, main ideas synthesized concisely and coherently, smooth flow with varied connectives.
3 = adequate summary showing good comprehension; paraphrasing inconsistent, some extraneous detail, main ideas mostly correct with minor omissions, connected but not tightly synthesized.
2 = partial summary showing basic comprehension; no clear distinction between main points and details, relies heavily on repeating source wording rather than paraphrasing, followable only with effort.
1 = relevant but not meaningfully summarized; limited comprehension; disconnected excerpts without synthesis; main ideas omitted or misrepresented.
0 = too limited to score higher; shows no comprehension of the source.

Form (0-2): 2 = 50-70 words. 1 = 40-49 or 71-100 words. 0 = under 40 or over 100 words, all-caps, no punctuation, or bullet points/very short sentences only.

Grammar (0-2): 2 = correct grammatical structure. 1 = grammatical errors present but don't hinder communication. 0 = defective grammatical structure that could hinder communication.

Vocabulary (0-2): 2 = appropriate word choice. 1 = lexical errors present but don't hinder communication. 0 = defective word choice that could hinder communication.

Spelling (0-2): 2 = correct spelling. 1 = one spelling error. 0 = more than one spelling error.

Convert the raw total (max 12) to a scaled practice score out of 90, proportionally: 10-12/12 is high 80s-90, 8-9/12 is 60s-70s, 4-7/12 is 40s-50s, cascaded zero is 10-20. This is a simplified per-response practice estimate, not the official multi-question overall PTE score.""",
    },
    "dictation": {
        "label": "Write From Dictation",
        "response_label": "Type exactly what you hear",
        "response_placeholder": "Listen carefully, then type the sentence exactly as you heard it...",
        "time_limit_min": 1,
        "no_llm": True,
    },
}

for _cfg in TASK_CONFIGS.values():
    if "criteria" in _cfg:
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
        max_tokens=5000,
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


def render_timer(minutes: int, key: str, auto_start: bool = False):
    """A self-contained countdown timer matching the official PTE time limit
    for this task. Runs in the browser (JS), independent of Streamlit reruns,
    so it keeps ticking while the person writes. If auto_start is True, it
    begins counting down immediately on mount (e.g. as soon as the task is
    opened), matching real exam behavior."""
    total_seconds = minutes * 60
    components.html(
        f"""
        <div style="font-family:Inter,sans-serif;display:flex;align-items:center;gap:12px;margin-bottom:8px;">
            <div id="clock_{key}" style="font-size:22px;font-weight:700;color:#0F172A;min-width:70px;
                font-variant-numeric:tabular-nums;">{minutes:02d}:00</div>
            <button id="startBtn_{key}" style="background:#2563EB;color:#FFFFFF;border:none;border-radius:6px;
                padding:6px 14px;font-weight:600;cursor:pointer;font-size:13px;">Start</button>
            <button id="pauseBtn_{key}" style="background:#FFFFFF;color:#0F172A;border:1px solid #E2E8F0;border-radius:6px;
                padding:6px 14px;font-weight:600;cursor:pointer;font-size:13px;">Pause</button>
            <button id="resetBtn_{key}" style="background:#FFFFFF;color:#0F172A;border:1px solid #E2E8F0;border-radius:6px;
                padding:6px 14px;font-weight:600;cursor:pointer;font-size:13px;">Reset</button>
            <span style="font-size:12px;color:#94A3B8;">Official time limit: {minutes} min</span>
        </div>
        <script>
        (function() {{
            try {{ window.speechSynthesis.cancel(); }} catch (e) {{}}
            try {{ window.parent.speechSynthesis.cancel(); }} catch (e) {{}}
            let remaining_{key} = {total_seconds};
            let interval_{key} = null;
            const clockEl = document.getElementById('clock_{key}');
            function render() {{
                const m = Math.floor(remaining_{key} / 60);
                const s = remaining_{key} % 60;
                clockEl.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                if (remaining_{key} <= 30) {{ clockEl.style.color = '#B91C1C'; }}
                else if (remaining_{key} <= 120) {{ clockEl.style.color = '#B45309'; }}
                else {{ clockEl.style.color = '#0F172A'; }}
                if (remaining_{key} <= 0) {{ clockEl.textContent = "Time's up"; }}
            }}
            function startTimer() {{
                if (interval_{key}) return;
                interval_{key} = setInterval(function() {{
                    if (remaining_{key} > 0) {{ remaining_{key} -= 1; render(); }}
                    else {{ clearInterval(interval_{key}); interval_{key} = null; }}
                }}, 1000);
            }}
            document.getElementById('startBtn_{key}').onclick = startTimer;
            document.getElementById('pauseBtn_{key}').onclick = function() {{
                clearInterval(interval_{key});
                interval_{key} = null;
            }};
            document.getElementById('resetBtn_{key}').onclick = function() {{
                clearInterval(interval_{key});
                interval_{key} = null;
                remaining_{key} = {total_seconds};
                render();
            }};
            render();
            if ({str(auto_start).lower()}) {{ startTimer(); }}
        }})();
        </script>
        """,
        height=50,
    )


def tts_button(text: str, key: str, button_label: str = "Play lecture aloud"):
    safe_text = json.dumps(text)
    safe_label = json.dumps(button_label)
    components.html(
        f"""
        <div style="font-family:Inter,sans-serif;">
        <button id="playBtn_{key}" style="background:#2563EB;color:#FFFFFF;border:1px solid #2563EB;border-radius:6px;
            padding:10px 18px;font-weight:500;cursor:pointer;"></button>
        <button id="stopBtn_{key}" style="background:#FFFFFF;color:#0F172A;border:1px solid #E2E8F0;border-radius:6px;
            padding:10px 18px;font-weight:500;cursor:pointer;margin-left:8px;">Stop</button>
        <script>
        (function() {{
            const text_{key} = {safe_text};
            document.getElementById('playBtn_{key}').textContent = {safe_label};

            // Pick the most natural-sounding English voice available in the
            // browser instead of whatever default the OS falls back to
            // (which is usually the flat, robotic-sounding one).
            function pickVoice() {{
                const voices = window.speechSynthesis.getVoices() || [];
                if (!voices.length) return null;
                const preferredNames = [
                    "Google US English", "Google UK English Female",
                    "Microsoft Aria Online (Natural) - English (United States)",
                    "Microsoft Ava Online (Natural) - English (United States)",
                    "Microsoft Guy Online (Natural) - English (United States)",
                    "Samantha", "Alex", "Karen", "Daniel"
                ];
                for (const name of preferredNames) {{
                    const v = voices.find(v => v.name === name);
                    if (v) return v;
                }}
                let v = voices.find(v => /Natural|Neural/i.test(v.name) && /^en/i.test(v.lang));
                if (v) return v;
                v = voices.find(v => /Google/i.test(v.name) && /^en/i.test(v.lang));
                if (v) return v;
                v = voices.find(v => /^en-US|^en_US/i.test(v.lang));
                if (v) return v;
                v = voices.find(v => /^en/i.test(v.lang));
                return v || voices[0];
            }}

            function speak() {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(text_{key});
                const voice = pickVoice();
                if (voice) {{ u.voice = voice; u.lang = voice.lang; }}
                // Slightly slower than default with natural pitch reads far
                // less "robotic" than the browser's flat default rate.
                u.rate = 0.93;
                u.pitch = 1.0;
                u.volume = 1;
                window.speechSynthesis.speak(u);
            }}

            document.getElementById('playBtn_{key}').onclick = function() {{
                if (window.speechSynthesis.getVoices().length === 0) {{
                    window.speechSynthesis.onvoiceschanged = speak;
                    // Fallback in case the event never fires on this browser.
                    setTimeout(speak, 250);
                }} else {{
                    speak();
                }}
            }};
            document.getElementById('stopBtn_{key}').onclick = function() {{
                window.speechSynthesis.cancel();
            }};

            // Stop playback automatically the moment the user clicks a tab
            // (New attempt / History), a sidebar nav button, or navigates
            // away — otherwise audio keeps playing under a different screen.
            // Streamlit's own st.tabs switch is handled client-side without
            // a script rerun, so this listener is attached on the parent
            // document rather than relying on this component unmounting.
            try {{
                if (window.parent.__write90StopSpeechHandler) {{
                    window.parent.document.removeEventListener(
                        'click', window.parent.__write90StopSpeechHandler, true
                    );
                }}
                const stopHandler = function(e) {{
                    const target = e.target.closest && e.target.closest(
                        '[role="tab"], [data-testid="stSidebar"] button, .stButton button'
                    );
                    if (target) {{
                        try {{ window.parent.speechSynthesis.cancel(); }} catch (err) {{}}
                    }}
                }};
                window.parent.__write90StopSpeechHandler = stopHandler;
                window.parent.document.addEventListener('click', stopHandler, true);
            }} catch (err) {{}}
        }})();
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
    st.caption("Your essay, kept as your own, with every error fixed.")
    st.markdown(f'<div class="pte-corrected-box">{esc(result.get("corrected_response",""))}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Model 90-score response")
    st.caption("An independent example response written fresh for this prompt — for comparison, not a correction of yours.")
    st.markdown(f'<div class="pte-corrected-box">{esc(result.get("model_response",""))}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Tips to work on")
    for tip in result.get("tips", []):
        st.markdown(f'<div class="pte-tip">{esc(tip)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Write From Dictation — scored locally (no LLM call needed) by diffing the
# typed response against the original sentence at the word level.
# ---------------------------------------------------------------------------
def _extract_words(text: str) -> list:
    return re.findall(r"[A-Za-z']+", text or "")


def compute_dictation_result(original: str, response: str) -> dict:
    orig_words = _extract_words(original)
    resp_words = _extract_words(response)
    orig_norm = [w.lower() for w in orig_words]
    resp_norm = [w.lower() for w in resp_words]

    matcher = difflib.SequenceMatcher(None, orig_norm, resp_norm)
    orig_display, resp_display = [], []
    matched = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            matched += (i2 - i1)
            for k in range(i1, i2):
                orig_display.append({"word": orig_words[k], "status": "correct"})
            for k in range(j1, j2):
                resp_display.append({"word": resp_words[k], "status": "correct"})
        elif tag == "replace":
            for k in range(i1, i2):
                orig_display.append({"word": orig_words[k], "status": "missing"})
            for k in range(j1, j2):
                resp_display.append({"word": resp_words[k], "status": "wrong"})
        elif tag == "delete":
            for k in range(i1, i2):
                orig_display.append({"word": orig_words[k], "status": "missing"})
        elif tag == "insert":
            for k in range(j1, j2):
                resp_display.append({"word": resp_words[k], "status": "extra"})

    total = len(orig_words)
    accuracy = (matched / total) if total else 0
    overall = max(0, min(90, round(accuracy * 90)))
    return {
        "overall": overall,
        "matched": matched,
        "total": total,
        "orig_display": orig_display,
        "resp_display": resp_display,
    }


def render_dictation_result(result: dict):
    overall = result.get("overall", 0)
    matched = result.get("matched", 0)
    total = result.get("total", 0)
    pct = round(matched / total * 100) if total else 0

    st.markdown(
        f'<div class="pte-score-box"><span class="num">{overall}</span><br>'
        f'<span class="of90">out of 90</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div style="text-align:center;">{score_badge(overall)}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="pte-summary">You correctly placed {matched} of {total} words ({pct}% word accuracy).</p>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("Correct sentence")
    parts = []
    for item in result.get("orig_display", []):
        cls = "ok-text" if item["status"] == "correct" else "orig-bad"
        parts.append(f'<span class="{cls}">{esc(item["word"])}</span>')
    st.markdown(f'<div class="pte-corrected-box">{" ".join(parts)}</div>', unsafe_allow_html=True)
    st.caption("Struck-through words are ones you missed or got wrong.")

    st.subheader("What you typed")
    parts2 = []
    for item in result.get("resp_display", []):
        cls = "ok-text" if item["status"] == "correct" else "orig-bad"
        parts2.append(f'<span class="{cls}">{esc(item["word"])}</span>')
    st.markdown(f'<div class="pte-corrected-box">{" ".join(parts2) if parts2 else "(no words typed)"}</div>', unsafe_allow_html=True)
    st.caption("Red words were incorrect, out of place, or extra.")


def render_dictation_section(cfg: dict, conn):
    bank = DICTATION_SENTENCES
    idx_key = "bank_idx_dictation"
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
    st.session_state[idx_key] %= len(bank)
    current_idx = st.session_state[idx_key]
    sentence = bank[current_idx]

    sub_new, sub_history = st.tabs(["New attempt", "History"])

    with sub_new:
        left, right = st.columns([1.3, 1])

        with left:
            render_timer(cfg["time_limit_min"], key=f"dictation_{current_idx}", auto_start=False)
            st.write("")

            nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 3])
            with nav_col1:
                if st.button("Previous", key="prev_dictation", use_container_width=True):
                    st.session_state[idx_key] = (current_idx - 1) % len(bank)
                    st.rerun()
            with nav_col2:
                if st.button("Next", key="next_dictation", use_container_width=True):
                    st.session_state[idx_key] = (current_idx + 1) % len(bank)
                    st.rerun()
            with nav_col3:
                st.caption(f"Sentence {current_idx + 1} of {len(bank)}")

            st.markdown("**Listen, then type exactly what you hear**")
            tts_button(sentence, key=f"dictation_{current_idx}", button_label="Play sentence")
            st.caption("On the real exam you hear it once — replay as much as you like while practicing.")

            response_text = st.text_area(
                cfg["response_label"],
                height=100,
                placeholder=cfg["response_placeholder"],
                key=f"resp_dictation_{current_idx}",
            )
            submit = st.button(
                "Check My Sentence",
                type="primary",
                key=f"submit_dictation_{current_idx}",
                disabled=not response_text.strip(),
            )

        with right:
            st.markdown(
                '<div class="w90-guide-box"><h4>Verification Guide</h4>'
                '<div class="w90-guide-item"><b>Word accuracy</b> — every correctly placed word counts toward your score.</div>'
                '<div class="w90-guide-item"><b>Spelling</b> — try to match each word exactly.</div>'
                '<div class="w90-guide-item"><b>Word order</b> — words must appear in the right position in the sentence.</div>'
                '<div style="font-size:11.5px;color:#1E3A8A;margin-top:10px;padding-top:8px;'
                'border-top:1px solid #BFDBFE;">Scored locally by comparing your response to the '
                'original sentence word-for-word — no API call needed.</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        if not response_text.strip():
            st.info("Play the sentence, type what you heard, then click **Check My Sentence**.")
        elif submit:
            result = compute_dictation_result(sentence, response_text)
            save_submission(conn, st.session_state["user"], "dictation", sentence, response_text, result)
            render_dictation_result(result)
        else:
            st.info("Click **Check My Sentence** to see your score.")

    with sub_history:
        history = get_history(conn, st.session_state["user"], "dictation")
        if not history:
            st.info("No attempts yet. Your history for this task will appear here.")
        else:
            scores = [row[3] for row in history][::-1]
            if len(scores) > 1:
                fixed_score_chart(scores)
            for created_at, hcontext, hresponse, hoverall, hresult_json in history:
                with st.expander(f"{created_at[:16].replace('T',' ')} — Score: {hoverall}/90"):
                    if hcontext:
                        st.caption(f"Correct sentence: {hcontext}")
                    st.write(hresponse)
                    try:
                        render_dictation_result(json.loads(hresult_json))
                    except Exception:
                        st.write("(Could not load detailed breakdown for this entry.)")


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
conn = get_db()

inject_sidebar_toggle()

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

    st.markdown("---")
    st.caption("NAVIGATE")
    nav_options = list(TASK_CONFIGS.keys()) + ["progress"]
    nav_labels = {**{k: v["label"] for k, v in TASK_CONFIGS.items()}, "progress": "My Progress"}
    if "current_section" not in st.session_state:
        st.session_state["current_section"] = "essay"
    for opt in nav_options:
        is_active = st.session_state["current_section"] == opt
        if st.button(
            nav_labels[opt],
            key=f"nav_{opt}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state["current_section"] = opt
            st.rerun()

# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------
render_top_banner()

current_section = st.session_state["current_section"]

if current_section == "dictation":
    cfg = TASK_CONFIGS["dictation"]
    render_dictation_section(cfg, conn)

elif current_section in TASK_CONFIGS:
    task_key = current_section
    cfg = TASK_CONFIGS[task_key]

    # Every task now draws from a built-in question bank only — no free-text
    # prompt/passage entry. Essay has its own 20-question bank; Summarize
    # Written Text and Summarize Spoken Text share the practice-passage bank
    # (used as a reading passage for SWT, and as a lecture transcript for SST).
    bank = ESSAY_QUESTIONS if task_key == "essay" else SWT_PASSAGES

    idx_key = f"bank_idx_{task_key}"
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0
    st.session_state[idx_key] %= len(bank)
    current_idx = st.session_state[idx_key]
    context_text = bank[current_idx]

    sub_new, sub_history = st.tabs(["New attempt", "History"])

    with sub_new:
        left, right = st.columns([1.3, 1])

        with left:
            # Timer key includes the question index so it resets fresh for
            # each new question, and auto-starts the moment this task/question
            # is opened — matching real exam behavior.
            render_timer(cfg["time_limit_min"], key=f"{task_key}_{current_idx}", auto_start=True)
            st.write("")

            nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 3])
            with nav_col1:
                if st.button("Previous", key=f"prev_{task_key}", use_container_width=True):
                    st.session_state[idx_key] = (current_idx - 1) % len(bank)
                    st.rerun()
            with nav_col2:
                if st.button("Next", key=f"next_{task_key}", use_container_width=True):
                    st.session_state[idx_key] = (current_idx + 1) % len(bank)
                    st.rerun()
            with nav_col3:
                st.caption(f"Question {current_idx + 1} of {len(bank)}")

            st.markdown(f'**{cfg["context_label"]}**')
            st.markdown(
                f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
                f'padding:14px 16px;font-size:14px;color:#0F172A;margin-bottom:10px;'
                f'max-height:{cfg["context_height"]}px;overflow-y:auto;">{esc(context_text)}</div>',
                unsafe_allow_html=True,
            )
            if task_key == "sst":
                tts_button(context_text, key=f"{task_key}_{current_idx}")

            response_text = st.text_area(cfg["response_label"], height=220,
                                          placeholder=cfg["response_placeholder"],
                                          key=f"resp_{task_key}_{current_idx}")
            wc = word_count(response_text)
            char_count = len(response_text)
            lo, hi = cfg["word_range"]
            wc_color = "green" if lo <= wc <= hi else ("orange" if wc else "gray")
            st.markdown(
                f'<div class="w90-metric-stack">METRIC STACK: {wc} WORDS | CHARACTER BLOCKS: {char_count}</div>',
                unsafe_allow_html=True,
            )
            st.caption(cfg["word_hint"])
            submit = st.button("Mark My Response Against Rubric", type="primary", key=f"submit_{task_key}_{current_idx}",
                                disabled=not response_text.strip())

        with right:
            total_max = sum(m for _, _, m in cfg["criteria"])
            guide_html = '<div class="w90-guide-box"><h4>Verification Guide</h4>'
            for key, name, max_score in cfg["criteria"]:
                guide_html += f'<div class="w90-guide-item"><b>{esc(name)}</b> — up to {max_score} pts</div>'
            guide_html += (
                f'<div style="font-size:11.5px;color:#1E3A8A;margin-top:10px;padding-top:8px;'
                f'border-top:1px solid #BFDBFE;">Trait names and point scale (raw total: {total_max}) '
                f'match Pearson\'s official PTE Academic Score Guide.</div>'
            )
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

elif current_section == "progress":
    all_hist = get_all_history(conn, st.session_state["user"])
    if not all_hist:
        st.info("Grade a few responses across the sections in the sidebar and your overall progress will show up here.")
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
