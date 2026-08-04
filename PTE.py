import difflib
import hashlib
import json
import re
import secrets
from datetime import date, datetime, timedelta, timezone

import streamlit as st
import streamlit.components.v1 as components
import extra_streamlit_components as stx
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
    [data-testid="stSidebar"] > div:first-child { padding-top: 8px; }
    [data-testid="stSidebar"] * { color: var(--text) !important; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: var(--text-secondary) !important; }
    [data-testid="stSidebar"] .stButton > button { background-color: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; color: var(--text) !important; }
    [data-testid="stSidebar"] .stButton > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
    [data-testid="stSidebar"] .stTextInput input { background-color: #FFFFFF !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
    [data-testid="stSidebar"] [data-testid="stProgress"] { background-color: transparent !important; }
    [data-testid="stSidebar"] [data-testid="stProgress"] > div { background-color: var(--border) !important; border-radius: 4px; overflow: hidden; }
    [data-testid="stSidebar"] [data-testid="stProgress"] [role="progressbar"] { background-color: var(--accent) !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { color: var(--text-secondary) !important; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }

    .stTextArea textarea { background-color: #FFFFFF !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 8px; font-size: 14.5px; padding: 12px 14px !important; }
    /* Hide Streamlit's "Press Ctrl+Enter to apply" / "Press Enter to apply"
       hint that appears under text inputs while typing — covers the testid
       used in current versions plus older fallback class names. */
    [data-testid="InputInstructions"] { display: none !important; visibility: hidden !important; }
    [data-testid="stTextAreaInstructions"] { display: none !important; visibility: hidden !important; }
    [data-testid="stWidgetInstructions"] { display: none !important; visibility: hidden !important; }
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
    .stButton > button { background-color: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; border-radius: 8px !important; font-weight: 500; transition: all 0.15s ease; }
    .stButton > button:hover, .stButton > button:hover * { color: var(--accent) !important; }
    .stButton > button:hover { border-color: var(--accent) !important; }
    .stButton > button[kind="primary"], .stButton > button[kind="primary"] * { color: #FFFFFF !important; }
    .stButton > button[kind="primary"] {
        background-color: var(--accent) !important;
        border: 1.5px solid var(--accent-hover) !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 6px rgba(37,99,235,0.25);
    }
    .stButton > button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover * { color: #FFFFFF !important; }
    .stButton > button[kind="primary"]:hover {
        background-color: var(--accent-hover) !important;
        border-color: #1E40AF !important;
        box-shadow: 0 4px 10px rgba(37,99,235,0.35);
        transform: translateY(-1px);
    }

    .stRadio label, .stCheckbox label { color: var(--text) !important; }
    [data-testid="stProgress"] { background-color: transparent !important; }
    [data-testid="stProgress"] > div { background-color: #E2E8F0 !important; border-radius: 4px; overflow: hidden; }
    [data-testid="stProgress"] [role="progressbar"] { background-color: var(--accent) !important; }

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

    /* ---- Chat / Ask the Tutor — styled to match the rest of the app
       instead of Streamlit's default chat bubble widget, which ignores
       our theme entirely (fixed avatars, dark-mode-leaning colors). ---- */
    .w90-chat-row { display: flex; margin-bottom: 14px; }
    .w90-chat-row.user { justify-content: flex-end; }
    .w90-chat-row.assistant { justify-content: flex-start; }
    .w90-chat-bubble {
        max-width: 78%; padding: 12px 16px; border-radius: 12px;
        font-size: 14px; line-height: 1.6; white-space: pre-wrap;
    }
    .w90-chat-bubble.user {
        background-color: var(--accent) !important; color: #FFFFFF !important;
        border-bottom-right-radius: 3px;
    }
    .w90-chat-bubble.assistant {
        background: var(--guide-bg) !important; color: var(--text) !important;
        border: 1px solid #BFDBFE; border-bottom-left-radius: 3px;
    }
    .w90-chat-label {
        font-size: 10.5px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
        color: var(--text-secondary) !important; margin-bottom: 3px; display: block;
    }
    .w90-chat-row.user .w90-chat-label { text-align: right; color: #93C5FD !important; }
    .w90-chat-empty {
        background: var(--guide-bg); border: 1px dashed #BFDBFE; border-radius: 10px;
        padding: 16px 18px; font-size: 13.5px; color: #1E3A8A !important; line-height: 1.6;
    }
    [data-testid="stChatInput"] { background-color: transparent !important; border-top: 1px solid var(--border); padding-top: 10px; }
    [data-testid="stChatInput"] textarea { background-color: #FFFFFF !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
    [data-testid="stChatInput"] textarea::placeholder { color: #94A3B8 !important; }
    [data-testid="stChatInput"] button { background-color: var(--accent) !important; }
    [data-testid="stChatInput"] button svg { fill: #FFFFFF !important; }
    [data-testid="stBottomBlockContainer"] { background-color: var(--bg) !important; }

    .w90-pro-banner {
        background-color: #FFF7ED;
        border: 1px solid #FDBA74;
        border-radius: 12px;
        padding: 18px 24px;
        margin-top: 32px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    }
    .w90-pro-banner .w90-pro-title { color: #9A3412 !important; font-weight: 700; font-size: 16px; margin: 0; }
    .w90-pro-banner .w90-pro-sub { color: #C2410C !important; font-size: 13px; margin-top: 2px; }

    .w90-pro-card {
        background: #FFF7ED; border: 1px solid #FDBA74; border-radius: 12px;
        padding: 28px 32px; text-align: center; max-width: 420px; margin: 12px auto;
    }
    .w90-pro-price { font-size: 40px; font-weight: 700; color: #9A3412 !important; }
    .w90-pro-price span { font-size: 15px; font-weight: 500; color: #C2410C !important; }
    .w90-pro-feature { font-size: 14px; color: #7C2D12 !important; text-align: left; padding: 4px 0; }

    /* Mobile responsiveness */
    @media (max-width: 640px) {
        .w90-banner { padding: 14px 18px; }
        .w90-banner .w90-title { font-size: 20px; }
        .w90-banner .w90-tag { font-size: 12px; }
        .w90-banner .w90-badge { font-size: 11px; padding: 6px 12px; }
        .pte-score-box .num { font-size: 36px; }
        .w90-pro-card { padding: 20px 18px; max-width: 100%; }
        .w90-pro-price { font-size: 32px; }
        .w90-pro-banner { padding: 14px 16px; flex-direction: column; align-items: flex-start; }
        .stButton > button { font-size: 13.5px; padding: 8px 10px !important; }
        .stTextArea textarea { font-size: 16px; } /* prevents iOS auto-zoom on focus */
    }
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
                    'position:fixed', 'top:78px', 'left:12px', 'z-index:2147483647',
                    'background:#2563EB', 'color:#FFFFFF', 'border:none',
                    'border-radius:8px', 'width:34px', 'height:34px',
                    'font-size:16px', 'line-height:1', 'cursor:pointer',
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
    'Renewable energy sources such as solar and wind power have grown rapidly over the past decade, driven by falling technology costs and increasing government support across both developed and developing economies. Unlike fossil fuels, these sources produce little to no greenhouse gas emissions during operation, making them central to global efforts to combat climate change and meet international emissions targets set under agreements such as the Paris Accord. However, their reliance on weather conditions creates challenges for maintaining a stable electricity supply, since solar output drops at night and wind generation can fluctuate significantly from one day to the next, prompting significant investment in battery storage and smart grid technologies capable of balancing supply and demand in real time. Many energy analysts now predict that renewables will overtake coal and gas as the dominant source of global electricity generation within the next two decades, provided that storage costs continue to decline at their current pace and governments maintain supportive regulatory frameworks. Utilities in several countries have already begun retiring older fossil-fuel plants ahead of schedule as renewable capacity expands, though grid operators caution that a fully renewable system will still require significant transmission infrastructure upgrades to move power efficiently from generation sites to population centers.',
    'Remote work, once a rare arrangement limited mainly to freelancers and a small number of technology firms, became mainstream during the global disruptions of the early 2020s and has remained widespread in many industries ever since. Proponents argue that it increases employee flexibility, reduces commuting time and associated carbon emissions, and can improve productivity for tasks requiring deep, uninterrupted concentration away from a noisy office environment. Critics, however, point to challenges in maintaining team cohesion, onboarding new employees effectively, and separating work from personal life, with some studies suggesting that isolation and blurred boundaries can contribute to burnout over extended periods. As a result, many organizations have adopted hybrid models that combine in-office collaboration on select days with remote flexibility on others, attempting to capture the benefits of both approaches while minimizing their respective drawbacks. Human resources researchers note that the long-term success of hybrid arrangements depends heavily on deliberate management practices, including clear communication norms and structured opportunities for informal social interaction, rather than simply splitting the week between locations without further planning. Commercial real estate markets in many major cities have also had to adapt to reduced office demand as a consequence of this broader shift in working patterns.',
    'Urban planners increasingly recognize that poorly designed cities contribute to a wide range of problems, from traffic congestion and air pollution to social isolation and reduced physical activity among residents. Compact, walkable neighborhoods with mixed residential and commercial zoning tend to reduce reliance on private vehicles, lower emissions, and foster stronger community interaction by placing shops, schools, and workplaces within easy walking or cycling distance of homes. In contrast, sprawling suburban developments built primarily around car travel often require long commutes and limit spontaneous social contact between residents, since daily life is organized around private vehicle trips rather than shared public spaces. Several cities around the world have begun redesigning neighborhoods around this walkability principle, incorporating wider footpaths, dedicated cycling lanes, and public plazas intended to encourage walking and casual interaction rather than car dependency. Early evaluations of these redesigned districts suggest measurable improvements in both physical activity levels and reported community wellbeing among residents, though implementing such changes in already-built cities often requires significant, and sometimes politically contentious, investment in reconfiguring existing streets and public land. Advocates argue that the long-term health and environmental savings ultimately justify this upfront cost.',
    'The rapid advancement of artificial intelligence has raised significant ethical questions about accountability, bias, and transparency in automated decision-making systems that increasingly influence important aspects of everyday life. Because many AI systems learn from historical data, they can inadvertently reproduce or even amplify existing societal biases, particularly in sensitive areas such as hiring, lending, and law enforcement, where biased outcomes can have serious consequences for the individuals affected. Researchers and policymakers are now exploring frameworks for auditing algorithms before deployment and requiring companies to disclose how automated decisions are made, aiming to give affected individuals a meaningful ability to understand and challenge outcomes they believe to be unfair. Some experts argue that without such oversight, the broader societal benefits of AI could be undermined by a loss of public trust and an increase in unintended discriminatory outcomes that disproportionately affect already disadvantaged groups. Several governments have begun drafting binding regulations that would require high-risk AI systems to undergo independent testing before being deployed commercially, though critics warn that overly rigid rules could slow beneficial innovation, creating an ongoing tension between fostering technological progress and protecting the public from potential algorithmic harm.',
    "Biodiversity loss has accelerated markedly over the past century, driven primarily by habitat destruction, pollution, overexploitation of natural resources, and climate change acting in combination across ecosystems worldwide. Scientists warn that the current rate of species extinction is significantly higher than the natural background rate observed throughout most of Earth's history, a trend some researchers describe as an unfolding sixth mass extinction event driven largely by human activity. Conservation efforts, including protected nature reserves and species reintroduction programs, have shown localized success in stabilizing or even reversing declines for specific species, but many experts argue that addressing the root causes, particularly deforestation and unsustainable agricultural expansion, is essential for any genuine long-term recovery of global biodiversity. International cooperation on this issue remains difficult to achieve, as conservation priorities often conflict with short-term economic development goals in many regions where local communities depend directly on land conversion for their livelihoods. Recent international agreements have set ambitious targets for protecting a much larger share of the planet's land and ocean area by mid-century, though independent monitoring organizations note that funding and enforcement mechanisms currently fall well short of what would be needed to meet these targets.",
    "Sleep researchers have found that chronic sleep deprivation is associated with a wide range of negative health outcomes, including impaired memory consolidation, weakened immune function, and an increased risk of cardiovascular disease and metabolic disorders such as type two diabetes. Despite this growing body of evidence, modern lifestyles characterized by long working hours, late-night screen use, and irregular schedules continue to erode average sleep duration in many industrialized countries, with surveys suggesting that a substantial share of adults now routinely sleep less than the amount recommended by health authorities. Some employers have begun experimenting with flexible start times and dedicated nap facilities in response to growing awareness of sleep's crucial role in productivity, decision-making, and overall workplace safety, particularly in industries involving shift work or operation of heavy machinery. Public health campaigns in several countries have also started promoting sleep hygiene alongside more traditional messaging about diet and exercise, treating adequate rest as an equally important pillar of preventive healthcare. Nevertheless, such initiatives remain far from universal across industries, and researchers caution that meaningful improvement will likely require broader cultural shifts in how societies value rest relative to constant productivity and availability.",
    'Financial literacy, broadly defined as the ability to understand and effectively use various financial skills such as budgeting, saving, and investing, remains uneven across populations despite its growing importance in an increasingly complex economic environment shaped by consumer credit, digital payments, and volatile investment markets. Studies have consistently shown that individuals with stronger financial literacy tend to save more consistently, carry less high-interest debt, and plan more effectively for major life events such as retirement, reducing their vulnerability to financial shocks. In response to these findings, some education systems have begun incorporating personal finance education into secondary school curricula, aiming to equip young people with practical skills before they encounter major financial decisions such as student loans or first mortgages. Critics, however, argue that such programs are often too brief or overly theoretical to meaningfully change long-term financial behavior, and that structural factors such as stagnant wages and rising living costs may matter more than individual knowledge in determining financial outcomes. Financial regulators in several countries have therefore begun exploring complementary approaches, including simplified product disclosures and default enrollment in retirement savings plans, designed to improve outcomes even among consumers who never receive formal financial education.',
    "Space exploration has entered a new era characterized by increasing involvement from private companies alongside traditional government space agencies that historically held a near-monopoly on launch capability. This shift has substantially reduced the cost of launching satellites and cargo into orbit, enabling more frequent missions and opening up possibilities for commercial activities such as space tourism, in-orbit manufacturing, and asteroid mining that were previously considered far beyond economic feasibility. Critics caution that the growing number of private launches raises concerns about space debris accumulation and regulatory oversight, since no single international body currently has comprehensive authority over commercial space activity, leaving a patchwork of national regulations that struggle to keep pace with the industry's rapid growth. Proponents counter that competition among private firms has accelerated innovation at a pace government agencies operating alone could not have matched, driving down costs and shortening development timelines for new launch vehicles. Several nations are now also pursuing renewed lunar exploration programs, partly in partnership with private contractors, with the stated long-term goal of establishing a sustained human presence on the Moon as a stepping stone toward eventual crewed missions to Mars.",
    'Antibiotic resistance has emerged as one of the most pressing challenges in modern medicine, driven by decades of overuse and misuse of antibiotics in both healthcare settings and agriculture, where the drugs are often administered to livestock to promote growth rather than to treat active infection. Bacteria that survive exposure to these drugs can pass resistant traits to future generations through both reproduction and horizontal gene transfer, gradually rendering once-effective treatments useless against infections that were previously considered routine and easily managed. Public health officials warn that without coordinated global action to reduce unnecessary prescriptions and develop new classes of antibiotics, routine infections and standard surgical procedures could become significantly more dangerous within a generation, effectively reversing decades of progress in modern medicine. Some pharmaceutical companies have scaled back antibiotic research in favor of more profitable drug categories, since new antibiotics are typically used sparingly to preserve their effectiveness, creating a difficult economic incentive problem that governments are now attempting to address through targeted subsidies and guaranteed purchase agreements. Meanwhile, researchers continue to explore alternative approaches, including bacteriophage therapy and novel antimicrobial compounds derived from previously unstudied environments such as deep soil and marine sediments.',
    'The gig economy, characterized by short-term contracts and freelance work facilitated by digital platforms that connect workers directly with customers, has expanded rapidly over the past fifteen years across sectors ranging from transportation and food delivery to freelance creative and technical services. Supporters argue it offers workers greater flexibility and access to income opportunities that traditional employment structures do not readily provide, particularly for individuals balancing caregiving responsibilities or pursuing education alongside part-time earning. Critics counter that gig workers often lack the job security, employer-provided benefits, and legal protections afforded to full-time employees, creating a growing segment of the workforce that remains vulnerable to sudden income loss and limited recourse in disputes with platform companies. Several jurisdictions have begun experimenting with new intermediate classifications of employment specifically designed to address this gap, offering gig workers certain protections such as minimum earnings guarantees or access to portable benefits without fully reclassifying them as traditional employees. Legal battles over worker classification continue in many countries, as platform companies argue that reclassification would undermine the flexible business model that both workers and consumers have come to rely on, while labor advocates maintain that current arrangements shift too much financial risk onto individual workers.',
    'Coral reefs, though covering less than one percent of the ocean floor, support roughly a quarter of all marine species at some stage of their life cycle, making them among the most biodiverse and ecologically valuable ecosystems on the planet. Rising ocean temperatures linked to climate change have triggered widespread coral bleaching events, in which corals expel the symbiotic algae that provide them with nutrients and vibrant color, often leading to mass die-offs if warmer conditions persist for extended periods without sufficient time for recovery. Marine biologists are experimenting with heat-resistant coral strains, selectively bred or genetically modified to withstand higher temperatures, in an effort to preserve reef ecosystems as ocean temperatures continue to rise over the coming decades. These restoration efforts have shown promising early results in controlled trials, though scientists caution that such interventions can only complement, not replace, the more fundamental need to reduce global greenhouse gas emissions and limit further ocean warming. Coastal communities that depend on reef tourism and fisheries for their economic livelihoods have increasingly become active partners in these conservation efforts, recognizing that reef degradation poses a direct and substantial threat to their long-term economic stability.',
    'Microplastics, tiny fragments of plastic less than five millimeters in size, have been detected in nearly every corner of the globe, from remote mountain snow and Arctic ice cores to deep ocean trenches thousands of meters below the surface. These particles originate from the gradual breakdown of larger plastic waste as well as from consumer products such as synthetic clothing fibers released during washing and cosmetic microbeads once commonly used in exfoliating products before many were banned. Although research into the health effects of microplastic ingestion in humans is still in its relatively early stages, scientists have already documented their presence in human blood, lung tissue, and other organs, prompting growing calls for stricter regulation of plastic production and improved waste management infrastructure worldwide. Some researchers are particularly concerned about the potential for microplastics to act as vectors for other harmful chemicals, since plastic particles can absorb and concentrate pollutants already present in the environment before being ingested by marine life and, eventually, humans further up the food chain. Several countries have begun restricting specific sources of microplastic pollution, though comprehensive solutions will likely require coordinated international action given how widely these particles disperse across ocean currents and atmospheric systems.',
    'Telemedicine, the practice of providing clinical healthcare remotely through video calls and digital monitoring tools, expanded dramatically in the wake of global health disruptions in the early 2020s and has continued to grow steadily since, reshaping how many patients access routine medical care. Advocates highlight its potential to improve healthcare access in rural and underserved areas where medical specialists are scarce, allowing patients to consult experts without the burden of long-distance travel that would otherwise be required for even routine follow-up appointments. Critics note important limitations in diagnosing conditions that require physical examination, specialized equipment, or laboratory testing that cannot currently be replicated through a remote consultation, meaning telemedicine works best as a complement rather than a complete substitute for in-person care. Many healthcare systems have settled on hybrid models that combine remote consultations for routine matters, medication management, and follow-up care with in-person visits reserved specifically for more complex diagnostic or procedural cases requiring hands-on assessment. Insurance providers and regulators in several countries have had to update longstanding reimbursement policies to accommodate this shift, and questions remain about how to ensure equitable access to telemedicine for patients who lack reliable internet connectivity or comfort with digital technology.',
    'The concept of a four-day work week has gained considerable traction among employers and policymakers seeking to improve worker wellbeing without sacrificing overall organizational productivity or competitiveness. Pilot programs conducted across several industries and countries have generally reported that employees maintain, or in some cases even increase, their output when given a shorter working week, attributing this outcome to reduced burnout, improved focus during working hours, and greater motivation stemming from additional personal time. Skeptics caution that the model may not translate easily to sectors requiring continuous staffing around the clock, such as healthcare, manufacturing, and emergency services, where reducing individual working hours could necessitate costly increases in hiring to maintain adequate coverage. Some economists also question whether productivity gains observed in relatively short pilot programs, often involving highly motivated volunteer companies, would persist if the model were mandated more broadly across an entire economy over a longer time horizon. Nevertheless, several national governments have begun exploring legislative frameworks that would encourage or gradually phase in shorter working weeks, viewing the policy as a potential tool for improving public health outcomes and addressing rising rates of workplace burnout across multiple industries.',
    "Vertical farming, the practice of growing crops in stacked layers within controlled indoor environments using artificial lighting and precisely regulated climate systems, has been proposed as a solution to the growing challenge of feeding an expanding urban population with increasingly limited arable land available near major cities. These systems use significantly less water than traditional agriculture, since irrigation can be precisely controlled and recycled within a closed system, and can operate year-round regardless of external weather conditions, insulating food production from droughts, floods, and seasonal variation. However, the high energy costs associated with artificial lighting and climate control have so far limited the technology's commercial profitability outside of high-value, fast-growing crops such as leafy greens, herbs, and certain berries, rather than staple grains that form the bulk of global caloric intake. Proponents argue that falling costs for renewable electricity and LED lighting efficiency could eventually make vertical farming viable for a broader range of crops, potentially reducing the environmental footprint associated with transporting fresh produce over long distances to urban centers. Critics remain skeptical that vertical farming can meaningfully address global food security challenges given its current scale and cost structure relative to conventional agriculture.",
    'Digital privacy has become an increasingly contentious issue as companies collect vast amounts of personal data to power targeted advertising, personalized recommendations, and increasingly sophisticated predictive services across nearly every online platform consumers regularly use. Consumer advocates argue that current regulations in many jurisdictions have not kept pace with the scale and sophistication of modern data collection practices, leaving individuals with limited meaningful control over how their information is gathered, stored, and ultimately used by third parties they may never directly interact with. Some governments have introduced stricter data protection laws requiring explicit consent for data collection and greater transparency about how personal information is processed, though enforcement across international borders remains a persistent challenge given how easily data can be transferred between jurisdictions with differing legal standards. Technology companies have responded with a mix of genuine policy changes and more superficial compliance measures, prompting ongoing debate among regulators about how to distinguish meaningful privacy protections from mere box-ticking exercises designed to satisfy the letter, rather than the spirit, of new regulations. Consumers themselves remain divided, with surveys suggesting many express concern about privacy in principle while continuing to use services that collect extensive personal data in practice.',
    'The rise of electric vehicles has prompted significant investment in charging infrastructure worldwide, though availability remains uneven between urban and rural areas, creating what some analysts describe as a widening geographic divide in practical access to electric mobility. While city dwellers increasingly have access to public charging stations at workplaces, shopping centers, and dedicated charging hubs, drivers in more remote regions often face long detours to find a compatible charger, a factor that continues to discourage adoption outside metropolitan centers where alternative fueling options remain limited. Automakers and governments alike have pledged substantial funding toward expanding charging networks, aiming to eliminate this disparity within the next decade through a combination of public investment and private industry partnerships. Battery technology has also improved considerably, extending the practical driving range of electric vehicles and reducing the anxiety some consumers report about running out of charge during longer journeys between charging opportunities. Nevertheless, questions remain about the capacity of existing electrical grids to handle widespread simultaneous vehicle charging, particularly during peak demand periods, prompting utilities in several regions to explore smart charging systems that can shift charging times to off-peak hours automatically.',
    "Museums around the world are increasingly using augmented reality technology to enhance visitor engagement, allowing patrons to view historical reconstructions, additional contextual information, or interactive animations simply by pointing a smartphone or dedicated device at a physical exhibit. Early studies suggest that these tools can meaningfully improve information retention among younger visitors, who often respond more enthusiastically to interactive digital content than to traditional static placards accompanying museum pieces. Some curators worry, however, that an overreliance on digital enhancement may distract from the direct, contemplative experience of viewing original artifacts and artworks, potentially reducing visitors' engagement with the physical objects themselves in favor of screen-mediated interaction. Museum administrators must also weigh the substantial upfront cost of developing and maintaining these digital experiences against uncertain long-term benefits, particularly as underlying technology evolves rapidly and today's cutting-edge installations risk becoming outdated within just a few years of deployment. Despite these concerns, many institutions view augmented reality as an essential tool for remaining relevant to younger audiences accustomed to interactive digital media, and some have begun collaborating directly with technology companies to develop increasingly sophisticated and immersive exhibition experiences.",
    'Water scarcity is projected to affect an increasing share of the global population as climate change alters precipitation patterns and population growth strains existing water supplies, particularly in arid and semi-arid regions already operating close to the limits of their available resources. Engineers have proposed a range of technical solutions, from large-scale desalination plants that convert seawater into fresh drinking water to more efficient drip irrigation techniques that dramatically reduce agricultural water waste compared to traditional flood irrigation methods. The high energy costs and substantial infrastructure investment required for many of these solutions mean that some of the most severely affected regions remain the least financially equipped to implement them at meaningful scale, creating a troubling mismatch between need and capacity. International development organizations have therefore begun prioritizing lower-cost interventions, such as rainwater harvesting systems and improved groundwater management practices, that can be implemented more affordably in resource-constrained settings while larger infrastructure projects are gradually developed. Water conflicts between neighboring regions or nations sharing the same river basins or aquifers have also become an increasing source of geopolitical tension, underscoring the need for cooperative water-sharing agreements alongside purely technical solutions to the underlying scarcity problem.',
    'The popularity of plant-based diets has grown substantially in recent years, driven by concerns about environmental sustainability, animal welfare, and personal health that have collectively shifted consumer preferences away from traditional meat-heavy diets in many wealthier nations. Food manufacturers have responded by developing an expanding range of meat and dairy alternatives designed to replicate the taste, texture, and cooking properties of traditional animal products as closely as possible, aiming to appeal to flexitarian consumers who are reducing rather than fully eliminating meat consumption. Nutritionists generally agree that well-planned plant-based diets can meet all necessary dietary requirements, including adequate protein and micronutrient intake, though they caution that highly processed plant-based substitutes are not automatically healthier than the animal products they replace, since some contain high levels of sodium and saturated fat. Agricultural economists note that a broader societal shift toward plant-based eating could have significant implications for land use, since livestock farming currently occupies a disproportionately large share of agricultural land relative to the calories and protein it ultimately provides compared with plant crops. Some traditional livestock farmers have begun diversifying into plant-based production themselves, seeking to remain economically viable as consumer preferences continue to evolve.',
    'Quantum computing, which exploits the properties of subatomic particles to perform certain calculations far faster than classical computers, has moved from purely theoretical physics into early commercial application over the past several years, attracting substantial investment from both governments and private technology firms. Unlike traditional bits, which represent either a zero or a one, quantum bits, or qubits, can exist in multiple states simultaneously through a property known as superposition, allowing quantum processors to explore many possible solutions to a problem at once rather than sequentially. This capability holds particular promise for fields such as drug discovery, cryptography, and materials science, where the sheer number of possible variable combinations quickly overwhelms even the most powerful conventional computing systems available today. However, quantum systems remain extremely sensitive to environmental interference, requiring near-absolute-zero temperatures and elaborate error-correction techniques to function reliably, since even minor vibrations or temperature fluctuations can disrupt delicate quantum states and introduce calculation errors. Meaning practical, large-scale quantum computers capable of consistently outperforming classical machines on real-world commercial problems are still likely years away, though incremental progress continues to be reported by leading research laboratories around the world.',
    "Ocean acidification, often described as the lesser-known twin of climate change, occurs as seawater absorbs increasing amounts of atmospheric carbon dioxide, gradually lowering the ocean's pH and altering its fundamental chemical balance in ways that affect marine life throughout the food web. This shift makes it considerably more difficult for shell-forming organisms such as oysters, corals, and certain plankton species to build and maintain their calcium carbonate structures, threatening the base of many marine food webs that larger species, including commercially important fish stocks, ultimately depend upon for survival. Because these small organisms underpin fisheries that hundreds of millions of people worldwide depend on for both food security and economic income, scientists warn that the economic consequences of continued acidification could be severe, particularly for coastal communities in developing nations with limited financial capacity to adapt to disrupted fisheries. Reducing carbon emissions remains the only genuine long-term solution to ocean acidification, though some researchers are also investigating selective breeding of more resilient shellfish strains capable of tolerating lower pH conditions as a stopgap measure while broader emissions reductions take effect over coming decades. Aquaculture operations in several regions have already reported reduced yields linked directly to acidification.",
    'The idea of a universal basic income, in which every citizen receives a regular, unconditional cash payment regardless of employment status or financial need, has attracted renewed interest as automation and artificial intelligence threaten to displace a growing share of routine jobs across multiple industries. Advocates argue that such a policy could reduce poverty, simplify bloated and often confusing welfare bureaucracies, and provide a financial cushion that allows people to pursue education, caregiving responsibilities, or entrepreneurial ventures without the immediate pressure of basic survival hanging over every decision. Critics, however, question whether the enormous cost of providing a universal payment to an entire population could be sustainably funded through taxation alone without significant economic disruption, and worry that guaranteed income might reduce incentives for some individuals to seek employment. Several pilot programs conducted in Finland, Kenya, and parts of the United States have produced mixed but generally encouraging results, showing modest improvements in wellbeing, mental health, and financial stability without the dramatic drop in overall employment rates that many critics had initially predicted. Policymakers in several other countries are now closely monitoring these results before deciding whether to pursue similar programs at a larger national scale.',
    "Artificial intelligence tools are increasingly being integrated into classrooms around the world, offering personalized tutoring, automated grading of routine assignments, and adaptive learning platforms that continuously adjust content difficulty based on individual student performance and areas of demonstrated weakness. Proponents argue that these tools can free teachers from repetitive administrative tasks, allowing more time for meaningful one-on-one instruction and relationship-building with students, while also giving learners immediate feedback that would be practically impossible for a single teacher to provide manually across an entire classroom. Skeptics, however, raise concerns about over-reliance on algorithmic assessment, the potential for these systems to entrench existing biases present in their training data, and the risk that students may lose valuable opportunities to develop independent critical thinking skills if AI tools consistently supply answers rather than genuinely guiding independent reasoning and problem-solving. Education researchers generally agree that the technology's ultimate impact on learning outcomes will depend heavily on how thoughtfully it is integrated into existing pedagogical practices rather than on the inherent capabilities of the technology itself. Several school districts have begun developing formal guidelines governing appropriate classroom use of these tools, seeking to balance genuine innovation with legitimate concerns about academic integrity and skill development.",
    'As organizations increasingly digitize their operations, cybersecurity threats have grown correspondingly more sophisticated, moving well beyond simple computer viruses to include ransomware attacks, coordinated phishing campaigns, and attacks that specifically exploit vulnerabilities in interconnected supply chains linking multiple companies and their various software vendors. High-profile breaches affecting hospitals, government agencies, and financial institutions have demonstrated that even well-resourced organizations remain vulnerable to determined attackers, particularly as remote work has substantially expanded the number of individual devices and networks that must be secured against potential intrusion. In response, many companies have shifted toward a so-called zero-trust security model, which assumes no device or user should be automatically trusted regardless of its physical or network location, requiring continuous verification of identity and permissions rather than a single login credential. Despite these technological advances, security experts consistently caution that human error, such as employees inadvertently falling for convincing phishing emails, remains one of the most common entry points for attackers, suggesting that technology alone cannot fully solve the underlying security problem. Cybersecurity insurance has also become increasingly common as companies seek to manage the substantial financial risk associated with a successful breach.',
    'Many developed nations are grappling with the significant economic and social implications of rapidly aging populations, as declining birth rates combine with steadily longer life expectancies to shift the ratio of working-age adults available to support a growing number of retirees. This demographic transition places mounting strain on pension systems and healthcare infrastructure, both of which were largely designed decades ago under the assumption of a much younger overall population base with a far larger proportion of active workers. Some governments have responded by gradually raising the official retirement age or actively encouraging greater labor force participation among older adults through targeted incentives, while others have turned to immigration policy as a means of replenishing the working-age population and offsetting domestic demographic decline. Economists remain divided on which combination of measures will ultimately prove most effective, though there is broad consensus that continued inaction carries substantial long-term fiscal risk, particularly for countries where public pension obligations already represent a significant and growing share of overall government spending. Some countries have also begun exploring reforms to long-term care systems specifically designed to address the needs of a much larger elderly population in coming decades.',
    'Deep-sea mining, which involves extracting mineral deposits such as cobalt, nickel, and manganese from the ocean floor using specialized remotely operated equipment, has emerged as a contentious frontier in the global push to secure critical materials needed for batteries and other clean-energy technologies. Proponents argue that seabed mining could reduce dependence on land-based mining operations, which are often associated with significant environmental damage and, in some regions, genuinely poor labor conditions for workers involved in extraction. Opponents counter that the deep ocean remains one of the least understood ecosystems on the entire planet, and that large-scale extraction could cause irreversible harm to species and habitats before scientists have even had the opportunity to properly study them and understand their ecological role. Several nations and private companies have already begun exploratory operations under the regulatory oversight of the International Seabed Authority, even as environmental groups and some scientific bodies call for a moratorium on commercial extraction until more comprehensive research on the associated ecological risks has been completed. The debate has increasingly pitted resource security concerns against environmental precaution, with no clear international consensus yet emerging on how to proceed.',
    'Gene therapy, which involves correcting or replacing faulty genes to treat inherited diseases at their underlying genetic source, has progressed from purely experimental research to fully approved clinical treatments for a growing number of specific conditions, including certain forms of inherited blindness and severe inherited blood disorders. Early gene therapies were significantly hampered by challenges in safely delivering genetic material into the appropriate human cells, but substantial advances in viral vector technology have considerably improved both the safety and overall effectiveness of these treatments over the past decade of intensive research. Despite this meaningful progress, the extraordinarily high cost of many currently approved gene therapies, sometimes exceeding a million dollars for a single patient treatment, has raised difficult and pressing questions about equitable access, particularly within healthcare systems already struggling with limited financial resources and competing priorities. Researchers continue to explore innovative ways to reduce manufacturing costs, including more efficient production methods, while regulators in multiple countries work to establish flexible approval frameworks that can keep pace with this rapidly evolving and scientifically complex field. Insurance companies and national health systems are also developing new payment models designed to spread the substantial upfront cost of these treatments over time.',
    "Social media platforms rely heavily on sophisticated recommendation algorithms designed to maximize user engagement by continuously predicting which specific content is most likely to hold a given individual's attention for the longest possible time. While this general approach has proven highly effective at increasing overall time spent on these platforms, critics argue that it often inadvertently amplifies sensational or emotionally charged content, since such material tends to generate substantially stronger engagement metrics than more measured, nuanced, or factually careful posts. Researchers have linked these underlying algorithmic incentives to the accelerated spread of misinformation and increased political polarization, as users are frequently shown content that reinforces their existing beliefs rather than exposing them to a genuinely broader range of perspectives and viewpoints. In response to mounting public and regulatory pressure, some platforms have begun experimenting with algorithmic adjustments specifically intended to reduce the visibility of borderline or potentially harmful content, though independent researchers remain skeptical about how effective, or how permanent, these particular changes will ultimately prove to be given the platforms' underlying commercial incentives. Regulators in several jurisdictions are now considering legislation that would require greater transparency about how these recommendation algorithms actually function.",
    "Nuclear fusion, the fundamental process that powers the sun by combining light atomic nuclei together to release enormous amounts of usable energy, has long been considered one of the most promising potential solutions to the world's growing energy demands, offering the theoretical possibility of abundant power without the carbon emissions associated with fossil fuels or the long-lived radioactive waste generated by conventional nuclear fission reactors. For decades, achieving a fusion reaction that produces more usable energy than it consumes remained an elusive scientific goal, but recent breakthroughs at major research facilities have finally demonstrated net energy gain under carefully controlled laboratory conditions for the first time in history. Scaling this significant scientific achievement into a commercially viable power plant capable of reliably supplying electricity to the grid remains a formidable engineering challenge, and most experts caution that fusion power is unlikely to make a meaningful contribution to the global energy mix for at least another two or three decades, even under relatively optimistic development timelines. Nevertheless, substantial private investment continues to flow into fusion research startups, reflecting considerable optimism that recent scientific progress could eventually be translated into practical commercial applications sooner than many conservative estimates currently suggest.",
    'Urban heat islands, a well-documented phenomenon in which cities experience significantly higher temperatures than surrounding rural areas due to the heat-absorbing properties of concrete, asphalt, and other common built surfaces, are becoming an increasingly pressing public health concern as global average temperatures continue to rise year over year. The effect is often most pronounced in lower-income neighborhoods, which tend to have considerably less tree cover and green space than wealthier areas of the same city, compounding existing social inequalities in heat-related illness and even mortality during periods of extreme summer weather. City planners have begun experimenting with a range of mitigation strategies, including reflective or light-colored roofing materials designed to reduce heat absorption, expanded urban tree canopies providing natural shade, and green roofs planted with vegetation that both cools buildings and manages stormwater runoff. While these various interventions have shown measurable benefits in smaller pilot studies conducted in individual neighborhoods, implementing them at the citywide scale needed to meaningfully offset broader urban warming trends requires substantial and sustained public investment that many municipal governments currently struggle to secure given competing budget priorities. Some cities have begun mandating minimum green space requirements for new construction projects as a longer-term structural solution.',
    'Roughly a third of all food produced globally for human consumption is lost or wasted each year before it can ever be eaten, a figure that represents not only a significant economic loss for producers and consumers alike but also a substantial, often overlooked contributor to global greenhouse gas emissions, since decomposing food waste in landfills generates significant quantities of methane. In wealthier nations, food waste tends to occur disproportionately at the consumer and retail level, driven by strict cosmetic standards for fresh produce and widespread confusion over the meaning of date labeling on packaged goods, whereas in developing countries losses more often occur earlier in the supply chain due to inadequate storage facilities and unreliable transportation infrastructure. A range of solutions have been proposed to address these very different drivers of waste, from simplifying standardized date labels and harmonizing food donation liability laws to investing directly in cold-chain infrastructure in regions where post-harvest losses currently remain highest. Reducing food waste is increasingly recognized by policymakers and environmental organizations alike as one of the most cost-effective strategies currently available for cutting emissions while simultaneously improving overall food security for vulnerable populations.',
    "Growing recognition of the significant mental health toll associated with modern workplaces has prompted many organizations to reassess how they genuinely support employee wellbeing, moving beyond superficial wellness perks toward more substantive structural changes to workload and management practices. Chronic stress, excessive and unrealistic workloads, and a persistent lack of clear boundaries between work and personal life have all been consistently linked to rising rates of professional burnout, which multiple studies suggest can meaningfully reduce both individual productivity and long-term employee retention across organizations. Some companies have introduced concrete measures such as mandatory disconnection policies outside of designated working hours, expanded access to confidential mental health resources, and dedicated manager training focused specifically on recognizing early warning signs of burnout among individual team members. Nevertheless, critics argue that such initiatives often fail to genuinely address the root causes of workplace stress, particularly chronic understaffing and unrealistic performance expectations set by senior leadership, meaning that surface-level wellness programs may do relatively little to change actual outcomes without accompanying, more difficult shifts in organizational culture and realistic workload management. Regulators in several countries have begun exploring legal frameworks that would formally recognize a worker's right to disconnect from work communications outside contracted hours.",
    'The development of autonomous vehicles has advanced considerably over the past decade, with several technology companies now operating limited self-driving taxi services in select cities under close and continuous regulatory supervision by transportation authorities. Proponents argue that widespread adoption of autonomous vehicles could dramatically reduce traffic accidents, the overwhelming majority of which are currently caused by human error such as distraction, fatigue, or impairment, while also improving mobility options for elderly and disabled individuals who are currently unable to drive themselves independently. However, the underlying technology continues to struggle with unpredictable edge cases, such as unusual weather conditions or erratic and unexpected behavior from pedestrians and other human drivers, that fall outside the range of scenarios its systems were extensively trained on during development. Regulatory frameworks governing legal liability in the event of an accident involving a self-driving vehicle also remain notably underdeveloped in most jurisdictions worldwide, creating significant legal uncertainty that some industry analysts believe may ultimately slow the pace of commercial deployment even as the underlying technology itself continues to steadily improve. Insurance companies are also actively working to develop entirely new risk models specifically suited to a future involving substantial numbers of autonomous vehicles on public roads.',
    'Illegal wildlife trafficking has grown into one of the most lucrative forms of transnational organized crime currently in operation, generating billions of dollars in illicit revenue annually through the trade of endangered species and their various parts, including ivory, rhino horn, and exotic live animals sold as pets. Beyond directly driving many already-threatened species toward extinction, this extensive illegal trade poses significant public health risks as well, as the close and often unsanitary contact between humans and wild animals involved in trafficking networks has been directly linked to the emergence of several serious zoonotic diseases capable of jumping from animals to human populations. International efforts to combat wildlife trafficking have included stricter enforcement of existing international trade bans, increased funding for dedicated anti-poaching patrols in vulnerable habitats, and targeted demand-reduction campaigns aimed at consumer markets where trafficked wildlife products are most actively sought after and purchased. Conservationists caution, however, that as long as substantial financial profits remain readily available to organized traffickers and enforcement resources stay chronically limited relative to the sheer scale of the trade, these various efforts are likely to only partially curb the overall practice rather than eliminate it entirely.',
    "Blockchain technology, best known publicly as the foundational infrastructure underlying various cryptocurrencies, is increasingly being explored for a wide range of applications well beyond digital currency, including supply chain tracking, land ownership registries, and verification of academic credentials and professional certifications. Because blockchain records are distributed across an extensive network of independent computers and are extremely difficult to alter retroactively once recorded, proponents argue the technology can provide a level of transparency and tamper-resistance that traditional centralized databases often struggle to match, particularly valuable in contexts where trust between transacting parties is otherwise quite limited. Several governments and major corporations have launched pilot programs specifically testing blockchain-based systems for tracking the provenance of goods such as food products and pharmaceuticals, aiming to reduce fraud and substantially improve accountability across increasingly complex international supply chains involving numerous intermediaries. Critics note, however, that many of these particular applications could likely be achieved with simpler, considerably less resource-intensive database technologies, and that blockchain's genuine comparative advantages are most pronounced specifically in situations requiring decentralized trust among parties who cannot otherwise reasonably rely on one another or a shared central authority.",
    'Labor economists have long debated the precise relationship between immigration and domestic labor markets, with the ongoing discussion often centering specifically on whether immigrant workers meaningfully depress overall wages or directly displace native-born workers from otherwise available jobs. A substantial body of accumulated research suggests that, in aggregate terms, immigration tends to have a modest positive or largely neutral effect on overall wages and employment levels, partly because immigrants often fill genuine labor shortages in specific sectors while simultaneously increasing overall demand for goods and services as active consumers themselves. However, these effects can vary considerably at the local and specific sector level, with some individual studies finding modest wage pressure specifically among workers possessing similar skill sets and limited English proficiency who are directly competing for the same entry-level positions. Policymakers attempting to design coherent immigration policy that maximizes overall economic benefit while genuinely addressing legitimate concerns about localized labor market disruption continue to face the persistent challenge of reconciling these nuanced, sometimes conflicting, research findings with a broader public debate that is often framed in far more simplistic and politically charged terms than the underlying evidence actually supports.',
    "Linguists estimate that nearly half of the world's roughly seven thousand living languages could disappear entirely by the end of this century, as globalization, rapid urbanization, and the growing dominance of a small number of major world languages in education, media, and international commerce accelerate an ongoing shift toward broader linguistic homogenization. The loss of any individual language represents far more than simply the disappearance of one communication system among many; each distinct language encodes a unique way of categorizing and understanding the world, along with irreplaceable cultural knowledge, oral histories, and, in some documented cases, specialized ecological or medicinal knowledge accumulated carefully over many generations of a community. Efforts to document and actively revitalize endangered languages have expanded considerably in recent years, ranging from community-led immersion programs designed for young children to sophisticated digital archiving projects that use audio recordings and interactive software specifically to preserve languages with only a small number of remaining fluent elderly speakers. Linguists caution, however, that genuine revitalization ultimately requires sustained intergenerational transmission of a language within its home community, meaning that documentation alone, while undeniably valuable for the historical record, is rarely sufficient by itself to keep a language truly alive and actively spoken.",
    "Additive manufacturing, more commonly known to the general public as three-dimensional printing, has moved well beyond its original origins as a simple prototyping tool to become a genuinely viable method for producing finished, end-use parts across diverse industries ranging from aerospace engineering to modern healthcare. The technology allows manufacturers to create highly complex internal geometries that would be extremely difficult or altogether impossible to achieve using traditional subtractive manufacturing methods, while also enabling on-demand, geographically localized production that can meaningfully reduce reliance on long, often vulnerable global supply chains subject to disruption. In medicine specifically, 3D printing has already enabled the creation of custom-fitted prosthetics and surgical implants tailored precisely to an individual patient's unique anatomy, and researchers are now actively exploring advanced bioprinting techniques theoretically capable of producing functional human tissue for eventual transplantation. Despite this considerable progress, the technology still faces significant practical limitations in terms of overall production speed and final material strength compared to conventional manufacturing methods, meaning it currently complements rather than fully replaces traditional production techniques for most large-scale industrial applications requiring high-volume output.",
    'Rising rates of obesity have become a major and growing public health concern in many countries around the world, driven by a genuinely complex combination of interacting factors including increased availability of cheap, calorie-dense processed foods, considerably more sedentary modern lifestyles, and, in certain specific populations, an underlying genetic predisposition toward weight gain. Public health officials have implemented a wide range of policy interventions aimed at reversing this troubling trend, from targeted taxes on sugary beverages to mandatory calorie labeling requirements on restaurant menus, with results that vary considerably depending on how comprehensively such policies are actually implemented and rigorously enforced within a given jurisdiction. Researchers increasingly emphasize that obesity cannot realistically be addressed through individual willpower alone, pointing instead to the powerful role of the broader food environment, including aggressive marketing of unhealthy products specifically targeted at children and the disproportionate concentration of fast food outlets in lower-income neighborhoods relative to healthier alternatives. Addressing these underlying structural factors directly, rather than focusing almost exclusively on individual behavior change, is now widely regarded by leading public health experts as genuinely essential to making meaningful, sustained progress on national obesity rates over the coming decades.',
    "Income inequality has widened considerably in many advanced economies over the past several decades, with wage growth for the highest earners substantially outpacing that of middle- and lower-income workers, even as overall economic productivity within these same economies has continued to rise steadily throughout the same period. Economists generally attribute this significant divergence to a combination of interacting factors, including the marked decline of labor unions in many industries, the widespread automation of routine manual and clerical jobs previously held by middle-income workers, and a tax and regulatory environment in many countries that has increasingly favored capital income over traditional labor income. Some policymakers have proposed concrete measures such as higher minimum wages, expanded earned income tax credits, and more genuinely progressive taxation systems specifically designed to help narrow this widening gap, while others argue that such interventions risk discouraging valuable investment and overall job creation within the broader economy. The debate remains highly contentious among economists and policymakers alike, in part because researchers continue to genuinely disagree about the precise magnitude of the trade-offs involved and how different countries' unique economic structures might respond differently to broadly similar policy interventions.",
    'The growing volume of debris currently orbiting Earth, ranging from defunct decommissioned satellites to countless small fragments generated by past collisions and deliberate anti-satellite weapons tests, has raised increasing concern among space agencies and private satellite operators alike about the long-term sustainability of continued activity in low Earth orbit. Even remarkably small pieces of debris travel at extremely high velocities capable of causing catastrophic damage to fully operational spacecraft, and scientists warn of a potential cascading effect, sometimes referred to as the Kessler syndrome, in which initial collisions generate substantial further debris that subsequently increases the likelihood of additional collisions occurring. As the total number of active satellites in orbit has grown quite dramatically with the emergence of large commercial satellite constellations providing global internet coverage, several organizations have begun developing dedicated technologies specifically to actively remove debris, including robotic capture arms, deployable nets, and harpoon-based capture systems, though none have yet been successfully deployed at truly meaningful operational scale. International coordination on binding orbital debris mitigation standards remains quite limited at present, and many experts argue that formal global agreements will ultimately prove necessary to prevent worsening orbital congestion from seriously threatening future space activities.',
    "Desertification, the gradual process by which previously fertile land transforms into arid desert, typically as a direct result of prolonged drought, extensive deforestation, and unsustainable agricultural practices acting together over time, threatens the basic livelihoods of hundreds of millions of people, particularly across sub-Saharan Africa, Central Asia, and parts of the wider Mediterranean region. As productive farmland gradually disappears in these affected areas, local communities often face substantially reduced food security and rising poverty, which in some specific regions has directly contributed to violent conflict over increasingly scarce access to remaining arable land and available water resources. Efforts to actively combat desertification have included large-scale reforestation initiatives, such as Africa's ambitious Great Green Wall project spanning the width of the continent, alongside more localized technical techniques like agricultural terracing and drought-resistant crop varieties specifically designed to help restore degraded soil health and improve moisture retention. While these various interventions have shown genuinely promising results in specific pilot regions studied closely by researchers, experts caution that reversing desertification at a truly meaningful scale requires sustained, multi-decade investment and close coordination across national borders, since the underlying drivers, particularly ongoing climate change, often extend well beyond the control of any single affected community or nation.",
    'The preservation of significant cultural heritage sites has become an increasingly urgent global priority as climate change, rapid urban development, and ongoing armed conflict pose growing and interconnected threats to historically and culturally important locations found throughout the world. Rising sea levels and increased coastal flooding directly threaten numerous low-lying archaeological sites and historic coastal cities, while rapid urbanization in many developing nations has, in certain documented cases, led to the outright demolition or gradual degradation of heritage sites in order to make way for new commercial or residential construction. International heritage organizations have responded to these mounting threats by expanding funding for digital documentation projects, using advanced laser scanning and photogrammetry techniques to create extremely detailed three-dimensional records of at-risk sites before they are potentially lost or irreparably damaged. While digital preservation ensures that some meaningful record of these sites will ultimately survive even physical destruction, heritage experts consistently emphasize that it cannot fully substitute for the profound cultural, spiritual, and economic value that local communities derive directly from the ongoing physical presence of these sites, underscoring the continued critical importance of direct on-the-ground conservation efforts wherever they remain genuinely feasible.',
    'Concerns about noise pollution, an issue long overshadowed by other more visible forms of environmental pollution, have recently gained increasing attention from public health researchers who have directly linked chronic exposure to traffic, industrial, and aircraft noise to a range of adverse health outcomes, including measurably elevated stress hormones, disrupted sleep patterns, and an increased documented risk of cardiovascular disease over time. Unlike more visible forms of pollution such as smog or litter, noise is often normalized by the public as simply an unavoidable feature of modern urban life, meaning it receives comparatively little dedicated regulatory attention despite genuinely affecting a substantial share of city residents worldwide on a daily basis. Some progressive cities have begun implementing targeted noise mitigation measures, including notably stricter zoning restrictions near major roadways, physical sound barriers erected along busy highways, and quieter pavement materials specifically engineered to reduce tire noise at the source. Though such interventions remain far less common in practice than comparable measures targeting air quality, researchers increasingly argue that as urban populations continue to grow worldwide, effectively addressing noise pollution will require treating it with the same regulatory seriousness historically reserved for other, more visible environmental hazards.',
    'The rise of digital nomadism, in which remote workers relocate quite frequently, often across international borders, while continuing to work for employers based elsewhere entirely, has been directly enabled by the broader normalization of remote work alongside the widespread proliferation of coworking spaces and increasingly reliable internet access in a growing number of attractive destinations worldwide. Several countries have introduced dedicated digital nomad visas specifically designed to actively attract these mobile professionals, recognizing the potential economic benefits of increased local spending on housing, dining, and various services without directly displacing local workers from the domestic job market in the process. Critics of this growing trend, however, point to legitimate concerns about digital nomads inadvertently driving up local housing costs in popular destination cities, sometimes effectively pricing out long-term local residents, echoing similar tensions previously observed in cities significantly affected by unregulated short-term rental platforms. As national governments continue refining policies specifically aimed at capturing the genuine economic benefits of this growing mobile workforce while simultaneously mitigating its potential negative downsides for host communities, digital nomadism appears likely to remain a significant and continuously evolving feature of the broader post-pandemic global labor landscape.',
    'Vaccine hesitancy, generally defined as a genuine reluctance or outright refusal to vaccinate despite the ready availability of vaccination services, has been identified by major public health organizations as a significant ongoing obstacle to controlling the spread of preventable infectious diseases, contributing directly to periodic disease outbreaks in regions with previously high historical immunization rates. Researchers have found that this hesitancy stems from a genuinely complex mix of interacting factors, including targeted misinformation spread rapidly through social media platforms, historical and often justified mistrust of medical institutions among certain specific communities, and genuine, good-faith uncertainty about vaccine safety among concerned parents actively seeking reliable information. Public health campaigns specifically aimed at addressing this hesitancy have increasingly moved away from simply presenting raw scientific data, instead focusing considerable effort on building genuine trust through already-trusted community messengers, such as local healthcare providers and respected religious leaders, who are often much better positioned to address specific individual concerns than distant government health agencies. Despite these evolving efforts, experts caution that rebuilding genuine trust in vaccination programs within communities where hesitancy has become deeply entrenched over time is likely to require sustained, long-term community engagement rather than short-term informational campaigns alone.',
    'Carbon capture and storage technology, which involves actively capturing carbon dioxide emissions from major industrial sources or, in some newer applications, directly from the ambient atmosphere and subsequently storing them underground or converting them into other stable materials, has attracted significant financial investment as governments and major corporations search for practical tools to meet increasingly ambitious national climate targets. Proponents argue that carbon capture is genuinely essential for decarbonizing certain industries such as cement and steel production, where emissions are inherently difficult to eliminate through electrification or renewable energy alone due to the fundamental chemical processes involved in manufacturing these materials. Critics, however, warn that an excessive overreliance on carbon capture technology could inadvertently delay more fundamental and necessary reductions in overall fossil fuel use, effectively allowing high-emitting industries to continue operating largely unchanged while betting heavily on unproven technology to fully offset their ongoing environmental impact. Current carbon capture projects remain notably expensive to build and operate, and collectively capture only a genuinely small fraction of total global emissions, leading many climate scientists to argue that the technology should be treated strictly as a complement to, rather than an outright substitute for, aggressive emissions reduction efforts across the broader global economy.',
    "Efforts to remove plastic waste already accumulated within the world's oceans have expanded significantly in recent years, with several dedicated organizations developing large-scale cleanup systems specifically designed to passively collect floating debris using natural ocean currents, most notably targeting the Great Pacific Garbage Patch, a vast accumulation zone located roughly between California and Hawaii. While these engineered systems have successfully removed substantial quantities of existing plastic debris from affected waters, marine biologists caution that cleanup efforts alone cannot realistically resolve the underlying environmental crisis, since an estimated eight million additional tons of new plastic waste continue to enter the ocean each year from various land-based sources worldwide. Some researchers also raise legitimate concerns that large mechanical collection systems could inadvertently capture marine organisms alongside targeted plastic debris, prompting engineers to continuously refine their designs specifically to minimize such unintended ecological bycatch. Most environmental experts broadly agree that genuinely meaningful progress against ocean plastic pollution will ultimately depend far more heavily on reducing overall plastic production at its source and substantially improving waste management infrastructure in the specific countries responsible for the largest share of ocean-bound plastic than on downstream cleanup technology deployed after the fact.",
    "Groundwater aquifers, which reliably supply drinking water and agricultural irrigation to a substantial share of the world's total population, are currently being depleted at an alarming rate in many major agricultural regions, as extraction for irrigation purposes consistently outpaces the natural rate at which these underground reservoirs are gradually replenished through rainfall infiltration over time. Unlike surface water shortages, which are often quite visible and prompt relatively immediate public attention and concern, aquifer depletion frequently goes largely unnoticed for many years, since actual groundwater levels can only be accurately measured through specialized monitoring wells rather than through straightforward direct visual observation available to the general public. In some of the world's most agriculturally productive regions, including parts of northern India and the American Great Plains, decades of unsustainable groundwater extraction have already led to dramatic and well-documented declines in local water tables, seriously threatening the long-term viability of farming practices that entire regional economies have come to depend upon over generations. Policymakers face genuinely significant political challenges in effectively addressing this issue, since meaningfully restricting groundwater use often meets strong organized resistance from farmers whose immediate livelihoods depend directly on continued unrestricted access, even as scientists repeatedly warn that current extraction rates simply cannot be sustained indefinitely into the future.",
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


SESSION_COOKIE_NAME = "write90_session"


def get_cookie_manager():
    """Returns the single cookie-manager instance for THIS browser session,
    cached in st.session_state (which is strictly per-session in Streamlit)
    rather than in a module-level global. A module-level global is shared
    across every concurrent user's script thread in the same server process,
    so two sessions running at once could read/write each other's cookie
    manager — silently returning None or a stale token and forcing a
    re-login on refresh even though the cookie was set correctly. Caching
    per st.session_state guarantees each browser session gets its own
    instance and never races with anyone else's."""
    if "_cookie_manager" not in st.session_state:
        st.session_state["_cookie_manager"] = stx.CookieManager(key="write90_cookie_manager")
    return st.session_state["_cookie_manager"]


def set_session_cookie(token: str):
    """Persists login across a page refresh using a browser cookie scoped to
    this device only — never the URL."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    get_cookie_manager().set(
        SESSION_COOKIE_NAME, token, expires_at=expires_at, key=f"set_{token[:8]}"
    )


def clear_session_cookie():
    try:
        get_cookie_manager().delete(SESSION_COOKIE_NAME, key="delete_session_cookie")
    except KeyError:
        pass  # cookie was already absent — nothing to clear


def get_session_cookie():
    """Reads the saved session token from the browser, or None if absent.
    May return None on the very first script run before the cookie
    component has finished mounting — the app treats that the same as
    'not logged in yet', and a normal Streamlit rerun (e.g. any widget
    interaction) picks it up moments later."""
    return get_cookie_manager().get(SESSION_COOKIE_NAME)


def save_pro_lead(conn, username: str, email: str, phone: str):
    """Records interest in Pro so it can be followed up on manually. Returns
    (ok, error)."""
    try:
        conn.table("pro_leads").insert({
            "username": username,
            "email": email,
            "phone": phone,
        }).execute()
        return True, None
    except Exception as e:
        return False, str(e)


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
    """A plain, static line chart — no scroll-zoom, no drag-pan (touch or
    mouse), fixed 0-90 axis. Altair charts have no pan/zoom by default;
    .interactive() is what turns it ON, so it's simply never called here."""
    df = pd.DataFrame({"Attempt": list(range(1, len(scores) + 1)), "Score": scores})
    chart = (
        alt.Chart(df)
        .mark_line(point={"size": 70, "filled": True}, color="#2563EB", strokeWidth=2.5)
        .encode(
            x=alt.X("Attempt:O", title="Attempt"),
            y=alt.Y("Score:Q", title="Score", scale=alt.Scale(domain=[0, 90])),
            tooltip=["Attempt", "Score"],
        )
        .properties(height=220)
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
# Study Tips — curated, high-leverage advice per task, aimed at the specific
# scoring traits Pearson grades on. Static reference content, not generated.
# ---------------------------------------------------------------------------
STUDY_TIPS = {
    "essay": [
        "Nail Form first — it's the easiest 2 points on the whole test. Land between 220–290 words so a slightly long or short count never tips you out of the 200–300 range.",
        "Use a simple, reliable structure: intro (paraphrase the prompt + state your position), two body paragraphs (one idea each, with an example), a short conclusion restating your stance. Examiners reward this predictability under Development & Coherence.",
        "If the prompt has two parts (\"discuss both views and give your opinion\"), address both explicitly and give equal space to each — a lopsided essay loses Content points even if the writing is strong.",
        "Vary your connectives. Rotate through however, moreover, consequently, nevertheless, in contrast, as a result, rather than repeating and/but/also — this alone moves the needle on General Linguistic Range.",
        "Mix sentence types deliberately: include at least one complex sentence (with a subordinate clause) and one conditional per paragraph, alongside simpler ones — pure simple sentences cap your Linguistic Range score.",
        "Save your last 2 minutes purely for proofreading subject-verb agreement, articles (a/an/the), and spelling — these small slips are the single most common way a strong essay loses points.",
        "Pick US or UK spelling and stick to it for the entire response — mixing color/colour or organize/organise triggers a Spelling deduction even if every individual word is spelled correctly.",
        "Use topic-relevant academic vocabulary, but only words you're confident using correctly — one badly-used \"impressive\" word does more damage than a well-used simple one.",
    ],
    "swt": [
        "It must be ONE sentence — no full stop until the very end. Use semicolons, colons, or subordinate clauses (while, although, which) to link ideas instead of starting a new sentence.",
        "Stay inside 5–75 words, but aim for 30–40 — long enough to capture the main idea and a key supporting point, short enough to stay tightly synthesized.",
        "Identify the passage's single main idea first, then ask what one supporting detail is essential to it. Trying to include everything usually produces a disconnected, low-coherence sentence.",
        "Paraphrase rather than lifting phrases directly from the passage — reusing the source's exact wording caps your Content score even if the sentence is accurate.",
        "Skip the throat-clearing. Don't open with \"This passage talks about\" or \"The passage is about\" — go straight into the content in your own words; every word here should be doing work.",
        "Read your sentence back once before submitting and check it's grammatically one sentence — if you can put a full stop anywhere in the middle and it still makes sense, restructure it.",
    ],
    "sst": [
        "Take notes while listening — you won't see the transcript at any point, so jot keywords, numbers, and cause/effect signal words (however, as a result, in contrast) as you hear them.",
        "Target 50–70 words in a single paragraph, no bullet points or line breaks — Form drops a full point outside 40–100 words.",
        "Capture the lecture's overall argument plus 2–3 supporting points, not every detail — an overstuffed summary usually loses coherence and clarity faster than it gains content.",
        "Write your summary as connected sentences, not a list of notes strung together — examiners are explicitly checking that ideas are synthesized, not just captured.",
        "If you missed a specific number or name, don't guess wildly — describe it generally (\"a significant increase\") rather than inventing a wrong detail, which reads as a comprehension error.",
        "Reread your response once before time is up to confirm it reads as one coherent paragraph summarizing the whole talk, not just the opening or closing lines.",
    ],
    "dictation": [
        "Listen for the sentence's core structure first (subject–verb–object), then reconstruct modifiers and connecting words afterward from memory.",
        "You typically hear it only once — resist the urge to write while still listening. Listen fully, then write immediately after from memory.",
        "Small function words (a, the, of, in, that) are the most commonly dropped words — proofread specifically for these once you've typed the sentence.",
        "Word order matters as much as word choice — read your typed sentence back and check it flows the way natural English would, not just that the words are all present.",
        "Practice with unfamiliar collocations (\"structural integrity\", \"regulatory oversight\") since real dictation sentences often include one less-common phrase alongside simple ones.",
        "If you're unsure of a word's spelling, write your best phonetic guess rather than skipping it — a wrong-but-present word can still register as partially correct; a gap never does.",
    ],
}

STUDY_TIPS_GENERAL = [
    "Across every task, the fastest points to lose are Form and Spelling — both are entirely within your control regardless of how strong your ideas are. Nail those first before polishing content.",
    "Read the rubric criteria for each task type in the sidebar's Verification Guide before you attempt it — knowing exactly what's being scored changes how you write in real time.",
    "Consistency beats brilliance. A 90 comes from reliably avoiding small errors across every response, not from occasional excellent responses mixed with weak ones.",
    "Review your History tab regularly — the recurring weaknesses PTE examiners flag for you are far more useful to fix than chasing a single high score.",
]


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


def render_live_word_counter(counter_key: str, textarea_label: str, lo: int, hi: int, initial_text: str = ""):
    """Renders a metric-stack box that updates on every keystroke, instead of
    only after a Streamlit rerun (which for st.text_area normally only fires
    once the field loses focus). This works by reaching into the parent page,
    finding the actual <textarea> Streamlit rendered for this widget (matched
    by its accessible label), and listening to its native 'input' event —
    completely independent of Streamlit's own rerun cycle."""
    initial_words = word_count(initial_text)
    initial_chars = len(initial_text)
    safe_label = json.dumps(textarea_label)
    box_id = f"w90-livecount-{counter_key}"
    st.markdown(
        f'<div id="{box_id}" class="w90-metric-stack">'
        f'METRIC STACK: {initial_words} WORDS | CHARACTER BLOCKS: {initial_chars}</div>',
        unsafe_allow_html=True,
    )
    components.html(
        f"""
        <script>
        (function() {{
            const label_{counter_key} = {safe_label};
            const lo_{counter_key} = {lo};
            const hi_{counter_key} = {hi};
            const boxId_{counter_key} = {json.dumps(box_id)};

            function render(textarea) {{
                const doc = window.parent.document;
                const box = doc.getElementById(boxId_{counter_key});
                if (!box) return;
                const val = textarea.value || "";
                const trimmed = val.trim();
                const words = trimmed.length ? trimmed.split(/\\s+/).length : 0;
                const chars = val.length;
                const inRange = words > 0 && words >= lo_{counter_key} && words <= hi_{counter_key};
                box.textContent = 'METRIC STACK: ' + words + ' WORDS | CHARACTER BLOCKS: ' + chars;
                box.style.color = words === 0 ? '#475569' : (inRange ? '#15803D' : '#B45309');
                box.style.borderColor = words === 0 ? '#E2E8F0' : (inRange ? '#15803D' : '#B45309');
            }}

            function attach() {{
                const doc = window.parent.document;
                const textarea = doc.querySelector('textarea[aria-label="' + label_{counter_key} + '"]');
                if (!textarea) {{ setTimeout(attach, 150); return; }}
                if (textarea.__write90WcHandler) {{
                    textarea.removeEventListener('input', textarea.__write90WcHandler);
                }}
                const handler = function() {{ render(textarea); }};
                textarea.__write90WcHandler = handler;
                textarea.addEventListener('input', handler);
                render(textarea);
            }}
            attach();
        }})();
        </script>
        """,
        height=0,
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
        <div id="voiceLabel_{key}" style="font-size:11px;color:#94A3B8;margin-top:6px;"></div>
        <script>
        (function() {{
            // Use the PARENT window's speech engine everywhere (voice list,
            // speaking, and cancelling) rather than this iframe's own copy.
            // Some browsers give an iframe a separate/emptier voice list than
            // the top-level page, which silently forces a worse fallback
            // voice even though better ones are actually installed.
            const synth = window.parent.speechSynthesis;
            const text_{key} = {safe_text};
            document.getElementById('playBtn_{key}').textContent = {safe_label};

            // Split into sentences so each one is spoken as its own utterance.
            // Long single utterances tend to sound flatter and more monotone;
            // short chained utterances let the engine reset intonation at
            // each sentence boundary, which reads as noticeably more natural.
            const sentences_{key} = text_{key}.match(/[^.!?]+[.!?]*/g) || [text_{key}];

            // Names known to sound distinctly robotic/dated — actively
            // avoided even if nothing better is found, since these are the
            // most common cause of "still sounds robotic" complaints.
            const AVOID_NAMES = /david desktop|zira desktop|mark desktop|espeak|compact|fred|whisper|junior|bells|bad news|boing|cellos|deranged|hysterical|pipe organ|trinoids|zarvox|bahh/i;

            function pickVoice() {{
                const voices = (synth.getVoices() || []).filter(v => !AVOID_NAMES.test(v.name));
                if (!voices.length) return null;
                const preferredNames = [
                    "Microsoft Aria Online (Natural) - English (United States)",
                    "Microsoft Ava Online (Natural) - English (United States)",
                    "Microsoft Emma Online (Natural) - English (United States)",
                    "Microsoft Guy Online (Natural) - English (United States)",
                    "Google US English", "Google UK English Female", "Google UK English Male",
                    "Samantha", "Karen", "Daniel", "Moira", "Tessa"
                ];
                for (const name of preferredNames) {{
                    const v = voices.find(v => v.name === name);
                    if (v) return v;
                }}
                // Voices flagged localService:false are almost always cloud/
                // network voices (Google, Microsoft Natural, etc.) which sound
                // dramatically less robotic than the offline OS default.
                let v = voices.find(v => v.localService === false && /^en/i.test(v.lang));
                if (v) return v;
                v = voices.find(v => /Natural|Neural/i.test(v.name) && /^en/i.test(v.lang));
                if (v) return v;
                v = voices.find(v => /Google/i.test(v.name) && /^en/i.test(v.lang));
                if (v) return v;
                v = voices.find(v => /^en-US|^en_US/i.test(v.lang));
                if (v) return v;
                v = voices.find(v => /^en/i.test(v.lang));
                return v || voices[0];
            }}

            let playToken_{key} = 0;

            function speakQueue(voice, myToken) {{
                let i = 0;
                function next() {{
                    if (myToken !== playToken_{key} || i >= sentences_{key}.length) return;
                    const u = new SpeechSynthesisUtterance(sentences_{key}[i].trim());
                    if (voice) {{ u.voice = voice; u.lang = voice.lang; }}
                    u.rate = 0.94;
                    u.pitch = 1.0;
                    u.volume = 1;
                    u.onend = function() {{ i += 1; next(); }};
                    synth.speak(u);
                }}
                next();
            }}

            function speak() {{
                synth.cancel();
                playToken_{key} += 1;
                const voice = pickVoice();
                const label = document.getElementById('voiceLabel_{key}');
                if (label) {{ label.textContent = voice ? ('Voice: ' + voice.name) : 'Voice: browser default'; }}
                speakQueue(voice, playToken_{key});
            }}

            document.getElementById('playBtn_{key}').onclick = function() {{
                if (synth.getVoices().length === 0) {{
                    synth.onvoiceschanged = speak;
                    // Fallback in case the event never fires on this browser.
                    setTimeout(speak, 250);
                }} else {{
                    speak();
                }}
            }};
            document.getElementById('stopBtn_{key}').onclick = function() {{
                playToken_{key} += 1;
                synth.cancel();
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
                        playToken_{key} += 1;
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


def render_word_level_diff(original: str, corrected: str) -> str:
    """Builds one flowing sentence with only the differing words marked —
    wrong/removed words struck through in red, replacement/added words in
    green — instead of showing the whole original sentence and the whole
    corrected sentence as two separate blocks. Whitespace is preserved as
    its own tokens so spacing reads naturally."""
    orig_tokens = re.findall(r"\s+|\S+", original)
    corr_tokens = re.findall(r"\s+|\S+", corrected)
    matcher = difflib.SequenceMatcher(None, orig_tokens, corr_tokens, autojunk=False)
    parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            parts.append(esc("".join(orig_tokens[i1:i2])))
        else:
            if i1 != i2:
                parts.append(f'<span class="orig-bad">{esc("".join(orig_tokens[i1:i2]))}</span>')
            if j1 != j2:
                parts.append(f'<span class="fixed">{esc("".join(corr_tokens[j1:j2]))}</span>')
    return "".join(parts)


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
            diff_html = render_word_level_diff(item.get("original", ""), item.get("corrected", ""))
            body = (
                f'{diff_html}'
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
        left, right = st.columns([2.3, 1])

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
            if scores:
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


@st.dialog("Write Your Own Essay")
def custom_essay_dialog():
    cfg = TASK_CONFIGS["essay"]
    lo, hi = cfg["word_range"]

    custom_question = st.text_area(
        "Your essay question",
        height=100,
        placeholder="Paste or write any essay prompt here...",
        key="custom_essay_question",
    )
    custom_response = st.text_area(
        "Your essay (custom prompt)",
        height=420,
        placeholder="Write or paste your 200–300 word essay here...",
        key="custom_essay_response",
    )
    render_live_word_counter(
        counter_key="custom_essay",
        textarea_label="Your essay (custom prompt)",
        lo=lo, hi=hi,
        initial_text=custom_response,
    )
    st.caption(cfg["word_hint"])

    submit = st.button(
        "Mark My Response Against Rubric",
        type="primary",
        disabled=not (custom_question.strip() and custom_response.strip()),
    )
    if submit:
        if not api_key:
            st.error("Enter your Anthropic API key in the sidebar first.")
        elif get_usage_count(conn, st.session_state["user"]) >= DAILY_LIMIT:
            st.error(f"Daily limit of {DAILY_LIMIT} responses reached. Please try again tomorrow.")
        else:
            with st.spinner("Marking carefully against the official rubric… this can take a little while."):
                try:
                    wc = word_count(custom_response)
                    result = call_claude(api_key, "essay", custom_question, custom_response, wc)
                    bump_usage_count(conn, st.session_state["user"])
                    save_submission(conn, st.session_state["user"], "essay", custom_question, custom_response, result)
                    render_result(result, "essay")
                except GradingError as e:
                    st.error("The examiner's response didn't come back in a readable format. Please try again.")
                    with st.expander("Technical details"):
                        st.code(e.raw_text[-2000:] if e.raw_text else str(e))
                except Exception as e:
                    st.error(f"Something went wrong marking your response: {e}")


@st.dialog("Write Your Own Summarize Written Text")
def custom_swt_dialog():
    cfg = TASK_CONFIGS["swt"]
    lo, hi = cfg["word_range"]

    custom_passage = st.text_area(
        "Your passage to summarize",
        height=220,
        placeholder="Paste any reading passage here (up to ~300 words)...",
        key="custom_swt_passage",
    )
    custom_response = st.text_area(
        "Your one-sentence summary",
        height=140,
        placeholder="Write ONE sentence, 5–75 words, capturing the passage's main idea...",
        key="custom_swt_response",
    )
    render_live_word_counter(
        counter_key="custom_swt",
        textarea_label="Your one-sentence summary",
        lo=lo, hi=hi,
        initial_text=custom_response,
    )
    st.caption(cfg["word_hint"])

    submit = st.button(
        "Mark My Response Against Rubric",
        type="primary",
        key="submit_custom_swt",
        disabled=not (custom_passage.strip() and custom_response.strip()),
    )
    if submit:
        if not api_key:
            st.error("Enter your Anthropic API key in the sidebar first.")
        elif get_usage_count(conn, st.session_state["user"]) >= DAILY_LIMIT:
            st.error(f"Daily limit of {DAILY_LIMIT} responses reached. Please try again tomorrow.")
        else:
            with st.spinner("Marking carefully against the official rubric… this can take a little while."):
                try:
                    wc = word_count(custom_response)
                    result = call_claude(api_key, "swt", custom_passage, custom_response, wc)
                    bump_usage_count(conn, st.session_state["user"])
                    save_submission(conn, st.session_state["user"], "swt", custom_passage, custom_response, result)
                    render_result(result, "swt")
                except GradingError as e:
                    st.error("The examiner's response didn't come back in a readable format. Please try again.")
                    with st.expander("Technical details"):
                        st.code(e.raw_text[-2000:] if e.raw_text else str(e))
                except Exception as e:
                    st.error(f"Something went wrong marking your response: {e}")


# ---------------------------------------------------------------------------
# Chat tutor — a free-form, open-ended chat where candidates can ask
# personal study questions (grammar rules, vocabulary, exam strategy,
# "is this sentence correct", general encouragement, etc.) outside the
# structured rubric-graded tasks above. Uses the Anthropic API directly with
# a lightweight system prompt rather than the rubric system prompts.
# ---------------------------------------------------------------------------
CHAT_SYSTEM_PROMPT = """You are the Write90 PTE Tutor, a warm, encouraging, and knowledgeable assistant embedded inside a PTE Academic (Pearson Test of English) practice app. Candidates come to this chat to ask personal, informal study questions that don't fit the structured Essay/SWT/SST/Dictation grading tools elsewhere in the app — things like grammar rules, vocabulary/synonym questions, whether a sentence sounds natural, exam strategy, time management, how scoring works, or general encouragement and study planning.

Guidelines:
- Be concise and practical. Most answers should be a short paragraph or a few bullet points, not an essay.
- When asked to check a sentence, give a corrected version plus a one-line explanation of what changed and why.
- When asked about scoring or exam format, answer accurately based on Pearson's official PTE Academic structure and be clear that exact question pools are confidential and rotate.
- You are not a therapist or medical professional; if a person raises serious personal distress unrelated to test prep, gently encourage them to speak with someone qualified rather than trying to counsel them yourself, while remaining warm.
- Keep the tone supportive but not saccharine — like a sharp, friendly tutor, not a cheerleader."""


def call_chat(api_key: str, messages: list) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1200,
        system=CHAT_SYSTEM_PROMPT,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")


def render_chat_bubble(role: str, content: str):
    """Renders one chat message as a themed bubble matching the rest of the
    app (w90-* classes), instead of st.chat_message's default widget, which
    ships with its own fixed avatars/colors that ignore this app's theme
    entirely and look visually disconnected from every other screen."""
    label = "You" if role == "user" else "Tutor"
    st.markdown(
        f'<div class="w90-chat-row {role}">'
        f'<div class="w90-chat-bubble {role}">'
        f'<span class="w90-chat-label">{label}</span>{esc(content)}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_chatbot_section(conn):
    st.subheader("Ask the Tutor")
    st.caption("Ask anything personal to your prep — grammar checks, vocabulary, strategy, \"does this sentence sound natural\", or just where to focus next. This chat isn't scored and doesn't count toward your task history.")

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    if not st.session_state["chat_messages"]:
        st.markdown(
            '<div class="w90-chat-empty">Try asking things like: "Is this sentence grammatically correct: ...", '
            '"What\'s the difference between \'affect\' and \'effect\'?", "How is the Essay task scored?", '
            'or "I keep running out of time on SST, what should I change?"</div>',
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state["chat_messages"]:
            render_chat_bubble(msg["role"], msg["content"])

    prompt = st.chat_input("Ask a question…")
    if prompt:
        if not api_key:
            st.error("Enter your Anthropic API key in the sidebar first.")
            return
        if get_usage_count(conn, st.session_state["user"]) >= DAILY_LIMIT:
            st.error(f"Daily limit of {DAILY_LIMIT} responses reached. Please try again tomorrow.")
            return

        st.session_state["chat_messages"].append({"role": "user", "content": prompt})

        with st.spinner("Thinking…"):
            try:
                api_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["chat_messages"]
                ]
                reply = call_chat(api_key, api_messages)
                bump_usage_count(conn, st.session_state["user"])
            except Exception as e:
                reply = f"Something went wrong reaching the tutor: {e}"

        st.session_state["chat_messages"].append({"role": "assistant", "content": reply})
        st.rerun()

    if st.session_state["chat_messages"]:
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state["chat_messages"] = []
            st.rerun()


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

# Restore login on refresh from a browser cookie (device-local, never part
# of a shareable URL). get_session_cookie() may briefly return None on the
# very first run before the cookie component finishes mounting — that's
# fine, since the component's own internal rerun re-checks moments later.
if not st.session_state["user"]:
    saved_token = get_session_cookie()
    if saved_token:
        restored_user = get_session_user(conn, saved_token)
        if restored_user:
            st.session_state["user"] = restored_user
            st.session_state["session_token"] = saved_token

if not st.session_state["user"]:
    render_top_banner()
    st.caption("New here? Create a free account to save your work and track your score history over time.")
    tab_signup, tab_login = st.tabs(["Sign up", "Log in"])

    with tab_login:
        lu = st.text_input("Username", key="login_user")
        lp = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log in"):
            ok = verify_user(conn, lu.strip(), lp)
            if ok:
                token = create_session(conn, lu.strip())
                st.session_state["user"] = lu.strip()
                st.session_state["session_token"] = token
                set_session_cookie(token)
                st.rerun()
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
                    set_session_cookie(token)
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
        clear_session_cookie()
        st.rerun()

    api_key = secret_key if secret_key else st.text_input("Anthropic API key", type="password")

    usage_today = get_usage_count(conn, st.session_state["user"])
    st.markdown("---")
    st.caption(f"DAILY LIMIT: {usage_today} / {DAILY_LIMIT}")
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
    nav_options = list(TASK_CONFIGS.keys()) + ["chatbot", "study_tips", "progress", "get_pro"]
    nav_labels = {
        **{k: v["label"] for k, v in TASK_CONFIGS.items()},
        "chatbot": "Ask the Tutor",
        "study_tips": "Study Tips",
        "progress": "My Progress",
        "get_pro": "Get Pro",
    }
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
        left, right = st.columns([2.3, 1])

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

            if task_key == "essay":
                if st.button("Write Your Own Essay", key="open_custom_essay", use_container_width=True):
                    custom_essay_dialog()

            if task_key == "swt":
                if st.button("Write Your Own Summary", key="open_custom_swt", use_container_width=True):
                    custom_swt_dialog()

            if task_key == "sst":
                # Real PTE exam behavior: you LISTEN to the lecture, you never
                # see it written out. Show only the audio control, not the
                # transcript — the text is still used behind the scenes for
                # grading (context_text), just never rendered on screen.
                st.markdown(f'**{cfg["context_label"]}**')
                st.caption("Listen carefully — the transcript is not shown, just like the real exam.")
                tts_button(context_text, key=f"{task_key}_{current_idx}")
            else:
                st.markdown(f'**{cfg["context_label"]}**')
                st.markdown(
                    f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;'
                    f'padding:14px 16px;font-size:14px;color:#0F172A;margin-bottom:10px;'
                    f'max-height:{cfg["context_height"]}px;overflow-y:auto;">{esc(context_text)}</div>',
                    unsafe_allow_html=True,
                )

            response_text = st.text_area(cfg["response_label"], height=420,
                                          placeholder=cfg["response_placeholder"],
                                          key=f"resp_{task_key}_{current_idx}")
            wc = word_count(response_text)
            char_count = len(response_text)
            lo, hi = cfg["word_range"]
            render_live_word_counter(
                counter_key=f"{task_key}_{current_idx}",
                textarea_label=cfg["response_label"],
                lo=lo, hi=hi,
                initial_text=response_text,
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
            if scores:
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

elif current_section == "chatbot":
    render_chatbot_section(conn)

elif current_section == "study_tips":
    st.subheader("Study Tips — how to reach 90")
    st.caption("Curated, rubric-specific advice for each task type. Not personalized — your recurring weaknesses are on the My Progress page.")

    st.markdown("---")
    st.markdown("**Across every task**")
    for tip in STUDY_TIPS_GENERAL:
        st.markdown(f'<div class="pte-tip">{esc(tip)}</div>', unsafe_allow_html=True)

    for task_key, cfg in TASK_CONFIGS.items():
        tips = STUDY_TIPS.get(task_key, [])
        if not tips:
            continue
        st.markdown("---")
        st.subheader(cfg["label"])
        for tip in tips:
            st.markdown(f'<div class="pte-tip">{esc(tip)}</div>', unsafe_allow_html=True)

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
            fixed_score_chart(task_scores)

            if cfg.get("criteria"):
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
            else:
                st.caption("Scored locally by word accuracy — see the History tab under Write From Dictation for a detailed breakdown of each attempt.")

elif current_section == "get_pro":
    st.subheader("Write90 Pro")
    st.markdown(
        """
        <div class="w90-pro-card">
            <div class="w90-pro-price">$12<span>/month</span></div>
            <div style="margin-top:18px;">
                <div class="w90-pro-feature">✓ Unlimited PTE-based AI evaluations</div>
                <div class="w90-pro-feature">✓ Full access to Essay, SWT, SST & Dictation banks</div>
                <div class="w90-pro-feature">✓ Detailed score history & progress tracking</div>
                <div class="w90-pro-feature">✓ Priority support</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "show_pro_form" not in st.session_state:
        st.session_state["show_pro_form"] = False

    col_center = st.columns([1, 1, 1])[1]
    with col_center:
        if not st.session_state["show_pro_form"]:
            if st.button("Get Pro", type="primary", use_container_width=True, key="get_pro_open_btn"):
                st.session_state["show_pro_form"] = True
                st.rerun()

    if st.session_state["show_pro_form"]:
        st.markdown("---")
        st.markdown("**Leave your contact details and we'll reach out to get you set up.**")
        pro_email = st.text_input("Email address", key="pro_lead_email")
        pro_phone = st.text_input("Phone number", key="pro_lead_phone")
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            if st.button("Submit", type="primary", use_container_width=True, key="pro_lead_submit"):
                if not pro_email.strip() or not pro_phone.strip():
                    st.error("Enter both your email and phone number.")
                else:
                    ok, err = save_pro_lead(conn, st.session_state["user"], pro_email.strip(), pro_phone.strip())
                    if ok:
                        st.session_state["show_pro_form"] = False
                        st.success("Thanks! We'll be in touch shortly to get you set up with Pro.")
                    else:
                        st.error("Could not save your details — a database error occurred.")
                        with st.expander("Technical details"):
                            st.code(err)
        with col_cancel:
            if st.button("Cancel", use_container_width=True, key="pro_lead_cancel"):
                st.session_state["show_pro_form"] = False
                st.rerun()

# ---------------------------------------------------------------------------
# Get Pro banner — shown at the bottom of every page except the Get Pro
# page itself, so the upsell is always one click away.
# ---------------------------------------------------------------------------
if current_section != "get_pro":
    st.markdown(
        """
        <div class="w90-pro-banner">
            <div>
                <p class="w90-pro-title">Upgrade to Write90 Pro — $12/month</p>
                <p class="w90-pro-sub">Unlimited evaluations, full question banks, and priority support.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Get Pro", key="bottom_banner_get_pro"):
        st.session_state["current_section"] = "get_pro"
        st.rerun()
