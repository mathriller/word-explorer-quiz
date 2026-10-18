import base64
import html
import json
import os
import random
import re
from io import BytesIO

import pandas as pd
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="단어 탐험대", page_icon="🔎", layout="centered")

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
div.stButton > button { border-radius: 14px; font-weight: 800; min-height: 2.8rem; }
div[data-testid="stMetric"] { background: white; border-radius: 18px; padding: 12px 16px; border: 1px solid #e8eff9; }
.small-note { color:#71819a; font-size:.9rem; }
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


def norm(text):
    text = text.strip().casefold()
    return re.sub(r"[\s\u3000.,!?;:'\"()\[\]{}·ㆍ~…–—-]+", "", text)


def matches(answer, accepted):
    answer_n = norm(answer)
    candidates = [part.strip() for part in re.split(r"[;|\n]", accepted) if part.strip()]
    return bool(answer_n) and any(answer_n == norm(candidate) for candidate in candidates)


def extract_vocab(image_bytes, mime_type):
    client = get_client()
    if not client:
        raise RuntimeError("사진에서 단어를 읽으려면 OpenAI API 키가 필요해요. 아래 표에 직접 입력할 수도 있어요.")
    encoded = base64.b64encode(image_bytes).decode("ascii")
    prompt = (
        "Read the printed vocabulary table in this worksheet photo. Return only a JSON array of objects "
        'with exactly these keys: "word" and "meaning". Keep English words and Korean printed meanings. '
        "Ignore handwriting, names, dates, page instructions, and row numbers. Do not guess unreadable text. "
        "If a row is partly unclear, include it only when both fields can be read."
    )
    result = client.responses.create(
        model="gpt-4.1-mini",
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:{mime_type};base64,{encoded}"},
        ]}],
    )
    raw = result.output_text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    parsed = json.loads(raw)
    return clean_word_rows(parsed)


def transcribe(audio_bytes, mode):
    client = get_client()
    if not client:
        raise RuntimeError("음성 인식에는 OpenAI API 키가 필요해요. 키보드로 답할 수 있어요.")
    language = "en" if mode == "뜻 → 단어" else "ko"
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "answer.wav"
    result = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe", file=audio_file, language=language
    )
    return result.text.strip()


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
            if not extracted:
                st.warning("읽을 수 있는 단어가 없어요. 밝고 반듯한 사진으로 다시 시도하거나 직접 입력해 주세요.")
            else:
                st.session_state.vocab = extracted
                st.session_state.pop("vocab_editor", None)
                st.session_state.quiz = None
                st.success(f"{len(extracted)}개 단어를 가져왔어요. 표를 확인해 주세요!")
        except Exception as exc:
            st.error(str(exc))
    st.markdown("#### 단어와 뜻 확인하기")
    edited = st.data_editor(
        pd.DataFrame(st.session_state.vocab),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={"word": "Word", "meaning": "Meaning"},
        key="vocab_editor",
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
    st.caption("🎙️ 음성 답변과 사진 읽기는 API 키를 등록하면 사용할 수 있어요. 키보드 퀴즈는 바로 할 수 있어요.")

if st.session_state.quiz is None or st.session_state.quiz["mode"] != mode or st.session_state.quiz["size"] != len(st.session_state.vocab):
    st.markdown("### 준비됐나요?")
    st.write(f"오늘의 단어 **{len(st.session_state.vocab)}개**를 순서를 섞어 연습해요.")
    count = st.slider("몇 개 풀까요?", min_value=1, max_value=len(st.session_state.vocab), value=min(10, len(st.session_state.vocab)))
    if st.button("🚀 퀴즈 시작!", type="primary", use_container_width=True):
        deck = random.sample(st.session_state.vocab, k=count)
        st.session_state.quiz = {"mode": mode, "size": len(st.session_state.vocab), "deck": deck, "index": 0, "score": 0, "checked": False, "last_correct": False, "last_answer": ""}
        st.rerun()
    st.stop()

quiz = st.session_state.quiz
if quiz["index"] >= len(quiz["deck"]):
    st.balloons()
    st.markdown("## 🎉 퀴즈 끝!")
    st.metric("맞힌 개수", f"{quiz['score']} / {len(quiz['deck'])}")
    if quiz["score"] == len(quiz["deck"]):
        st.success("완벽해요! 단어 탐험 대장!")
    elif quiz["score"] * 2 >= len(quiz["deck"]):
        st.success("잘했어요! 조금만 더 연습하면 다 맞힐 수 있어요.")
    else:
        st.info("괜찮아요. 한 번 더 풀면서 익혀 봐요!")
    if st.button("🔀 다시 섞어서 도전", type="primary", use_container_width=True):
        deck = random.sample(st.session_state.vocab, k=len(quiz["deck"]))
        st.session_state.quiz = {"mode": mode, "size": len(st.session_state.vocab), "deck": deck, "index": 0, "score": 0, "checked": False, "last_correct": False, "last_answer": ""}
        st.rerun()
    st.stop()

item = quiz["deck"][quiz["index"]]
prompt = item["meaning"] if mode == "뜻 → 단어" else item["word"]
expected = item["word"] if mode == "뜻 → 단어" else item["meaning"]
st.progress(quiz["index"] / len(quiz["deck"]), text=f"문제 {quiz['index'] + 1} / {len(quiz['deck'])}  ·  맞힌 개수 {quiz['score']}")
st.markdown(f'<div class="question"><div class="eyebrow">{ "뜻을 보고 영어 단어를 말해 봐요" if mode == "뜻 → 단어" else "영어 단어의 뜻을 말해 봐요" }</div><div class="prompt">{html.escape(prompt)}</div></div>', unsafe_allow_html=True)
st.write("")

if not quiz["checked"]:
    with st.form(f"answer-form-{quiz['index']}"):
        answer = st.text_input("내 답", placeholder="여기에 답을 써 보세요", label_visibility="collapsed")
        st.caption("📱 iPad에서는 답 칸을 누르고 Apple Pencil로 써 보세요. Scribble이 손글씨를 글자로 바꿔 줘요.")
        submitted = st.form_submit_button("정답 확인", type="primary", use_container_width=True)
    audio = None
    if voice_enabled:
        st.caption("또는 마이크를 눌러 말한 다음, 아래 버튼으로 확인해요.")
        audio = st.audio_input("🎙️ 음성으로 답하기", key=f"audio-{quiz['index']}")
        if audio and st.button("음성을 글자로 바꿔 정답 확인", key=f"transcribe-{quiz['index']}", use_container_width=True):
            try:
                with st.spinner("답을 듣고 있어요…"):
                    spoken = transcribe(audio.getvalue(), mode)
                st.session_state.quiz["last_answer"] = spoken
                st.session_state.quiz["last_correct"] = matches(spoken, expected)
                if st.session_state.quiz["last_correct"]:
                    st.session_state.quiz["score"] += 1
                st.session_state.quiz["checked"] = True
                st.rerun()
            except Exception as exc:
                st.error(f"음성을 읽지 못했어요: {exc}")
    if submitted:
        if not answer.strip():
            st.warning("답을 먼저 써 주세요.")
        else:
            quiz["last_answer"] = answer.strip()
            quiz["last_correct"] = matches(answer, expected)
            if quiz["last_correct"]:
                quiz["score"] += 1
            quiz["checked"] = True
            st.rerun()
else:
    if quiz["last_correct"]:
        st.success(f"정답이에요! 🎉  **{quiz['last_answer']}**")
    else:
        st.error(f"아쉽지만 괜찮아요! 정답은 **{expected}**예요.")
    if mode == "뜻 → 단어":
        st.caption(f"뜻: {item['meaning']}")
    else:
        st.caption(f"단어: {item['word']}")
    if st.button("다음 문제 ➜", type="primary", use_container_width=True):
        quiz["index"] += 1
        quiz["checked"] = False
        quiz["last_answer"] = ""
        quiz["last_correct"] = False
        st.rerun()

st.write("")
st.caption("정답은 대소문자와 띄어쓰기를 구분하지 않아요. 사진의 인쇄 글씨를 자동으로 읽은 뒤, 표에서 꼭 확인해 주세요.")



