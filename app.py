"""
AI Video Assistant - Streamlit UI
Place this file in the project root (next to main.py) and run:
    streamlit run app.py
"""
import os
import tempfile
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from main import run_pipeline          # noqa: E402
from core.rag_engine import ask_question  # noqa: E402

st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Styling (kept small: one headline treatment, quiet everything else)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .block-container { padding-top: 2.2rem; max-width: 1100px; }

    .app-title {
        font-family: 'Fraunces', serif;
        font-size: 2.6rem;
        line-height: 1.15;
        letter-spacing: -0.02em;
        margin: 0 0 .35rem 0;
    }
    .app-sub { color: #5F6B7A; font-size: 1.02rem; margin-bottom: 1.6rem; max-width: 60ch; }

    .video-title {
        font-family: 'Fraunces', serif;
        font-size: 1.9rem;
        line-height: 1.25;
        margin: 0 0 .3rem 0;
    }
    .meta { color: #5F6B7A; font-size: .9rem; margin-bottom: 1.2rem; }

    .step {
        border-left: 3px solid #3B5BDB;
        padding: .15rem 0 .15rem .9rem;
        margin-bottom: 1rem;
    }
    .step b { display: block; margin-bottom: .1rem; }
    .step span { color: #5F6B7A; font-size: .92rem; }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E3E7ED;
        border-radius: 10px;
        padding: .7rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# State
# ----------------------------------------------------------------------------
DEFAULTS = {"result": None, "chat": [], "meta": {}}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

SUGGESTIONS = [
    "What is the main point of this video?",
    "What are the key takeaways?",
    "Who is speaking and what is their view?",
]


def save_upload(uploaded) -> str:
    """Write an uploaded file to a temp path and return it."""
    suffix = os.path.splitext(uploaded.name)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        return tmp.name


def build_report(result: dict) -> str:
    return (
        f"# {result['title']}\n\n"
        f"## Summary\n{result['summary']}\n\n"
        f"## Action items\n{result['action_items']}\n\n"
        f"## Key decisions\n{result['key_decisions']}\n\n"
        f"## Open questions\n{result['open_questions']}\n\n"
        f"## Transcript\n{result['transcript']}\n"
    )


def answer(question: str) -> None:
    st.session_state.chat.append({"role": "user", "content": question})
    try:
        reply = ask_question(st.session_state.result["rag_chain"], question)
    except Exception as exc:  # noqa: BLE001
        reply = f"Something went wrong while answering: {exc}"
    st.session_state.chat.append({"role": "assistant", "content": reply})


# ----------------------------------------------------------------------------
# Sidebar: input
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Add a video")
    mode = st.radio("Source", ["YouTube link", "Upload a file"], horizontal=True,
                    label_visibility="collapsed")

    source, uploaded = None, None
    if mode == "YouTube link":
        source = st.text_input("YouTube link",
                               placeholder="https://www.youtube.com/watch?v=...").strip()
    else:
        uploaded = st.file_uploader(
            "Audio or video file",
            type=["mp3", "wav", "m4a", "aac", "ogg", "mp4", "mkv", "webm", "mov"],
        )

    language = st.selectbox("Spoken language", ["english", "hinglish"])

    ready = bool(source) or uploaded is not None
    run = st.button("Analyze video", type="primary", use_container_width=True,
                    disabled=not ready)

    if st.session_state.result is not None:
        st.divider()
        st.download_button(
            "Download full report",
            data=build_report(st.session_state.result),
            file_name="video_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        if st.button("Start over", use_container_width=True):
            st.session_state.result = None
            st.session_state.chat = []
            st.session_state.meta = {}
            st.rerun()

    st.caption("Long videos can take a few minutes to download and transcribe.")

# ----------------------------------------------------------------------------
# Run the pipeline
# ----------------------------------------------------------------------------
if run:
    target = source if mode == "YouTube link" else save_upload(uploaded)
    label = source if mode == "YouTube link" else uploaded.name
    st.session_state.chat = []

    with st.status("Analyzing your video...", expanded=True) as status:
        st.write("Fetching audio, transcribing, and generating the summary. "
                 "This runs in one pass, so keep this tab open.")
        try:
            st.session_state.result = run_pipeline(target, language)
            st.session_state.meta = {
                "source": label,
                "language": language,
                "time": datetime.now().strftime("%d %b %Y, %H:%M"),
            }
            status.update(label="Analysis complete", state="complete", expanded=False)
        except Exception as exc:  # noqa: BLE001
            status.update(label="Analysis failed", state="error")
            st.error(f"Could not process this video: {exc}")
            st.info("If the error mentions ffmpeg, make sure it is installed and "
                    "on your PATH, then restart VS Code.")

# ----------------------------------------------------------------------------
# Main area
# ----------------------------------------------------------------------------
result = st.session_state.result

if result is None:
    st.markdown('<h1 class="app-title">Turn any video into notes you can question</h1>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="app-sub">Paste a YouTube link or upload a recording. You get a summary, '
        'action items, decisions, and a chat that answers from the transcript.</p>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="step"><b>Add a video</b><span>A YouTube link, or an audio or '
                'video file from your computer.</span></div>', unsafe_allow_html=True)
    c2.markdown('<div class="step"><b>Read the breakdown</b><span>Summary, action items, '
                'key decisions, and open questions.</span></div>', unsafe_allow_html=True)
    c3.markdown('<div class="step"><b>Ask questions</b><span>Answers come from what was '
                'actually said in the video.</span></div>', unsafe_allow_html=True)
    st.stop()

# Header + stats
meta = st.session_state.meta
st.markdown(f'<h2 class="video-title">{result["title"]}</h2>', unsafe_allow_html=True)
st.markdown(f'<div class="meta">{meta.get("source", "")}  |  {meta.get("language", "").title()}'
            f'  |  analyzed {meta.get("time", "")}</div>', unsafe_allow_html=True)

words = len(result["transcript"].split())
m1, m2, m3 = st.columns(3)
m1.metric("Words transcribed", f"{words:,}")
m2.metric("Reading time", f"{max(1, round(words / 220))} min")
m3.metric("Questions asked", sum(1 for m in st.session_state.chat if m["role"] == "user"))

tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
    ["Summary", "Action items", "Key decisions", "Open questions", "Transcript", "Chat"]
)

with tab_summary:
    st.markdown(result["summary"])

with tab_actions:
    st.markdown(result["action_items"])

with tab_decisions:
    st.markdown(result["key_decisions"])

with tab_questions:
    st.markdown(result["open_questions"])
    st.caption("These are generated by the model and may go beyond what the speaker said. "
               "Use the Chat tab to check what the video actually covers.")

with tab_transcript:
    st.download_button("Download transcript", result["transcript"],
                       file_name="transcript.txt", mime="text/plain")
    st.text_area("Transcript", result["transcript"], height=420,
                 label_visibility="collapsed")

with tab_chat:
    history = st.container()

    clicked = None
    if not st.session_state.chat:
        st.caption("Try one of these, or type your own question below.")
        cols = st.columns(len(SUGGESTIONS))
        for col, text in zip(cols, SUGGESTIONS):
            if col.button(text, use_container_width=True):
                clicked = text

    prompt = st.chat_input("Ask about this video")
    question = prompt or clicked
    if question:
        with st.spinner("Searching the transcript..."):
            answer(question)

    with history:
        if not st.session_state.chat:
            st.info("Ask anything about the video. Answers are based on its transcript.")
        for msg in st.session_state.chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if st.session_state.chat:
        if st.button("Clear chat"):
            st.session_state.chat = []
            st.rerun()