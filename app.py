import base64
from concurrent.futures import ThreadPoolExecutor
import html
import json
import os
import random
import re
import time
from io import BytesIO
from pathlib import Path

import pandas as pd
from PIL import Image, ImageOps
import streamlit as st
from openai import OpenAI
from google import genai
from google.genai import types
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
div[data-testid="stCheckbox"] { min-height: 48px; }
div[data-testid="stCheckbox"] label { min-height: 48px; padding-block: 8px; cursor: pointer; }

/* Keep the app readable when iPadOS requests dark controls. */:root { color-scheme: light; }html, body, [class*="css"] { color-scheme: light; }.stApp, [data-testid="stAppViewContainer"] { color: #24344d !important; }[data-testid="stMain"], [data-testid="stMainBlockContainer"] { color: #24344d !important; }label, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,[data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"],[data-testid="stRadio"] label, [data-testid="stRadio"] label p,[data-testid="stCheckbox"] label, [data-testid="stCheckbox"] label p,[data-testid="stSlider"] label, [data-testid="stFileUploader"] label {  color: #24344d !important;}input, textarea, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {  color: #24344d !important;  -webkit-text-fill-color: #24344d !important;  background-color: #fff !important;  caret-color: #24344d !important;}input::placeholder, textarea::placeholder {  color: #69778d !important; opacity: 1 !important;  -webkit-text-fill-color: #69778d !important;}[data-testid="stFileUploader"] section {  background: #fff !important; color: #24344d !important;  border-color: #cbd7e8 !important;}[data-testid="stAlert"], [data-testid="stAlert"] p { color: #24344d !important; }.question .eyebrow, .answer-title { color: #52647e !important; }</style>


""", unsafe_allow_html=True)
def get_api_key():
    try:
        return st.secrets.get("OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    except Exception:
        return os.getenv("OPENAI_API_KEY", "")


def get_gemini_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


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


def preprocess_image(image_bytes, max_dim=1600):
    """스마트폰 고해상도 사진을 리사이즈/압축하고 회전(EXIF)을 자동 보정합니다."""
    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # 긴 변 기준 1600px로 축소 (인식 품질을 유지하면서 토큰 및 전송량 90% 이상 절감)
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=82, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, "image/jpeg"


def extract_vocab(image_bytes, mime_type="image/jpeg", max_retries=3):
    key = get_gemini_api_key()
    if not key:
        raise RuntimeError("사진에서 단어를 읽으려면 Streamlit Secrets에 GEMINI_API_KEY를 등록해 주세요. 표에 직접 입력할 수도 있어요.")
    
    # 1. 이미지 최적화 (속도 개선 및 서버 과부하 방지)
    optimized_bytes, target_mime = preprocess_image(image_bytes)

    client = genai.Client(api_key=key)
    prompt = (
        "Read the printed vocabulary table in this worksheet photo. Return only a JSON array of objects "
        'with exactly these keys: "word" and "meaning". Keep English words and Korean printed meanings. '
        "Ignore handwriting, names, dates, page instructions, and row numbers. Do not guess unreadable text. "
        "Include a row only when both fields can be read."
    )
    
    # 무료 티어 혼잡 시 폴백할 모델 목록
    candidate_models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    last_err = None

    for attempt in range(max_retries):
        model_name = candidate_models[attempt % len(candidate_models)]
        try:
            result = client.models.generate_content(
                model=model_name,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=optimized_bytes, mime_type=target_mime),
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return clean_word_rows(json.loads(result.text))
        except Exception as exc:
            last_err = exc
            err_msg = str(exc).lower()
            is_overload_or_quota = any(
                w in err_msg for w in ["overloaded", "503", "429", "quota", "resource_exhausted", "rate limit", "busy"]
            )
            if is_overload_or_quota and attempt < max_retries - 1:
                # 구글 서버 과부하/속도제한 시 지수 백오프 대기 후 재시도
                sleep_sec = (attempt + 1) * 2.0 + random.uniform(0.5, 1.5)
                time.sleep(sleep_sec)
                continue
            elif attempt < max_retries - 1:
                time.sleep(1.0)
                continue
            else:
                raise last_err

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


def make_quiz(mode, selected_words, selected_indices, count):
    return {
        "mode": mode,
        "size": len(selected_words),
        "selected_indices": list(selected_indices),
        "deck": random.sample(selected_words, k=count),
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
    uploaded = st.file_uploader("단어표 사진", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, help="여러 장을 한 번에 선택할 수 있어요. 사진 속 인쇄된 영어 단어와 뜻을 읽어요.")
    st.caption("iPad에서 파일 선택 후 카메라 화면이 검게 보이면 앱 카메라를 사용해 보세요.")
    use_camera = st.checkbox("📷 앱에서 카메라로 촬영")
    camera_photo = st.camera_input("단어표 사진 촬영", key="camera-photo") if use_camera else None
    photos = list(uploaded or [])
    if camera_photo:
        photos.append(camera_photo)
    if photos and st.button("✨ 사진에서 단어 읽기", use_container_width=True):
        try:
            extracted = []
            seen_rows = set()
            with st.spinner(f"사진 {len(photos)}장을 최적화하여 읽고 있어요 (서버 지연 시 자동 재시도)..."):
                # 여러 장일 때 병렬 처리하여 대기 시간 단축
                max_workers = min(len(photos), 3)
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(extract_vocab, photo.getvalue(), photo.type or "image/jpeg")
                        for photo in photos
                    ]
                    for f in futures:
                        rows = f.result()
                        for row in rows:
                            signature = (row["word"].casefold(), row["meaning"].casefold())
                            if signature not in seen_rows:
                                seen_rows.add(signature)
                                extracted.append(row)
            if extracted:
                st.session_state.vocab = extracted
                st.session_state.pop("vocab_editor", None)
                st.session_state.pop("quiz-selected-indices", None)
                for key in [key for key in st.session_state if key.startswith("quiz-word-")]:
                    del st.session_state[key]
                st.session_state.quiz = None
                st.success(f"{len(photos)}장 사진에서 중복을 합쳐 {len(extracted)}개 단어를 가져왔어요. 표를 확인해 주세요!")
            else:
                st.warning("사진에서 읽을 수 있는 단어가 없어요. 사진을 다시 찍거나 표에 직접 입력해 주세요.")
        except Exception as exc:
            err_text = str(exc)
            if any(w in err_text.lower() for w in ["overloaded", "503", "resource_exhausted", "quota"]):
                st.error("⚠️ 구글 Gemini 무료 서버가 일시적으로 매우 혼잡합니다. 잠시 후 다시 시도해 주세요. (Google AI Studio에서 카드를 등록하면 이 현상이 완전히 사라집니다.)")
            else:
                st.error(f"오류가 발생했습니다: {exc}")
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
word_options = list(range(len(st.session_state.vocab)))
for i in word_options:
    checkbox_key = f"quiz-word-{i}"
    if checkbox_key not in st.session_state:
        st.session_state[checkbox_key] = True

with st.expander("퀴즈에 사용할 단어 선택", expanded=False):
    select_all_col, clear_all_col = st.columns(2)
    with select_all_col:
        if st.button("전체 선택", use_container_width=True, key="select-all-quiz-words"):
            for i in word_options:
                st.session_state[f"quiz-word-{i}"] = True
            st.rerun()
    with clear_all_col:
        if st.button("전체 해제", use_container_width=True, key="clear-all-quiz-words"):
            for i in word_options:
                st.session_state[f"quiz-word-{i}"] = False
            st.rerun()
    for i in word_options:
        vocab_item = st.session_state.vocab[i]
        st.checkbox(
            f"{i + 1}. {vocab_item['word']} — {vocab_item['meaning']}",
            key=f"quiz-word-{i}",
        )

selected_indices = [i for i in word_options if st.session_state.get(f"quiz-word-{i}", True)]
st.caption(f"현재 {len(selected_indices)}개 단어 선택됨")
selected_vocab = [st.session_state.vocab[i] for i in selected_indices]
if not selected_vocab:
    st.info("퀴즈를 시작하려면 단어를 하나 이상 선택해 주세요.")
    st.stop()
voice_enabled = bool(get_api_key())
st.caption("📷 사진 단어 읽기는 Streamlit Secrets의 GEMINI_API_KEY, 🎙️ 음성 입력은 OPENAI_API_KEY를 등록하면 사용할 수 있어요.")

if (st.session_state.quiz is None or st.session_state.quiz["mode"] != mode
        or st.session_state.quiz.get("selected_indices") != selected_indices):
    st.markdown("### 준비됐나요?")
    st.write(f"선택한 단어 **{len(selected_vocab)}개**를 순서를 섞어 연습해요.")
    count = st.slider("몇 개 풀까요?", min_value=1, max_value=len(selected_vocab), value=min(10, len(selected_vocab)))
    if st.button("🚀 퀴즈 시작!", type="primary", use_container_width=True):
        st.session_state.quiz = make_quiz(mode, selected_vocab, selected_indices, count)
        st.rerun()
    st.stop()

quiz = st.session_state.quiz
if quiz["index"] >= len(quiz["deck"]):
    st.markdown("## 🎉 퀴즈 끝!")
    st.metric("내가 맞혔다고 표시한 개수", f"{quiz['score']} / {len(quiz['deck'])}")
    st.caption("정답은 자동으로 채점하지 않았어요. 문제마다 스스로 판단한 결과예요.")
    if st.button("🔀 다시 섞어서 도전", type="primary", use_container_width=True):
        st.session_state.quiz = make_quiz(mode, selected_vocab, selected_indices, len(quiz["deck"]))
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
        if ";" in expected or "|" in expected:
            options = [s.strip() for s in re.split(r"[;|]", expected) if s.strip()]
            st.markdown(f"### {' / '.join(html.escape(o) for o in options)}")
        else:
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
