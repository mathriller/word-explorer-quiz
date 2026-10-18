# 단어 탐험대

초등학생이 단어표 사진으로 어휘 퀴즈를 만드는 Streamlit 웹앱입니다.

## 기능

- 사진에서 인쇄된 영어 단어와 한국어 뜻을 읽어와 표로 편집
- `뜻 → 단어`, `단어 → 뜻` 두 가지 퀴즈 모드
- 문제 순서를 무작위로 섞고 키보드로 답하기
- 마이크로 답을 녹음해 글자로 바꿔 채점
- 사진 예시의 20개 단어를 기본 연습 목록으로 제공

사진 읽기와 음성 인식은 OpenAI API 키가 필요합니다. 키가 없어도 기본 단어 편집과 키보드 퀴즈는 사용할 수 있습니다. 사진의 손글씨와 학생 이름 같은 정보는 읽기 대상에서 제외하도록 설정했으며, 자동으로 읽은 결과는 퀴즈를 시작하기 전에 표에서 확인할 수 있습니다.

## 로컬 실행

Python 3.10 이상에서:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY="발급받은_API_키"
streamlit run app.py
```

API 키 없이 실행할 때는 `OPENAI_API_KEY` 설정을 생략하면 됩니다.

## Streamlit Community Cloud 배포

1. GitHub에 새 저장소를 만들고 `app.py`, `requirements.txt`를 올립니다.
2. [Streamlit Community Cloud](https://share.streamlit.io/)에 GitHub로 로그인하고 **Create app**을 선택합니다.
3. 저장소, 브랜치, 진입 파일 `app.py`를 지정하고 **Deploy**를 누릅니다.
4. 사진 읽기와 음성 기능을 쓰려면 앱 설정의 **Secrets**에 다음을 입력합니다.

```toml
OPENAI_API_KEY = "발급받은_API_키"
```

API 키를 GitHub 저장소에 올리지 마세요. Community Cloud의 비밀 설정에만 넣어 주세요.

[Streamlit 배포 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) · [비밀 키 설정 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)

## 사용 메모

- OCR은 사진의 기울기, 조명, 해상도에 따라 잘못 읽을 수 있어 표를 검토한 뒤 퀴즈를 시작하세요.
- 음성 인식은 영어 단어 모드에서 영어, 뜻 모드에서 한국어를 기준으로 인식합니다.
- 정답 확인은 단순 표기 일치 방식입니다. 뜻에 여러 정답을 허용하려면 표의 뜻 칸에서 `;` 또는 `|`로 나눠 적을 수 있습니다.
