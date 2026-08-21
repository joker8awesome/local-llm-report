# [프로젝트 가이드] 로컬 LLM & 멀티미디어 크롤링 파이프라인

**문서 버전:** v2.2.0
**최종 업데이트:** 2026-08-21
**기본 작업 경로:** `D:\로컬LLM` (코드 내부 하드코딩 경로는 `D:\로컬llm` — Windows에서 대소문자 무시되어 동일)

> ✅ **v2.2.0 변경:** 로드맵 3~6번 완료 — 멀티소스 HTML 렌더러, Streamlit 대시보드(`app.py`), 로컬 뷰어 서버, 이미지 로컬 다운로더. 사용자용 매뉴얼은 별도 `MANUAL.md` 참고.
> ✅ **v2.1.0:** 로드맵 2번(LLM 요약 파이프라인) 구현.
> ⚠️ **v2.0.0 정정 이력:** 이전 v1.2.0 문서는 실제 코드와 달라 재작성.

---

## 1. 프로젝트 개요 & 아키텍처

로컬 PC 환경에서 웹 커뮤니티·유튜브·AI 인물 갤러리 데이터를 수집하고, **Ollama 로컬 LLM으로 요약·종합 브리핑**을 생성하여, 미디어(이미지/영상 임베드)를 포함한 반응형 HTML 뷰어(`FINAL_ACTION_REPORT.html`)와 실무 마크다운 리포트(`FINAL_ACTION_REPORT.md`)를 자동 빌드하는 파이프라인입니다. 여기에 로컬 LLM을 LiteLLM 프록시로 노출하고 Open Interpreter 에이전트로 다루는 **별도의 대화형 트랙**이 함께 존재합니다.

이 저장소에는 **두 개의 트랙**이 있습니다. (트랙 A는 이제 LLM을 사용하며, 트랙 B는 독립적인 대화형 에이전트입니다.)

```text
[트랙 A] 크롤링 → LLM 요약/브리핑 → 리포트 조립
  [데이터 소스]
    ├─ 루리웹 유머/이슈 (crawl_humor.py, 본문 5건 + 미디어 태그)
    ├─ 유튜브 스포츠 (crawl_youtube_sports.py, 임베드 최대 50건)
    └─ AI 인물 갤러리 (crawl_ai_portraits.py, Unsplash 스톡 25종×2 = 50건)
            │
            ▼ (원문/미디어 메타데이터를 .txt로 저장)
  [D:\로컬llm\workspaces\raw_inputs\*.txt]
            │
            ▼ (pipeline_orchestrator.py)
    ├─ hermes3:8b  ── 개별 글 요약 ──▶ [refined_data\*.md]  (콘텐츠 해시 캐시)
    └─ qwen2.5:14b ── 종합 브리핑 ──┐
            │                        ▼
            ▼ (렌더링)
  [D:\로컬llm\workspaces\final_outputs\]
    ├─ FINAL_ACTION_REPORT.md    (종합 브리핑 + 전체 개별 요약, 모든 소스 대상)
    └─ FINAL_ACTION_REPORT.html  (ai_portrait 갤러리 + 🤖 LLM 요약 주입)

[트랙 B] 로컬 LLM 대화형 에이전트  (config.yaml)
  Ollama(:11434) ──▶ LiteLLM Proxy(:4000, config.yaml) ──▶ Open Interpreter CLI
    모델: hermes3:8b (local-agent / agent-ai), qwen3.5:9b (local-qwen)
```

### 설계 노트 (트랙 A LLM 파이프라인)

* **백엔드:** 기본은 Ollama OpenAI 호환 엔드포인트(`:11434/v1`). 환경변수 `OLLAMA_BASE`를 `http://localhost:4000/v1`로 바꾸면 LiteLLM 프록시 경유로 전환됩니다.
* **모델 선택:** 요약=`hermes3:8b`, 브리핑=`qwen2.5:14b`(기본값). ⚠️ `qwen3.5:9b`는 **reasoning(thinking) 모델**이라 `content` 없이 사고과정만 반환 → 브리핑용으로 부적합해 기본값에서 제외했습니다. 필요 시 `SUMMARY_MODEL`/`BRIEFING_MODEL` 환경변수로 교체.
* **캐시:** 크롤러가 매 실행 시 `.txt`를 지우므로 mtime이 아닌 **원문 SHA-256 해시**로 캐시합니다. 포트레이트는 결정론적(동일 URL·seed)이라 재크롤 후에도 캐시가 유효해 50회 재호출을 절약합니다.
* **폴백:** Ollama 미실행·모델 오류 시 원문 발췌로 대체하고 HTML은 계속 생성하되, 실패 건수를 `.md` 헤더에 명시합니다(무음 실패 방지).
* **범위:** `.md` 리포트는 `raw_inputs`의 **모든 소스**를 커버. HTML 갤러리는 구조상 포트레이트 전용(배지·프롬프트 박스)이라 `ai_portrait_*`만 렌더링 — 범용 렌더러는 로드맵 3번.

### 🚧 남은 계획 (미구현)

* **humor/youtube의 HTML 반영**: 마크다운 리포트에는 모든 소스가 들어가지만, HTML 갤러리는 여전히 포트레이트 전용. 소스 무관 범용 카드 렌더러가 필요(로드맵 3번).
* **크롤러 상호 삭제 해소**: 여러 소스를 한 리포트에 담으려면 크롤러의 `.txt` 전체 삭제 로직을 prefix 단위로 바꿔야 함(로드맵 3번).

---

## 2. 디렉터리 구조 및 파일 역할

```text
D:\로컬LLM\
 ├── 0_크롤러실행.bat                # 크롤러 실행 배치 (현재 crawl_ai_portraits.py 고정 호출)
 ├── 1_서버실행_LiteLLM.bat          # [트랙 B] LiteLLM 프록시 서버 기동 (포트 4000)
 ├── 2_에이전트실행_Interpreter.bat   # [트랙 B] Open Interpreter 대화형 에이전트 실행
 ├── 4_하이브리드_파이프라인실행.bat    # [트랙 A] pipeline_orchestrator.py 실행 → HTML 조립
 ├── config.yaml                    # [트랙 B] LiteLLM 모델 매핑 (Ollama 백엔드)
 ├── crawl_humor.py                 # [트랙 A/모듈1] 루리웹 유머 본문+미디어 크롤러 (limit=5)
 ├── crawl_youtube_sports.py        # [트랙 A/모듈2] 유튜브 스포츠 임베드 수집기 (limit=50)
 ├── crawl_ai_portraits.py          # [트랙 A/모듈3] Unsplash 인물 사진 50건 데이터셋 생성기
 ├── pipeline_orchestrator.py       # [트랙 A] LLM 요약·브리핑 + HTML/MD 리포트 조립 엔진
 ├── local_llm_easy_manual.pdf      # 참고 매뉴얼 (문서)
 ├── AnyDesk.exe / Chatbox-*.exe    # 외부 설치 도구 (프로젝트 코드 아님)
 └── workspaces\
      ├── raw_inputs\               # 수집된 원본 텍스트 + 미디어 메타데이터 (.txt)
      ├── refined_data\             # 개별 LLM 요약 캐시 (.md, SRC-HASH 헤더로 재사용 판정)
      └── final_outputs\            # 최종 산출물 (FINAL_ACTION_REPORT.html / .md)
```

> ⚠️ **크롤러 간 상호 삭제 주의:** `crawl_ai_portraits.py`와 `crawl_youtube_sports.py`는 실행 시작 시 `raw_inputs\` 내 **모든 `.txt`를 삭제**합니다. 따라서 크롤러를 연달아 실행하면 마지막에 실행한 크롤러의 데이터만 남습니다. (`crawl_humor.py`는 삭제하지 않고 추가만 함.)

---

## 3. 세션 트러블슈팅 히스토리 (Troubleshooting Ledger)

다른 세션에서 동일 이슈 발생 시 아래 해결 로직을 참조합니다.

| 이슈 증상 | 발생 원인 | 해결 조치 |
| --- | --- | --- |
| **`OSError: [Errno 22] Invalid argument`** | 크롤링 제목 내 개행문자(`\n`) 및 특수문자로 인한 파일 저장 실패 | `re.sub(r'[\\/*?:"<>\|\r\n\t]', '', title)` 정규식으로 파일명 강제 정제 |
| **배치 파일 명령어 인식 에러 (`'mor'`, `'한국'` 등)** | `.bat` 저장 인코딩(UTF-8 BOM vs ANSI) 불일치로 한글 주석/경로 깨짐 | 불필요 한글 주석 제거, `chcp 65001` 적용. ✅ **해결됨(2026-08-21):** `0_`,`2_`의 경로 소실(`D:\??llm`) 복구, 배치 4종(`0_`·`1_`·`2_`·`4_`)을 UTF-8(BOM 없음) + `chcp 65001` 패턴으로 통일 |
| **유튜브 임베드 오류 153** | `file:///` 로컬 프로토콜 실행 시 Referer 부재로 유튜브 정책 차단 | `youtube-nocookie.com` 적용 및 iframe에 `referrerpolicy="strict-origin-when-cross-origin"` 삽입 (※ 현재 크롤러는 일반 `youtube.com/embed` 사용 — 로컬 실행 시 재현 가능) |
| **Lexica API WAF/SSL 에러** | Cloudflare WAF 차단 및 Python 3.13 OpenSSL 충돌 | Lexica 대신 안정적인 CDN(현재 Unsplash) 직접 호출로 전환 |
| **모든 카드가 동일 사진으로 나오는 현상** | HTML 렌더러 `onerror`에 고정 이미지 URL 하드코딩되어 강제 fallback | 고정 fallback 제거, 개별 인물 이미지 URL 매핑으로 개별 렌더링 보장 |
| **HTML 텍스트 프레임 이탈** | 긴 URL/프롬프트에 줄바꿈 속성 부재 | CSS에 `word-break: break-word`, `overflow-wrap: anywhere` 적용 |

---

## 4. 운영 및 실행 지침서 (Standard Operating Procedure)

### 환경 요구사항

* **Python 3.10+** (테스트 환경: 3.13.6)
  * 트랙 A 크롤링: `requests`, `beautifulsoup4`
  * 트랙 A 파이프라인(LLM): `openai` (2.x, OpenAI 호환 클라이언트)
  * 트랙 B 에이전트: `litellm`, `open-interpreter` (`%APPDATA%\Python\Python313\Scripts\` 에 설치됨)
* **Ollama 로컬 실행** (`http://localhost:11434`)
  * 설치 확인된 모델: `hermes3:8b`, `qwen3.5:9b`, `qwen2.5:7b`, `qwen2.5:14b`
  * 파이프라인 기본 모델: 요약 `hermes3:8b`, 브리핑 `qwen2.5:14b`
  * ⚠️ `qwen3.5:9b`는 reasoning 모델이라 브리핑용으로 부적합 (§1 설계 노트 참고). 사용 전 `ollama list`로 태그 확인 권장.
* **파이프라인 환경변수(선택):** `OLLAMA_BASE`(기본 `:11434/v1`, LiteLLM은 `:4000/v1`), `SUMMARY_MODEL`, `BRIEFING_MODEL`, `LLM_TIMEOUT`(기본 180s), `MAX_FILES`(0=전체, 테스트용 제한)

### 트랙 A — 방법 ①: 대시보드 (권장)

* `3_대시보드실행.bat` 실행 → 브라우저에서 `http://localhost:8501` 자동 오픈.
* 사이드바에서 소스 선택 → **크롤링 실행** → **파이프라인 실행**, 우측 탭에서 브리핑·리포트 확인.

### 트랙 A — 방법 ②: 배치 수동 실행

1. **크롤러 가동:** `0_크롤러실행.bat` 실행 (현재 `crawl_ai_portraits.py` 고정 호출)
   * 대상 변경 시 `0_크롤러실행.bat` 내부 파이썬 파일명을 교체 (`crawl_humor.py` / `crawl_youtube_sports.py` / `crawl_ai_portraits.py`)
   * ⚠️ 크롤러 간 `.txt` 상호 삭제 주의 (§2 참고). 여러 소스를 합치려면 코드 수정 필요.
2. **파이프라인 실행:** `4_하이브리드_파이프라인실행.bat` 실행 → 개별 요약(캐시) → 종합 브리핑 → `.md`/`.html` 생성
   * 첫 실행은 Ollama 모델 콜드 로드 + 전체 요약으로 수 분 소요. 재실행 시 캐시로 빨라짐.
3. **결과 확인:**
   * 종합 리포트: `workspaces\final_outputs\FINAL_ACTION_REPORT.md`
   * 갤러리 뷰어: `workspaces\final_outputs\FINAL_ACTION_REPORT.html` (브라우저로 열기)

### 트랙 B — 로컬 LLM 대화형 에이전트

1. **프록시 서버 기동:** `1_서버실행_LiteLLM.bat` 실행 (포트 4000, `config.yaml` 로드)
2. **에이전트 실행:** `2_에이전트실행_Interpreter.bat` 실행 → `http://localhost:4000/v1` 로 접속하는 Open Interpreter CLI

---

## 5. 개발 로드맵 이력 (Completed & Next)

### ✅ 완료 (2026-08-21 세션)

1. **[정합성 복구]** 배치 파일 경로 소실(`D:\??llm`) 복구, 배치 4종 UTF-8 + `chcp 65001` 통일.
2. **[LLM 파이프라인]** `pipeline_orchestrator.py`가 Ollama를 호출해 개별 요약(hermes3) → 종합 브리핑(qwen2.5:14b) → `refined_data\*.md`·`FINAL_ACTION_REPORT.md` 생성. 콘텐츠 해시 캐시·폴백 포함.
3. **[멀티소스 리포트]** `.md`는 전 소스 커버, HTML은 소스별 카드(portrait/sports/humor) 범용 렌더러로 확장. 크롤러 `.txt` 삭제를 prefix 단위로 변경해 소스 공존 가능.
4. **[GUI / WebUI]** Streamlit 대시보드(`app.py`) — 소스 선택 → 크롤링/파이프라인 실행(로그 스트리밍) → 브리핑·리포트 뷰어 일원화. 실행: `3_대시보드실행.bat`.
5. **[로컬 웹서버]** `file:///` 제약 해소 — `serve_viewer()` + `5_뷰어서버실행.bat`(포트 8000, 자동 브라우저 오픈). 대시보드는 캐시된 백그라운드 서버로 리포트 임베드.
6. **[이미지 로컬 다운로더]** portrait 이미지 + sports 썸네일을 `workspaces\images\`에 저장하고 HTML을 상대경로(`../images/...`)로 재바인딩. 파이프라인에 통합(기본 ON).

### 🚧 다음 (고도화 대상)

* **humor/sports 이미지·미디어의 완전 로컬화**: 현재 humor 본문 인라인 미디어와 sports 유튜브 임베드는 온라인 의존. 로컬 캐싱 확장 여지.
* **Track B 의존성 격리**: Streamlit 설치로 `open-interpreter`와 공유 패키지 충돌 발생 → venv 분리 권장(§6 참고).
* **자동화/스케줄링**: 크롤링→파이프라인 주기 실행(작업 스케줄러) 및 리포트 아카이빙.
* (이후 항목은 사용자가 정의할 고도화 개발문서로 대체 예정.)

---

## 6. 알려진 이슈 / 주의

* **Track B 패키지 충돌:** 이번 세션에서 Streamlit(트랙 A GUI)을 전역 설치하면서 `open-interpreter 0.4.3`이 핀한 `starlette`/`tiktoken`/`typer`/`psutil`/`send2trash`가 상위 버전으로 올라가 충돌 경고가 발생했습니다. 트랙 B(대화형 에이전트)가 오작동하면 **전용 venv로 분리**하세요:
  ```powershell
  python -m venv .venv-agent
  .\.venv-agent\Scripts\activate
  pip install open-interpreter litellm
  ```
* **크롤러 소스 선택:** `0_크롤러실행.bat`은 `crawl_ai_portraits.py` 고정. 다른 소스는 대시보드(`app.py`)에서 선택하거나 배치 내 파일명을 교체.
* **Ollama 필수:** 파이프라인은 `localhost:11434`에 Ollama와 모델(`hermes3:8b`, `qwen2.5:14b`)이 있어야 정상 요약. 없으면 원문 폴백으로 리포트만 생성(폴백 건수는 `.md` 헤더에 표기).
