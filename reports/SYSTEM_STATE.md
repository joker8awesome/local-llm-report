# 시스템 현재 상태 종합 (스펙 · 모델 · 자료수집)

**작성일:** 2026-08-21
**용도:** 업무 방향 수립 플랜용 현행 스냅샷
**코드 상태:** v3.0-dev (DEV-02 완료 / DEV-03 Phase 1~2 부분 / DEV-05·06 B안 부분 선행)
**경로:** `D:\로컬LLM`

> 본 문서는 "지금 무엇이 어떻게 세팅되어 있고, 데이터가 어떤 디테일로 들어오는가"를 한 장에 모은 현행 기준선이다.
> 개발 이력·판정은 [`PARTIAL_OPT_REPORT.md`](PARTIAL_OPT_REPORT.md), 사용자 매뉴얼은 [`MANUAL.md`](MANUAL.md), 향후 설계는 [`PRD_본문_v3.md`](PRD_본문_v3.md), **보류(착수 금지) 목록은 [`DEFERRED_ITEMS.md`](DEFERRED_ITEMS.md)** 참조.

---

## 1. 하드웨어 · 런타임 (모든 결정의 물리적 상한)

| 항목 | 사양 | 실측/제약 |
| --- | --- | --- |
| GPU | NVIDIA RTX 4070 Ti | **VRAM 12,282 MiB** |
| RAM | 32 GB | CPU 오프로딩 여유 있으나 속도 급락 |
| OS | Windows 11 | 작업 스케줄러 사용, **WDDM 드라이버** |
| Python | 3.13.6 | |
| LLM 런타임 | Ollama `http://localhost:11434` | OpenAI 호환 `/v1` 사용 |

**VRAM 실측 예산 (VRAM_AUDIT.md):**
- **데스크톱/브라우저 상시 점유 ≈ 1,450 MB** (explorer·Chrome·Edge WebView·NVIDIA Overlay·Docker·Claude 등)
- **모델 실가용 ≈ 10,832 MB** (12,282 − 1,450). ← 예산 상한은 12GB가 아니라 이 값.
- ⚠️ 프로세스별 VRAM은 Windows WDDM에서 `nvidia-smi`가 `[N/A]` → **`ollama ps` + 격리 로드**로 측정.

---

## 2. 모델 세팅 (역할별)

| 역할 | 모델 | 실측 VRAM | 성격/제약 |
| --- | --- | --- | --- |
| **개별 요약** | `exaone3.5:7.8b` (4.8GB, Q4) | **6,792 MB** | 한국어 특화(LogicKor 9.08), 구조화 JSON 출력. 미설치 시 `hermes3:8b` 자동 폴백 |
| **종합 브리핑** | `qwen2.5:14b` (9.0GB, Q4) | **10,140 MB** | 비-reasoning instruct. **여유 692MB(빠듯)** — 부하 추가 전 확인 |
| **임베딩(RAG)** | `KURE-v1` (`nlpai-lab/KURE-v1`) | CPU 고정 | 1024차원, 8192토큰, 한국어 검색 특화. GPU OOM 방지 위해 CPU 강제 |
| **STT** | `faster-whisper large-v3` (int8) | **~2,500 MB (GPU)** | ✅ GPU 복구(cublas/cudnn 휠, CPU 대비 9.1배). VAD 필수, 언어 `ko` 고정. int8_float16 |
| **분류·태깅(계획)** | `qwen2.5:7b` (4.7GB) | ~미측정 | PRD 제6조/DEV-03 예정. 현재 미가동 |
| **에이전트** | `qwen2.5:14b` | 10,140 MB | Telegram tool-calling(코드 완료, 토큰 대기) |
| **reasoning(제외)** | `qwen3.5:9b` (6.6GB) | — | ⚠️ content 없이 thinking만 반환 → 요약·브리핑 **금지** |
| **bench 후보** | `qwen3:14b` (9.3GB) | — | 브리핑 3파전용. thinking 모델 → `/no_think` 적용 |

**설치된 Ollama 모델 6종:** exaone3.5:7.8b, qwen2.5:14b, qwen2.5:7b, qwen3:14b, qwen3.5:9b, hermes3:8b

**동시 상주 규칙(§0 불변 제약):**
- EXAONE(6,792) + qwen2.5:14b(10,140) = 16,932MB > 실가용 → **동시 상주 금지, 순차 로드**.
- 파이프라인은 요약(EXAONE) 종료 시 언로드 → 브리핑(qwen) → 종료 시 언로드(`keep_alive:0`, `UNLOAD_MODELS=1`).
- STT GPU 복구됨(≈2.5GB): EXAONE(6,792) + Whisper(2,500) = 9,292MB ≤ 실가용 10,832 → **동시 상주 성립**(전사·요약 단계 겹쳐도 OOM 없음).

---

## 3. 자료 수집 상세 (소스별)

수집물은 모두 `workspaces\raw_inputs\`에 **소스별 prefix `.txt`** 로 저장. 각 크롤러는 **자기 prefix만 삭제** 후 재수집(소스 공존).

### 3.1 커뮤니티 유머 — `crawl_humor.py` → `humor_*`
| 항목 | 값 |
| --- | --- |
| 대상 | 루리웹 모바일 베스트 `https://m.ruliweb.com/best/humor/now` |
| 목록 selector | `.list_item .subject a` / `a.subject_link` |
| 본문 selector(폴백체인) | `.view_content` → `.article_content` → `#article_content` → `.board_main` |
| 수집량 | `limit=5` |
| 미디어 | 본문 내 `<img>`/`<video>`/`<iframe>` 태그를 **텍스트로 보존**(HTML 렌더 시 통과) — `//`→`https:`, 상대경로 절대화, icon/emoticon 제외 |
| UA | Safari(목록)/Chrome(상세) 분리 |
| 특이 | `[메타데이터]`·`[미디어영역]` 섹션 **없음**(본문에 미디어 인라인) |

### 3.2 유튜브 스포츠 — `crawl_youtube_sports.py` → `sports_*`
| 항목 | 값 |
| --- | --- |
| 방식 | 유튜브 검색결과 HTML의 `ytInitialData` JSON 파싱(`videoRenderer`) |
| 검색 쿼리 | "한국 스포츠 하이라이트", "KBO 야구 하이라이트", "손흥민 축구 하이라이트", "배구 농구 스포츠 이슈" |
| 정렬 | 최신 업로드순(`sp=CAI%3D`) |
| 수집량 | `limit=50` |
| 저장 | 제목/채널/조회수/업로드/썸네일(`i.ytimg.com/vi/{id}/hqdefault.jpg`) + **iframe 임베드 블록**(`youtube.com/embed/{id}`) |
| 쿠키 | SOCS/CONSENT 동의 쿠키 포함 |
| 특이 | 임베드-only(본문=제목+채널+요약). **전사는 §3.4 STT로 승격** |

### 3.3 AI 인물 갤러리 — `crawl_ai_portraits.py` → `ai_portrait_*`
| 항목 | 값 |
| --- | --- |
| 실체 | **Unsplash 스톡 사진 25종 × 2회 = 50건**(FLUX/SDXL 생성물 아님, 프롬프트는 장식 텍스트) |
| 결정론성 | 고정 URL + `seed=50000+count*113`, `&v={count}` 캐시버스터 → **재크롤 시 동일**(SRC-HASH 캐시 유효) |
| 스타일 | 2사이클: "Photorealistic Masterpiece" / "Warm Vintage 35mm" |
| 특이 | `[메타데이터]`(번호/스타일/해상도/Seed) + `[미디어영역]`(이미지 URL) 보유 |

### 3.4 STT 전사 — `transcribe_youtube.py` → `yt_*` / `voice_*`
| 항목 | 값 |
| --- | --- |
| 엔진 | faster-whisper `large-v3` int8, **VAD 필수**(min_silence 500ms), 언어 `ko` 고정 |
| device | CUDA 자동감지 → 실패 시 **CPU 폴백**(현재 CPU: cublas 부재) |
| 오디오 | yt-dlp `bestaudio` → m4a, **403 우회: player_client=[android,ios,web]** |
| 길이 상한 | `MAX_TRANSCRIBE_MINUTES=30`(초과 스킵) |
| 폴백 | 다운로드 실패/자막전용 시 전사 스킵(기존 임베드 유지) |
| 음성 메모 | `workspaces\voice_inbox\` 오디오 → `voice_*` 편입(Phase 2 음성명령 연계) |
| 검증 | 8분 배구중계 2,762자 정상 전사 확인 |

### 3.5 raw_inputs 공통 스키마 (`.txt`)
```text
제목: ...                 ← 필수
원문링크: https://...      ← 필수
[메타데이터]              ← 선택(portrait/sports/yt만)
- key: value
[미디어영역]              ← 선택(이미지URL 또는 iframe블록)
...
[본문 전문]               ← 필수(전사문/프롬프트/본문. 폴백 시 발췌)
...
[출처 URL]                ← 필수
https://...
```
소스 판정(파일 prefix): `ai_portrait_`→portrait, `sports_`→sports, `humor_`→humor, `yt_`→youtube, `voice_`→voice.

---

## 4. 처리 파이프라인 (`pipeline_orchestrator.py`)

```text
raw_inputs/*.txt
  → [로드/파싱]
  → [이미지 로컬 다운로드]  portrait 이미지 + sports 썸네일 → workspaces/images/*.jpg, HTML 상대경로(../images)
  → [개별 요약]  EXAONE 구조화 JSON(summary/tags/importance/source_type), temperature 0, json_schema→json_object 폴백 1회
        · 캐시: 원문 SHA-256[:16] + MODEL + SCHEMA-VER 일치 시 재사용 → refined_data/<stem>.md
        · 실패 시 원문 발췌 폴백(캐시 안 함)
  → [EXAONE 언로드]  (§0 동시상주 방지, 실호출 있었을 때만)
  → [종합 브리핑]  qwen2.5:14b (총평/흐름/시사점), 실패 시 폴백 문구
  → [qwen 언로드]
  → [렌더]  FINAL_ACTION_REPORT.md(전 소스) + .html(소스별 카드 + 🤖요약 + 태그칩)
```

**구조화 요약 스키마 (Pydantic `DocSummary`):**
```python
summary: str          # 2~3문장 한국어
tags: list[str]       # 1~5개
importance: float     # 0.0~1.0
source_type: str      # portrait/sports/humor/youtube/voice
```

**refined_data `.md` 헤더(캐시 키):**
```
<!-- SRC-HASH: 16hex --> <!-- MODEL: exaone3.5:7.8b --> <!-- SCHEMA-VER: s1 -->
<!-- TAGS: a, b, c --> <!-- IMPORTANCE: 0.80 --> <!-- SOURCE_TYPE: ... -->
```
→ SRC-HASH·MODEL·SCHEMA-VER **모두 일치**해야 캐시 히트(모델/스키마 변경 시 자동 재요약).

---

## 5. RAG (아카이브 질의응답)

| 항목 | 값 |
| --- | --- |
| 임베딩 | KURE-v1(CPU), `normalize_embeddings=True`(코사인=내적) |
| 저장소 | ChromaDB `workspaces\chroma`, 컬렉션 `archive`, `hnsw:space=cosine` |
| 인덱싱 대상 | `refined_data/*.md`(요약+tags+importance+source_type). `RAG_SOURCE_DIR`로 교체 가능(아카이브 계층 미구현) |
| 증분 | SRC-HASH 비교 → 신규/변경만 upsert |
| 중복제거 | 코사인 임계 `0.88` union-find 클러스터링 |
| 질의 | top-K(기본5) 검색 → EXAONE이 근거문서와 함께 답변 |
| 도구화 | `rag.search()`(LLM 없이 히트) — 에이전트 `search_archive`용 |

---

## 6. 부가 시스템

| 시스템 | 파일 | 상태 |
| --- | --- | --- |
| **대시보드** | `app.py` (Streamlit) | ✅ 소스선택→크롤/파이프라인 실행(로그 스트리밍)→브리핑/뷰어/아카이브질의 4탭. 실행: `3_대시보드실행.bat` |
| **Telegram 에이전트** | `telegram_agent.py` + `agent_tools.py` | ✅ **가동 검증**(@localsrcLLM_bot). qwen2.5:14b tool-calling(텍스트 임베드 `<tool_call>` 파싱 폴백 포함), 화이트리스트 5종, 쓰기툴 확인버튼(고정 한국어 응답), 음성명령(GPU STT), user 화이트리스트 |
| **GPU 락** | `gpu_lock.py` | ✅ `workspaces\.pipeline.lock` 원자적 획득, STALE 2h 회수 |
| **계측** | `metrics.py` | ✅ `metrics.sqlite`(runs/stages/llm_calls/resources), schema_ver=2, **실측 토큰**(Ollama usage), `METRICS=1`일 때만 |
| **Gemini(무료 API)** | `gemini_client.py` | 코드 완료(키 대기). 민감정보 차단 게이트·429 백오프·브릿지 폴백 |
| **뷰어 서버** | `serve_viewer()` / `5_뷰어서버실행.bat` | ✅ workspaces 루트 서빙(:8000) |
| **트랙 B(동결)** | `1_`·`2_` bat, `config.yaml` | LiteLLM+Open Interpreter. **동결**(보존, 신규개발 없음) |

---

## 7. 환경변수 전체

| 변수 | 기본 | 설명 |
| --- | --- | --- |
| `OLLAMA_BASE` | `http://localhost:11434/v1` | LiteLLM은 `:4000/v1` |
| `SUMMARY_MODEL` | `exaone3.5:7.8b` | 미설치 시 hermes3 폴백 |
| `BRIEFING_MODEL` | `qwen2.5:14b` | reasoning 모델 금지 |
| `STRUCTURED` | `1` | 구조화 출력 on/off |
| `UNLOAD_MODELS` | `1` | 단계경계 언로드(VRAM 안전) |
| `SUMMARY_PARALLEL` | **`3`** | 요약 동시 요청(DEV-04 채택, 콜드 2.23배). 1=순차 원복 |
| (Ollama user env) | `OLLAMA_KV_CACHE_TYPE=q8_0`·`OLLAMA_FLASH_ATTENTION=1` | DEV-04 채택, VRAM −987MB |
| `VLM_CAPTION` | `0` | 요약 전 VLM 이미지 캡션 주입(Phase 5, 옵트인) |
| `TTS_SEND` | `0` | 종료 후 **금일 작업요약 음성** 텔레그램 전송(Phase 4, 옵트인) |
| `TTS_VOICE` / `TTS_POLISH` | `ko-KR-SunHiNeural` / `0` | TTS 보이스 / EXAONE 낭독 자연화 |
| `VLM_MODEL` | `qwen3-vl:8b` | VLM(미설치 시 qwen2.5vl:7b 폴백) |
| `SUMMARY_NUM_CTX`/`BRIEFING_NUM_CTX` | `0` | num_ctx(0=Ollama 기본, 실험 결과 원복) |
| `DOWNLOAD_IMAGES` | `1` | 이미지 로컬 저장 |
| `MAX_FILES` | `0` | 처리 상한(테스트) |
| `METRICS` | `0` | 계측 기록 |
| `EMBED_MODEL` | `nlpai-lab/KURE-v1` | RAG 임베딩 |
| `RAG_SOURCE_DIR` | `refined_data` | 인덱싱 대상 |
| `DEDUP_THRESHOLD` | `0.88` | 중복 클러스터 임계 |
| `WHISPER_MODEL` | `large-v3` | STT 모델 |
| `MAX_TRANSCRIBE_MINUTES` | `30` | 전사 길이 상한 |
| `GEMINI_API_KEY` | (없음) | Gemini 키(env 전용) |
| `TELEGRAM_BOT_TOKEN`/`TELEGRAM_ALLOWED_IDS` | (없음) | 봇 토큰·허용 ID |

---

## 8. 현재 데이터 현황 (실측)

| 구분 | 수량 |
| --- | --- |
| raw_inputs 전체 | **102건** |
| └ ai_portrait_ | 50 |
| └ sports_ | 50 |
| └ humor_ | **5** (에이전트 크롤 실행으로 갱신) |
| └ yt_ (전사) | 1 |
| └ voice_ | 0 |
| refined_data(요약 캐시) | 103 |
| images(로컬 이미지) | 100 |
| ChromaDB 인덱스 | 102 |

---

## 9. 성능 · 품질 베이스라인 (실측, DEV-05/06)

**성능(OPTIMIZATION_BASELINE.md v2, 계측 오버헤드 교정 후):**
| 상태 | 총 소요 중앙값 | 편차 | 지배 단계 |
| --- | ---: | ---: | --- |
| 웜(캐시 적중) | **32.3s** | 3.5s | 브리핑(qwen 콜드로드+추론 ~27s) |
| 콜드(캐시 비움) | **179.9s** | 3.2s | 요약(EXAONE ×102, 건당 1.39s) |
- 콜드 요약 prompt_tokens: p50=175, p95=280, max=1366. num_ctx 하향 실험 → **개선 없음(원복)**.

**품질(QUALITY_BASELINE.md):**
| 지표 | 값 |
| --- | --- |
| 요약 스키마 통과율 | 19/20 (95%) |
| easy hit@3 | 9/9 |
| hard hit@3 / hit@5 | 6/6 / 6/6 |
| 네거티브 골드 | ✅ 전부 통과(Winter Snow/KBO/배구외 금지 구간 밖) |
| H1 top-1 점수(추이) | 0.435 |

---

## 10. 구현 상태 매트릭스

| 영역 | 상태 |
| --- | --- |
| 크롤링 3종 + STT 전사 | ✅ 가동 |
| EXAONE 구조화 요약 + 캐시 | ✅ |
| qwen 브리핑 + 단계경계 언로드 | ✅ |
| 멀티소스 HTML/MD 리포트 | ✅ |
| KURE-v1 + ChromaDB RAG + 중복제거 | ✅ |
| Streamlit 대시보드(아카이브 질의 포함) | ✅ |
| 계측(metrics.sqlite, 실측 토큰) | ✅ |
| A/B·bench·품질/성능 베이스라인 | ✅ |
| Telegram 에이전트 (DEV-03 Phase 2) | ✅ **가동 검증**(읽기툴·쓰기툴 확인버튼·언어·STT) |
| Gemini 무료 API | 🔶 코드 완료, **API 키 대기** |
| 브리핑 모델 확정(3파전) | 🔶 채점 요청서 생성, **브릿지 회수 대기** |
| 프롬프트 다이어트 | 🔶 요청서 생성, **회수 후 판정** |
| Whisper GPU 복구 (DEV-03 Phase 1.0) | ✅ 복구(cublas/cudnn 휠, CPU 대비 9.1배) |
| STT 파이프라인 (DEV-03 Phase 1) | ✅ 가동 (VAD 30분 육안검수만 잔여) |
| 소스 레지스트리(sources.yaml)·RSS·범용추출 | 🚧 PRD 설계만(미구현) |
| 아카이브·시계열 브리핑 | 🚧 미구현(RAG는 refined_data 인덱싱으로 대체 중) |
| 스케줄러·알림 | 🚧 미구현 |
| 분류·태깅 단계·reasoning 흡수 | 🚧 미구현 |
| 개인문서 RAG (DEV-03 Phase 3) | 🔶 모듈 완료(`personal_rag.py`)+대시보드 통합. PDF 샘플·파서비교 게이트 |
| TTS **금일 작업요약** (DEV-03 Phase 4) | ✅ 파이프라인 편입(`TTS_SEND=1`) — 작업요약 음성 텔레그램 전송 **검증**. edge-tts. (MeloTTS 3안은 선택) |
| VLM 이미지 캡션 (DEV-03 Phase 5) | ✅ 파이프라인 편입·**검증**(전체 실행: 69건 캡션 주입, nsfw 제외, s1+vlm 캐시 분리, RAG 동기화). OCR 육안검수 게이트 |

---

## 11. 파일 인벤토리

**실행 배치:** `0_크롤러실행` `1_서버실행_LiteLLM`(동결) `2_에이전트실행_Interpreter`(동결) `3_대시보드실행` `4_하이브리드_파이프라인실행` `5_뷰어서버실행`

**핵심 코드:** pipeline_orchestrator · crawl_{humor,youtube_sports,ai_portraits} · transcribe_youtube · rag · app · agent_tools · telegram_agent · gemini_client · gpu_lock · metrics

**분석/실험:** ab_summary · bench_briefing · baseline_run · numctx_experiment · prompt_diet · quality_baseline · rag_eval · vram_audit

**설정:** config.yaml(트랙 B) · prompts/(프롬프트 버전관리)

**문서:** [MANUAL](MANUAL.md) · [PROJECT_GUIDE](PROJECT_GUIDE.md) · [PRD_결정사항_v3](PRD_결정사항_v3.md) · [PRD_본문_v3](PRD_본문_v3.md) · [VRAM_AUDIT](VRAM_AUDIT.md) · [OPTIMIZATION_BASELINE](OPTIMIZATION_BASELINE.md) · [QUALITY_BASELINE](QUALITY_BASELINE.md) · [PARTIAL_OPT_REPORT](PARTIAL_OPT_REPORT.md) · [DEFERRED_ITEMS](DEFERRED_ITEMS.md) · SYSTEM_STATE(본 문서)

---

## 12. 플랜 수립 시 유의점 (요약)

1. **VRAM 여유 692MB**가 qwen 경로의 병목 — 부하 추가 전 필독(§2). EXAONE↔qwen 순차 로드 불변.
2. **웜 32s의 대부분이 qwen 콜드로드** — 에이전트 상시 응답을 원하면 "세션 중 keep_alive 유지"가 관건([`DEFERRED_ITEMS.md`](DEFERRED_ITEMS.md), DEV-04 재개 시).
3. **콜드 병목은 요약(102건×1.39s)** — 대량 유입 시 병렬화(보류)가 후보이나 VRAM 제약.
4. **humor 데이터 1건** — 커버리지 확대하려면 crawl_humor 재실행 + 소스 다변화(sources.yaml 미구현).
5. **Whisper GPU 복구**가 STT 처리량·Phase 2 음성명령 실시간성의 분기점.
6. 미구현 대형 항목(소스 레지스트리/아카이브/시계열/스케줄러/분류/VLM/TTS)은 PRD_본문_v3에 설계 존재 — 우선순위만 정하면 착수 가능.
