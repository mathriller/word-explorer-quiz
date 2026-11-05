# 단어 탐험대

초등학생이 단어표 사진으로 어휘 퀴즈를 만드는 웹앱입니다.

## 기능

- 사진에서 인쇄된 영어 단어와 한국어 뜻을 읽어와 표로 편집 (Gemini Flash OCR)
- `뜻 → 단어`, `단어 → 뜻` 두 가지 퀴즈 모드
- 문제 순서를 무작위로 섞고 출제 단어 개수 조절
- **✏️ Apple Pencil / 손가락 손글씨 답안 작성 (필압 지원)**
- **⌨️ 키보드 또는 🎙️ 음성으로 답하기**
- 내가 쓴 손글씨와 정답을 나란히 비교하여 스스로 채점
- 사진 예시의 20개 단어를 기본 연습 목록으로 제공

---

## 🚀 GitHub Pages로 초고속 실행하기 (추천!)

별도의 서버 설치나 파이썬 실행 없이, GitHub 저장소 설정만 켜면 `https://<내아이디>.github.io/<저장소이름>/` 주소로 즉시 접속할 수 있습니다. (서버 딜레이 0초, 아이패드 최적화)

1. 저장소 상단의 **Settings** 메뉴로 이동합니다.
2. 왼쪽 사이드바에서 **Pages**를 클릭합니다.
3. **Build and deployment** 항목에서:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main`, 폴더는 `/ (root)` 선택 후 **Save** 클릭
4. 1~2분 뒤 화면 상단에 표시되는 주소(`https://...github.io/...`)로 접속합니다.
5. 우측 상단 **⚙️ Gemini API 키 설정**을 누르고 발급받은 무료 API 키를 등록하면 사진 단어 인식을 즉시 사용할 수 있습니다. (브라우저 로컬 저장소에 안전하게 보관됩니다)

---

## 🐍 Streamlit 로컬 및 Community Cloud 실행

Python 3.10 이상에서:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GEMINI_API_KEY="구글_GEMINI_API_키"
$env:OPENAI_API_KEY="오픈AI_API_키" # 음성 기능용 (선택)
streamlit run app.py
```

### Streamlit Community Cloud 배포 시
앱 설정의 **Secrets**에 다음을 등록합니다:
```toml
GEMINI_API_KEY = "발급받은_구글_API_키"
OPENAI_API_KEY = "발급받은_오픈AI_API_키" # 선택 사항
```
