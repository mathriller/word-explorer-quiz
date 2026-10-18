import base64
import html
import json
import os
import random
import re
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI
from streamlit.components.v1 import declare_component

st.set_page_config(page_title="단어 탐험대", page_icon="🔎", layout="centered")

handwriting_canvas = declare_component(
    "handwriting_canvas",
    path=str(Path(__file__).parent / "handwriting_canvas"),
)

DEFAULT_WORDS = [
    {"word": "usual", "meaning": "흔히 하는"},
    {"word": "porridge", "meaning": "죽"},
    {"word": "sardine", "meaning": "정어리"},
    {"word": "plateful", "meaning": "한 접시 (가득한 양)"},
    {"word": "cheesy", "meaning": "치즈 맛이 나는"},
    {"word": "grocer", "meaning": "식료품 잡화점"},
    {"word": "noticed", "meaning": "신경 쓰다; ~을 의식하다"},
    {"word": "nearly", "meaning": "거의"},
    {"word": "looked at", "meaning": "~을 살피다"},
    {"word": "meant", "meaning": "의미했다 (mean의 과거형)"},
    {"word": "backwards", "meaning": "뒤로"},
    {"word": "crate", "meaning": "나무로 된 운송용 상자"},
    {"word": "reflection", "meaning": "반사"},
    {"word": "admiring", "meaning": "감탄하는"},
    {"word": "each other", "meaning": "서로"},
    {"word": "roll off", "meaning": "굴러 떨어지다"},
    {"word": "pavement", "meaning": "인도; 포장도로"},
    {"word": "squashed", "meaning": "짓눌렀다"},
    {"word": "sticky", "meaning": "끈적끈적한"},
    {"word": "instead", "meaning": "~을 대신해"},
]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@500;700;800;900&family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Nunito','Noto Sans KR',sans-serif; }
.stApp { background: linear-gradient(150deg,#f3fbff 0%,#fffaf0 68%,#f8f4ff 100%); }
.block-container { max-width: 850px; padding-top: 2rem; }
.hero { background: #fff; border: 2px solid #e7f1ff; border-radius: 28px; padding: 1.5rem 1.6rem; box-shadow: 0 12px 36px #33558812; }
.hero h1 { font-weight: 900; font-size: 2.2rem; color: #243b64; margin: 0; }
.hero p { color: #61728d; margin: .35rem 0 0; }
.question { background: #fff; border: 2px solid #dceaff; border-radius: 28px; padding: 2rem 1.5rem; text-align: center; box-shadow: 0 14px 36px #33558814; }
.question .eyebrow { color: #7a91b6; font-weight: 800; letter-spacing: .05em; }
.question .prompt { color: #263b60; font-size: 2.5rem; font-weight: 900; margin: .7rem 0; line-height: 1.25; }
.answer-card { background:#fff; border:2px solid #dceaff; border-radius:18px; padding:14px; min-height:170px; }
.answer-title { color:#71819a; font-weight:800; margin-bottom:8px; }
div.stButton > button { border-radius: 14px; font-weight: 800; min-height: 2.8rem; }
</style>
""", unsafe_allow_html=True)


def get_api_key():
    try:
        return st.secrets.get("OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    except Exception:
        return os.getenv("OPENAI_API_KEY", "")


def get_client():
    key = get_api_key()
    return OpenAI(api_key=key) if key else None


def clean_word_rows(rows):
    cleaned = []
    for row in rows:
        word = str(row.get("word", "")).strip()
        meaning = str(row.get("meaning", "")).strip()
        if word and meaning:
            cleaned.append({"word": word, "meaning": meaning})
    return cleaned


def extract_vocab(image_bytes, mime_type):
    client = get_client()
    if not client:
        raise RuntimeError("사진에서 단어를 읽으려면 OpenAI API 키가 필요해요. 표에 직접 입력할 수도 있어요.")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    prompt = (
        "Read the printed vocabulary table in this worksheet photo. Return only a JSON array of objects "
        'with exactly these keys: "word" and "meaning". Keep English words and Korean printed meanings. '
        "Ignore handwriting, names, dates, page instructions, and row numbers. Do not guess unreadable text. "
        "Include a row only when both fields can be read."
    )
    result = client.responses.create(
        model="gpt-4.1-mini",
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:{mime_type};base64,{encoded}"},
        ]}],
    )
    fence = chr(96) * 3
    raw = result.output_text.strip().replace(fence + "json", "").replace(fence, "").strip()
    return clean_word_rows(json.loads(raw))


def transcribe(audio_bytes, mode):
    client = get_client()
    if not client:
        raise RuntimeError("음성 인식에는 OpenAI API 키가 필요해요.")
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "answer.wav"
    language = "en" if mode == "뜻 → 단어" else "ko"
    result = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe", file=audio_file, language=language
    )
    return result.text.strip()


def make_quiz(mode, size, count):
    return {
        "mode": mode,
        "size": size,
        "deck": random.sample(st.session_state.vocab, k=count),
        "index": 0,
        "score": 0,
        "checked": False,
        "last_answer": "",
        "last_drawing": "",
    }


def next_question(quiz, got_it_right=False):
    if got_it_right:
        quiz["score"] += 1
    quiz["index"] += 1
    quiz["checked"] = False
    quiz["last_answer"] = ""
    quiz["last_drawing"] = ""


if "vocab" not in st.session_state:
    st.session_state.vocab = DEFAULT_WORDS.copy()
if "quiz" not in st.session_state:
    st.session_state.quiz = None

with st.sidebar:
    st.markdown("## 🧺 단어 바구니")
    st.caption("사진을 올려 단어를 가져오거나, 표에서 직접 고쳐 보세요.")
    uploaded = st.file_uploader("단어표 사진", type=["png", "jpg", "jpeg", "webp"], help="사진 속 단어표의 인쇄된 영어 단어와 뜻을 읽어요.")
    if uploaded and st.button("✨ 사진에서 단어 읽기", use_container_width=True):
        try:
            with st.spinner("사진 속 표를 읽고 있어요…"):
                extracted = extract_vocab(uploaded.getvalue(), uploaded.type or "image/jpeg")
            if extracted:
                st.session_state.vocab = extracted
                st.session_state.pop("vocab_editor", None)
                st.session_state.quiz = None
                st.success(f"{len(extracted)}개 단어를 가져왔어요. 표를 확인해 주세요!")
            else:
                st.warning("읽을 수 있는 단어가 없어요. 사진을 다시 찍거나 표에 직접 입력해 주세요.")
        except Exception as exc:
            st.error(str(exc))
    st.markdown("#### 단어와 뜻 확인하기")
    edited = st.data_editor(
        pd.DataFrame(st.session_state.vocab), num_rows="dynamic", use_container_width=True,
        hide_index=True, column_config={"word": "Word", "meaning": "Meaning"}, key="vocab_editor",
    )
    st.session_state.vocab = clean_word_rows(edited.to_dict(orient="records"))
    st.caption(f"현재 {len(st.session_state.vocab)}개 단어")

st.markdown('<div class="hero"><h1>🔎 단어 탐험대</h1><p>사진 속 단어를 꺼내서, 재미있게 퀴즈로 연습해요!</p></div>', unsafe_allow_html=True)
st.write("")
if not st.session_state.vocab:
    st.info("왼쪽 단어 바구니에 단어와 뜻을 추가해 주세요.")
    st.stop()

mode = st.radio("어떤 퀴즈를 할까요?", ["뜻 → 단어", "단어 → 뜻"], horizontal=True)
voice_enabled = bool(get_api_key())
if not voice_enabled:
    st.caption("🎙️ 음성 입력과 사진 읽기는 API 키를 등록하면 사용할 수 있어요.")

if (st.session_state.quiz is None or st.session_state.quiz["mode"] != mode
        or st.session_state.quiz["size"] != len(st.session_state.vocab)):
    st.markdown("### 준비됐나요?")
    st.write(f"오늘의 단어 **{len(st.session_state.vocab)}개**를 순서를 섞어 연습해요.")
    count = st.slider("몇 개 풀까요?", min_value=1, max_value=len(st.session_state.vocab), value=min(10, len(st.session_state.vocab)))
    if st.button("🚀 퀴즈 시작!", type="primary", use_container_width=True):
        st.session_state.quiz = make_quiz(mode, len(st.session_state.vocab), count)
        st.rerun()
    st.stop()

quiz = st.session_state.quiz
if quiz["index"] >= len(quiz["deck"]):
    st.markdown("## 🎉 퀴즈 끝!")
    st.metric("내가 맞혔다고 표시한 개수", f"{quiz['score']} / {len(quiz['deck'])}")
    st.caption("정답은 자동으로 채점하지 않았어요. 문제마다 스스로 판단한 결과예요.")
    if st.button("🔀 다시 섞어서 도전", type="primary", use_container_width=True):
        st.session_state.quiz = make_quiz(mode, len(st.session_state.vocab), len(quiz["deck"]))
        st.rerun()
    st.stop()

item = quiz["deck"][quiz["index"]]
prompt = item["meaning"] if mode == "뜻 → 단어" else item["word"]
expected = item["word"] if mode == "뜻 → 단어" else item["meaning"]
st.progress(quiz["index"] / len(quiz["deck"]), text=f"문제 {quiz['index'] + 1} / {len(quiz['deck'])}")
st.markdown(
    f'<div class="question"><div class="eyebrow">{"뜻을 보고 영어 단어를 써 보세요" if mode == "뜻 → 단어" else "영어 단어의 뜻을 써 보세요"}</div><div class="prompt">{html.escape(prompt)}</div></div>',
    unsafe_allow_html=True,
)
st.write("")

if not quiz["checked"]:
    st.markdown("#### ✏️ 손글씨로 답하기")
    drawing = handwriting_canvas(key=f"handwriting-{quiz['index']}", default="", reset=False)
    typed_answer = st.text_input("키보드 또는 Scribble로 답하기", placeholder="원하면 여기에 입력하세요")
    audio = st.audio_input("🎙️ 음성으로 답하기", key=f"audio-{quiz['index']}") if voice_enabled else None
    submitted = st.button("답과 정답 비교하기", type="primary", use_container_width=True)
    if submitted:
        if not typed_answer.strip() and not drawing and not audio:
            st.warning("손글씨, 키보드, 음성 중 한 가지 방법으로 답해 주세요.")
        else:
            spoken = ""
            if audio and not typed_answer.strip() and not drawing:
                try:
                    with st.spinner("음성을 글자로 바꾸고 있어요…"):
                        spoken = transcribe(audio.getvalue(), mode)
                except Exception as exc:
                    st.error(f"음성을 읽지 못했어요: {exc}")
                    st.stop()
            quiz["last_answer"] = typed_answer.strip() or spoken
            quiz["last_drawing"] = drawing if isinstance(drawing, str) and drawing.startswith("data:image/png;base64,") else ""
            quiz["checked"] = True
            st.rerun()
else:
    st.info("직접 살펴보고 판단해 보세요. 앱이 정답을 자동 채점하지 않아요.")
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="answer-card"><div class="answer-title">내 답</div>', unsafe_allow_html=True)
        if quiz["last_drawing"]:
            image_data = base64.b64decode(quiz["last_drawing"].split(",", 1)[1])
            st.image(image_data, use_container_width=True)
        if quiz["last_answer"]:
            st.markdown(f"**{html.escape(quiz['last_answer'])}**")
        if not quiz["last_drawing"] and not quiz["last_answer"]:
            st.caption("필기 입력이 없어요.")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="answer-card"><div class="answer-title">정답</div>', unsafe_allow_html=True)
        st.markdown(f"### {html.escape(expected)}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.write("")
    st.caption("스스로 맞았다고 판단하면 아래 버튼을 누르세요.")
    correct_col, next_col = st.columns(2)
    with correct_col:
        if st.button("✅ 내가 맞혔어요", type="primary", use_container_width=True, key=f"self-correct-{quiz['index']}"):
            next_question(quiz, got_it_right=True)
            st.rerun()
    with next_col:
        if st.button("다음 문제", use_container_width=True, key=f"skip-{quiz['index']}"):
            next_question(quiz)
            st.rerun()

st.write("")
st.caption("문제 순서는 무작위예요. 손글씨는 이 화면에서 비교하기 위해 저장되고, 다음 문제로 넘어가면 지워져요.")
