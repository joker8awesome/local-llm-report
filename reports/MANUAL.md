# 📖 로컬 LLM & 멀티미디어 크롤링 파이프라인 — 사용 매뉴얼

**매뉴얼 버전:** v2.0.0
**대상 시스템:** 로컬 LLM 크롤링 파이프라인 (코드 v3.0-dev — DEV-02 완료, DEV-03 Phase 1~2)
**작성일:** 2026-08-21
**작업 경로:** `D:\로컬LLM`

> 이 문서는 **현재 완성된 시스템의 스펙·기능·사용법**을 정리한 사용자 매뉴얼입니다.
> 내부 개발 이력·트러블슈팅 원장은 [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md)를 참고하세요.
> §1~§9는 기반 시스템(v2.2.0), **§10은 v3 확장(모델 업그레이드·RAG·STT·에이전트)** 을 다룹니다.

---

## 1. 이 시스템은 무엇인가

로컬 PC에서 **웹 데이터를 수집 → 로컬 LLM으로 요약/브리핑 → 리포트로 시각화**하는 자동화 파이프라인입니다. 외부 유료 API 없이 **Ollama 로컬 모델**만으로 동작합니다.

**두 개의 독립 트랙:**

| 트랙 | 목적 | 진입점 |
| --- | --- | --- |
| **트랙 A** | 크롤링 → LLM 요약/브리핑 → 리포트 (핵심 파이프라인) | `3_대시보드실행.bat` (권장) 또는 배치 수동 실행 |
| **트랙 B** | 로컬 LLM을 프록시로 노출한 대화형 에이전트 | `1_`·`2_` 배치 (Open Interpreter) |

---

## 2. 시스템 스펙 & 요구사항

### 실행 환경
| 항목 | 사양 |
| --- | --- |
| OS | Windows 11 |
| Python | 3.10+ (검증 환경 3.13.6) |
| LLM 런타임 | Ollama (`http://localhost:11434`) |
| 대시보드 | Streamlit 1.62 |

### 필수 Python 패키지
```
requests          # 크롤링 + 이미지 다운로드
beautifulsoup4    # HTML 파싱 (crawl_humor)
openai            # Ollama OpenAI 호환 클라이언트 (2.x)
streamlit         # 대시보드 GUI (트랙 A)
litellm           # 트랙 B 프록시
open-interpreter  # 트랙 B 에이전트
```

### 설치된 Ollama 모델
`hermes3:8b`, `qwen2.5:7b`, `qwen2.5:14b`, `qwen3.5:9b`

| 용도 | 기본 모델 | 비고 |
| --- | --- | --- |
| 개별 요약 | `hermes3:8b` | 빠른 instruct 모델 |
| 종합 브리핑 | `qwen2.5:14b` | 고품질 instruct 모델 |
| ⚠️ 사용 금지(브리핑) | `qwen3.5:9b` | **reasoning 모델** — `content` 없이 사고과정만 반환하여 브리핑 부적합 |

---

## 3. 파일 & 디렉터리 맵

```text
D:\로컬LLM\
 ├── 0_크롤러실행.bat             # 크롤러 단독 실행 (crawl_ai_portraits.py 고정)
 ├── 1_서버실행_LiteLLM.bat       # [트랙 B] LiteLLM 프록시 (:4000)
 ├── 2_에이전트실행_Interpreter.bat # [트랙 B] Open Interpreter CLI
 ├── 3_대시보드실행.bat           # [트랙 A] Streamlit 대시보드 (권장 진입점)
 ├── 4_하이브리드_파이프라인실행.bat # [트랙 A] 파이프라인 단독 실행
 ├── 5_뷰어서버실행.bat           # 리포트 로컬 뷰어 서버 (:8000, 자동 브라우저)
 ├── app.py                      # Streamlit 대시보드 본체
 ├── config.yaml                 # [트랙 B] LiteLLM 모델 매핑
 ├── crawl_ai_portraits.py       # 크롤러: AI 인물(Unsplash 스톡 50건)
 ├── crawl_youtube_sports.py     # 크롤러: 유튜브 스포츠(임베드 ~50건)
 ├── crawl_humor.py              # 크롤러: 루리웹 유머 본문+미디어(5건)
 ├── pipeline_orchestrator.py    # 파이프라인 엔진 (요약·브리핑·리포트·이미지)
 └── workspaces\
      ├── raw_inputs\            # 크롤링 원본 (.txt) — 소스별 prefix
      ├── refined_data\          # 개별 LLM 요약 캐시 (.md, SRC-HASH 헤더)
      ├── images\                # 로컬 다운로드 이미지 (.jpg)
      └── final_outputs\         # 최종 산출물
           ├── FINAL_ACTION_REPORT.md    # 종합 브리핑 + 개별 요약
           └── FINAL_ACTION_REPORT.html  # 소스별 카드 리포트 뷰어
```

**배치 파일 인코딩:** 모두 UTF-8(BOM 없음) + `chcp 65001`로 통일됨.

---

## 4. 기능 목록

### 크롤러 (3종)
| 크롤러 | 대상 | 산출 파일 | 특징 |
| --- | --- | --- | --- |
| `crawl_ai_portraits.py` | Unsplash 인물 사진 25종×2 = 50건 | `ai_portrait_*.txt` | 결정론적(고정 URL·seed) |
| `crawl_youtube_sports.py` | 유튜브 한국 스포츠 검색 결과 | `sports_*.txt` | iframe 임베드 블록 저장 |
| `crawl_humor.py` | 루리웹 유머 베스트 본문 5건 | `humor_*.txt` | 본문 내 이미지/영상 태그 보존 |

> **소스 공존:** 각 크롤러는 **자기 prefix(`ai_portrait_`/`sports_`/`humor_`)만 삭제** 후 재수집하므로, 세 소스를 순차 실행해도 서로 덮어쓰지 않습니다.

### 파이프라인 (`pipeline_orchestrator.py`)
- **개별 요약:** 각 원본을 `hermes3:8b`로 2~3문장 요약 → `refined_data\*.md`
- **콘텐츠 해시 캐시:** 원문 SHA-256으로 캐시. 재크롤 후에도 동일 콘텐츠는 재호출 없이 재사용
- **종합 브리핑:** 전체 요약을 `qwen2.5:14b`로 종합(총평·주요 흐름·실무 시사점) → `FINAL_ACTION_REPORT.md`
- **이미지 로컬 다운로드:** portrait 이미지 + sports 썸네일을 `images\`에 저장, HTML을 상대경로로 재바인딩 (엑박 방지)
- **범용 HTML 리포트:** portrait/sports/humor를 소스별 카드로 렌더 + 🤖 LLM 요약 주입
- **폴백:** Ollama 미실행/모델 오류 시 원문 발췌로 대체하고, 실패 건수를 리포트 헤더에 명시

### 대시보드 (`app.py`)
- 사이드바에서 수집 소스 다중 선택 → 크롤링 실행(실시간 로그 스트리밍)
- 브리핑 모델·이미지 다운로드·파일 수 제한 옵션 → 파이프라인 실행
- 탭: **종합 브리핑**(마크다운) / **리포트 뷰어**(HTML 임베드) / **실행 로그**

---

## 5. 사용법

### 방법 ① 대시보드 (권장)
1. Ollama 실행 확인 (`ollama list`)
2. `3_대시보드실행.bat` 더블클릭 → `http://localhost:8501` 자동 오픈
3. 사이드바:
   - **수집 소스 선택** (AI 인물 / 유튜브 스포츠 / 유머)
   - **크롤링 실행** 버튼
   - 옵션 확인 후 **파이프라인 실행** 버튼
4. 우측 탭에서 브리핑·리포트 확인

### 방법 ② 배치 수동 실행
1. **크롤링:** `0_크롤러실행.bat` (다른 소스는 배치 내 파일명 교체 또는 대시보드 이용)
2. **파이프라인:** `4_하이브리드_파이프라인실행.bat`
   - 첫 실행은 모델 콜드 로드 + 전체 요약으로 **수 분 소요**, 재실행은 캐시로 빠름
3. **리포트 열기:** `5_뷰어서버실행.bat` (또는 `workspaces\final_outputs\FINAL_ACTION_REPORT.html` 직접 열기)

### 환경변수 (파이프라인 커스터마이징)
| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `OLLAMA_BASE` | `http://localhost:11434/v1` | LiteLLM 경유 시 `http://localhost:4000/v1` |
| `SUMMARY_MODEL` | `hermes3:8b` | 개별 요약 모델 |
| `BRIEFING_MODEL` | `qwen2.5:14b` | 종합 브리핑 모델 (비-reasoning 권장) |
| `LLM_TIMEOUT` | `180` | 요청 타임아웃(초), 콜드 로드 대비 |
| `MAX_FILES` | `0` | 처리 파일 수 제한 (0=전체) |
| `DOWNLOAD_IMAGES` | `1` | 이미지 로컬 다운로드 (0=끔) |
| `SERVE` / `SERVE_PORT` | `0` / `8000` | 파이프라인 종료 후 뷰어 서버 자동 기동 |

예시(PowerShell):
```powershell
$env:MAX_FILES=5; $env:BRIEFING_MODEL="qwen2.5:7b"; python pipeline_orchestrator.py
```

---

## 6. 데이터 포맷

### 원본 `.txt` (raw_inputs) 공통 스키마
```text
제목: ...
원문링크: https://...

[메타데이터]         ← portrait/sports 만 (humor 없음)
- key: value

[미디어영역]         ← portrait=이미지URL, sports=iframe 블록 (humor 없음)
...

[본문 전문]
...

[출처 URL]
https://...
```

### 요약 캐시 `.md` (refined_data)
```markdown
<!-- SRC-HASH: <16자리 해시> -->
<!-- MODEL: hermes3:8b -->

# <제목>
**종류:** portrait  |  **원문:** <url>

## 요약
<LLM 요약문>
```
`SRC-HASH`가 원문 해시와 일치하면 재사용, 불일치 시 재요약.

---

## 7. 아키텍처 / 데이터 흐름

```text
크롤러(3종) ──▶ raw_inputs/*.txt (소스별 prefix)
                     │
                     ▼  pipeline_orchestrator.py
   ┌─────────────────┼──────────────────────────┐
   ▼                 ▼                           ▼
이미지 다운로드   hermes3:8b 요약            qwen2.5:14b 브리핑
images/*.jpg     refined_data/*.md          (전체 요약 종합)
   │                 │                           │
   └────────┬────────┴───────────┬───────────────┘
            ▼                     ▼
  FINAL_ACTION_REPORT.html   FINAL_ACTION_REPORT.md
  (소스별 카드 + 요약)        (브리핑 + 개별 요약)
            │
            ▼  app.py (Streamlit) / 5_뷰어서버실행.bat
       브라우저 뷰어 (:8501 / :8000)
```

---

## 8. 트러블슈팅 (요약)

| 증상 | 조치 |
| --- | --- |
| 브리핑이 비어 있음/실패 | 브리핑 모델이 reasoning(`qwen3.5:9b`)인지 확인 → `qwen2.5:14b`로 변경 |
| 리포트 폴백 건수 표시 | Ollama 미실행/모델 없음 → `ollama list`로 모델 확인 후 재실행 |
| 이미지 엑박 | `DOWNLOAD_IMAGES=1`로 재실행 → `images\`에 로컬 저장·상대경로 바인딩 |
| 유튜브 임베드 안 뜸 | `file:///` 대신 뷰어 서버(`5_뷰어서버실행.bat`) 사용 |
| 배치 실행 시 한글 경로 오류 | 배치는 UTF-8 + `chcp 65001` 유지 필요 (현재 통일됨) |
| 트랙 B 에이전트 오작동 | Streamlit과 패키지 충돌 → 전용 venv 분리 (아래) |

**Track B venv 분리:**
```powershell
python -m venv .venv-agent
.\.venv-agent\Scripts\activate
pip install open-interpreter litellm
```

자세한 이슈 원장은 [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) §3, §6 참고.

---

## 9. 변경 이력

| 버전 | 내용 |
| --- | --- |
| 코드 v3.0-dev | (DEV-02) EXAONE 요약·구조화 출력·KURE-v1 RAG·bench·Gemini / (DEV-03) STT·Telegram 에이전트 |
| 코드 v2.2.0 | 멀티소스 렌더러, Streamlit 대시보드, 로컬 뷰어 서버, 이미지 다운로더 |
| 코드 v2.1.0 | LLM 요약/브리핑 파이프라인 구현 |
| 코드 v2.0.0 | 실제 코드 기준 문서 재작성, 배치 인코딩 정상화 |

---

## 10. v3 확장 (DEV-02 모델 업그레이드 / DEV-03 확장)

### 10.1 신규 모델
| 용도 | 모델 | 비고 |
| --- | --- | --- |
| 개별 요약 | **EXAONE 3.5 7.8B** (`exaone3.5:7.8b`) | 한국어 특화. 미설치 시 `hermes3:8b` 자동 폴백 |
| 종합 브리핑 | `qwen2.5:14b` (기본) | 3파전 A/B 후 확정 예정 |
| 에이전트 | `qwen2.5:14b` | Telegram 도구 호출 |
| 임베딩(RAG) | **KURE-v1** (`nlpai-lab/KURE-v1`, CPU) | 1024차원, sentence-transformers |
| STT | **faster-whisper large-v3** (int8) | CUDA 자동감지→CPU 폴백, VAD 필수, ko 고정 |

### 10.2 §2 구조화 출력
- 요약이 JSON 스키마(`summary`·`tags`·`importance`·`source_type`)로 생성됨(Pydantic 검증, temperature 0, 1회 재시도 후 폴백).
- `refined_data\*.md` 헤더 주석에 `SRC-HASH`·`MODEL`·`SCHEMA-VER`·`TAGS`·`IMPORTANCE`·`SOURCE_TYPE` 저장.
- **캐시 무효화:** SRC-HASH + MODEL + SCHEMA-VER가 모두 일치할 때만 재사용(모델/스키마 변경 시 재요약).

### 10.3 신규 파일 & 실행
| 파일 | 용도 | 실행 |
| --- | --- | --- |
| `ab_summary.py` | §1.1 요약 모델 A/B (hermes3 vs EXAONE) | `python ab_summary.py` → `workspaces/ab_summary/` |
| `bench_briefing.py` | §1.2 브리핑 3파전 + 블라인드 채점 요청서 | `python bench_briefing.py` → `workspaces/bench_briefing/` |
| `rag.py` | RAG 인덱싱/질의/중복제거 | `python rag.py index` / `query "질문"` / `dedup` |
| `gemini_client.py` | §5 Gemini 무료 API(민감정보 차단·백오프·브릿지 폴백) | `GEMINI_API_KEY=... python gemini_client.py "..."` |
| `transcribe_youtube.py` | Phase 1 STT | `python transcribe_youtube.py urls <URL>` / `from-sports N` / `voice` |
| `gpu_lock.py` | §0 GPU 동시성 락 | (자동) `workspaces\.pipeline.lock` |
| `agent_tools.py` | Phase 2 도구 5종 | (telegram_agent가 사용) |
| `telegram_agent.py` | Phase 2 Telegram 에이전트 | `TELEGRAM_BOT_TOKEN=... TELEGRAM_ALLOWED_IDS=... python telegram_agent.py` |

- 대시보드(`app.py`)에 **"아카이브 질의"** 탭 추가(RAG 인덱스 갱신/중복 클러스터/질의응답).

### 10.4 신규 환경변수
| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `SUMMARY_MODEL` | `exaone3.5:7.8b` | 요약 모델(미설치 시 hermes3 폴백) |
| `STRUCTURED` | `1` | 구조화 출력 on/off |
| `EMBED_MODEL` | `nlpai-lab/KURE-v1` | RAG 임베딩 모델 |
| `RAG_SOURCE_DIR` | `refined_data` | 인덱싱 대상(아카이브 계층 구현 시 교체) |
| `DEDUP_THRESHOLD` | `0.88` | 중복 클러스터 코사인 임계 |
| `WHISPER_MODEL` | `large-v3` | STT 모델 |
| `MAX_TRANSCRIBE_MINUTES` | `30` | 전사 영상 길이 상한 |
| `GEMINI_API_KEY` | (없음) | Gemini 키(환경변수 전용, 커밋 금지) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_ALLOWED_IDS` | (없음) | 봇 토큰·허용 사용자 ID(커밋 금지) |

### 10.5 의존성·venv 주의
- 신규 패키지: `pydantic`, `sentence-transformers`, `chromadb`, `feedparser`, `trafilatura`, `google-genai`, `faster-whisper`, `yt-dlp`, `python-telegram-bot`. (`ffmpeg` 시스템 설치 필요 — 확인됨)
- **CUDA 참고:** `torch`는 CPU 전용이나 STT(CTranslate2)는 자체 CUDA를 감지해 GPU 사용. RAG 임베딩(KURE-v1)은 의도적으로 **CPU 고정**(GPU OOM 방지).
- **Track B / MeloTTS(Phase 4 예정)** 는 의존성 충돌로 **전용 venv 분리** 권장(§8, DEV-03 §4.1).

### 10.6 사용자 조치 대기(게이트)
- **브리핑 모델 확정:** `workspaces/bench_briefing/BENCH_REVIEW_REQUEST.md`를 클라우드 브레인에 붙여넣어 채점 → 승자를 `BRIEFING_MODEL`로 설정.
- **Gemini 실호출:** `GEMINI_API_KEY` 설정 시 검증.
- **Telegram 에이전트:** BotFather 토큰 + 본인 user ID 필요.

---

## 11. 웹 운영 콘솔 (DEV-07 — 원격 보기 + 클릭 트리거)

브라우저에서 파이프라인 상태·수집물·오류·건강을 **원격 조회**하고, 조회/실행 명령을 **클릭으로 트리거**한다.
2계층: ① 정적 대시보드(`report_site/console.html`, GitHub Pages) ② 로컬 명령 폴러(`console_poller.py`).

### 11.1 구성 파일
| 파일 | 역할 |
| --- | --- |
| `export_web_data.py` | metrics·refined_data·건강 → `report_site/data/*.json` 발행(**새니타이즈**: 경로·토큰·개인문서 배제). `--push`로 git push |
| `report_site/console.html` | 대시보드(개요·실행이력·오류·수집물·건강·명령). 60초 자동갱신 |
| `console_poller.py` | 저장소를 주기 pull → 명령 검증·실행 → 결과 push. 이슈 자동화 포함 |
| `report_site/commands/` | 파일 명령 큐(`pending/`, `confirm/`) — 대시보드가 Contents API로 기록 |
| `report_site/data/commands_log.json` | 명령 처리 로그(대시보드 "명령 로그"에 표시) |

### 11.2 실행 순서
1. **폴러 상시 구동(로컬):** `python console_poller.py` (주기 `CONSOLE_POLL_SEC`, 기본 45초).
2. **파이프라인 실행 시 자동 발행:** `pipeline_orchestrator.py` 종료 시 `data/` 발행+push(`WEB_EXPORT=0`/`WEB_PUSH=0`로 비활성).
3. **대시보드 접속:** GitHub Pages URL 또는 로컬 `python -m http.server`(report_site 폴더)로 `console.html`.

### 11.3 대시보드 PAT 발급(명령 전송용, 조회는 불필요)
- 조회(실행이력·오류·수집물·건강)는 **PAT 없이** 동작. **명령 전송에만** PAT 필요.
- GitHub → Settings → Developer settings → **Fine-grained PAT** → 대상 저장소 `local-llm-report`만 → 권한 **Contents: Read and write** 만 부여.
- 대시보드 우측 상단 **⚙ 설정** → PAT 입력 → 저장. **PAT는 이 브라우저 localStorage에만 저장**되며 저장소·HTML에 절대 포함되지 않는다.

### 11.4 명령 화이트리스트(고정 5종 — 신규 추가 금지)
- 조회: `pipeline_status`, `get_briefing`, `search_archive` — 즉시 처리.
- 실행: `trigger_crawl`(source=`humor`/`sports`/`portrait`), `trigger_pipeline` — **2단계 확인** 후 처리.
- 폴러는 화이트리스트를 `agent_tools.DISPATCH`에서 단일 임포트하여 **스스로 확장 불가**. 그 외 명령은 실행 없이 거부 로그.
- 쓰기 명령은 `pending`+`confirm` 파일이 **둘 다·id 일치·요청 후 10분 이내**일 때만 폴러가 실행(2단계를 실행 지점에서 강제). GPU 락으로 웹·Telegram 동시 트리거도 **단일 실행** 보장.

### 11.5 GitHub Pages 활성화(사용자 조치)
- **저장소가 Private + 무료 플랜이면 Pages 라이브 URL이 제공되지 않는다.** 두 경로 중 택1:
  - **(권장) 저장소를 Public 전환** → Pages 무료. 발행 데이터는 §3 새니타이즈로 **공개돼도 무해**(경로·토큰·개인문서·원문 전문 없음)하도록 설계됨.
  - **GitHub Pro 유지 + Private** → Private Pages 사용.
- 활성화: 저장소 **Settings → Pages → Source: Deploy from a branch → `main` / `/ (root)`** → 저장. 수 분 후 `https://joker8awesome.github.io/local-llm-report/console.html` 접속.

### 11.6 이슈 자동화(Phase 5)
- 폴러가 **최근 2회 연속 실행 실패** 또는 **소스 급감 경보** 감지 시 GitHub 이슈 자동 생성(중복 방지). `CONSOLE_ISSUES=0`로 비활성.
- 이슈 생성에는 `gh` CLI가 **Issues 쓰기 권한**을 가진 계정으로 로그인돼 있어야 한다(현재 push용 토큰은 Contents 전용이라 실패할 수 있음 — 비치명적으로 스킵).
