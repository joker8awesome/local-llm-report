# PRD 본문 — 하이브리드 파이프라인 v3.0

- 문서번호: PRD-2026-0821-BODY
- 상위문서: [`PRD_결정사항_v3.md`](PRD_결정사항_v3.md) (결재일 2026-08-20)
- 기준 코드: v2.2.0 ([`MANUAL.md`](MANUAL.md) / [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md))
- 작성일: 2026-08-21
- 상태: 초안 (Draft)

---

## 1. 개요 (Overview)

### 1.1 배경
현재 시스템(v2.2.0)은 로컬 PC에서 **크롤링 → 로컬 LLM 요약/브리핑 → 리포트(HTML/MD)**를 수행하는 단일 실행형 파이프라인이다. 세 종의 크롤러, 콘텐츠 해시 캐시, 이미지 로컬 다운로더, Streamlit 대시보드를 갖췄으나 다음 한계가 있다.

- 수집 소스가 코드에 하드코딩되어 확장이 어렵다.
- 매 실행이 이전 결과를 덮어써 **이력·추세**가 없다.
- 실행이 수동이며 **자동화·알림**이 없다.
- 로컬 LLM 역할이 요약/브리핑에 국한된다.
- 상위 LLM("클라우드 브레인")과의 협업 경로가 없다.

v3.0은 이 한계를 해소해 **확장 가능하고 자동화된 하이브리드(로컬 LLM + 클라우드 브레인) 파이프라인**으로 발전시킨다.

### 1.2 목표
- **G1.** 소스를 레지스트리(`sources.yaml`)로 관리하고 RSS/범용 추출로 확장한다. (제3조)
- **G2.** 실행 결과를 아카이브하고 **시계열 브리핑**을 제공한다. (제4조)
- **G3.** 크롤링→파이프라인을 **스케줄 실행**하고 결과를 **알림**한다. (제5조)
- **G4.** 로컬 LLM 역할을 **분류·태깅**까지 확장하고 reasoning 모델을 흡수한다. (제6조)
- **G5.** **클라우드 브레인**에 계획·코드생성·프롬프트최적화·소스발굴·품질검수를 위임하는 **프롬프트 브릿지**를 둔다. (제1·2조)
- **G6.** 브리핑/요약 **품질 검수 루프**를 도입한다. (제2·8조)

### 1.3 범위 (In / Out)
| 구분 | 내용 |
|---|---|
| **In-scope** | 소스 레지스트리·범용 수집, 아카이브·시계열, 스케줄·알림, 분류·태깅·reasoning, 클라우드 브레인 브릿지, 품질 검수 루프 |
| **Out-of-scope** | 트랙 B(대화형 에이전트) 신규 개발 — **동결**(§7). 클라우드 브레인 **API 유료 연동**(제1조에서 브라우저 자동화로 결정). 멀티 사용자/웹 배포. |

### 1.4 결정사항 요약 (상위문서 매핑)
| 조항 | 결정 | 본 문서 섹션 | 릴리스 우선순위(제8조) |
|---|---|---|---|
| 제1조 | 클라우드 브레인 = 브라우저 자동화 | §2 | P0 |
| 제2조 | 브레인 위임 5종 | §2, §8 | P0/P2 |
| 제3조 | 소스 레지스트리·RSS·범용추출 | §3 | P0 |
| 제4조 | 아카이브 + 시계열 브리핑 | §4 | P0/P1 |
| 제5조 | 스케줄 + 알림 | §5 | P1 |
| 제6조 | 요약+브리핑+분류·태깅, reasoning 흡수 | §6 | P2 |
| 제7조 | 트랙 B 동결 | §7 | — |

### 1.5 용어
- **클라우드 브레인:** claude.ai 등 상위 LLM(브라우저 자동화로 연동).
- **로컬 LLM:** Ollama 모델(hermes3:8b, qwen2.5:14b 등).
- **프롬프트 브릿지:** 로컬↔브레인 간 파일 기반 비동기 요청/응답 규약.
- **스냅샷:** 1회 실행의 수집·요약·브리핑 결과 묶음(아카이브 단위).
- **아이템:** 개별 수집 콘텐츠 1건(원문 URL + 콘텐츠 해시로 식별).

---

## 2. 클라우드 브레인 연동 & 프롬프트 브릿지 (Cloud Brain Bridge)

> **결정 근거:** PRD 결정사항 v3.0 제1조(연동 방식 = **브라우저 자동화**, API 아님·비권장이나 확정) / 제2조(위임 작업 5종) / 제8조(P0: 프롬프트 브릿지 폴더 규약).
> **현재 코드 상태(v2.2.0):** 로컬 파이프라인(`pipeline_orchestrator.py`)은 Ollama 로컬 모델만 사용하며, 클라우드 브레인 연동·브릿지 계층은 **미구현**이다. 본 섹션은 v3.0에서 신설할 계층을 정의한다.

### 2.0 개념 정의

- **클라우드 브레인(Cloud Brain):** Claude 등 상위 LLM. `claude.ai` 웹 UI를 브라우저 자동화로 조작해 접근한다.
- **프롬프트 브릿지(Prompt Bridge):** 로컬 파이프라인과 브라우저 자동화 워커 사이의 **파일 기반 비동기 핸드오프 계층**. 로컬은 요청 파일을 남기고, 브라우저 자동화 워커가 이를 브레인에 주입·수집하여 응답 파일로 되돌린다. 양측은 서로의 실행 시점에 의존하지 않는다(비동기).
- **위임 작업(제2조):** ① 수집 계획 수립 ② 크롤러 코드 생성·수리 ③ 로컬용 프롬프트 최적화 ④ 트렌드·실시간 소스 발굴 ⑤ 브리핑 품질 검수.

---

### 2.1 기능 요구사항 (Functional Requirements)

#### FR-1: 브라우저 자동화 연동 (제1조)

| ID | 요구사항 | 설명 | 수용 기준 |
|---|---|---|---|
| **FR-1.1** | 브라우저 세션/로그인 | `claude.ai` 로그인 세션을 확보·유지한다(쿠키/프로필 재사용). | 워커 기동 시 로그인 상태를 감지하고, 미로그인 시 사람 개입 지점으로 전환한다. 재기동 후에도 세션이 유지되면 재로그인 없이 진행. |
| **FR-1.2** | 요청 텍스트 주입 | 브릿지 요청 파일의 `payload`를 프롬프트로 조립해 대화창에 입력·전송한다. | 요청 1건당 새 대화(또는 지정 대화)에 프롬프트가 온전히 입력되고 전송된다. 입력 유실·잘림이 없다. |
| **FR-1.3** | 응답 수집 | 브레인의 답변(텍스트·코드블록)을 완결 시점까지 수집한다. | 스트리밍 완료를 감지한 뒤 전체 응답을 추출하고, 코드블록은 언어·파일 힌트와 함께 `artifacts`로 분리 저장한다. |
| **FR-1.4** | 실패/타임아웃 폴백 | 응답 지연·차단·오류 시 재시도 후 실패 처리한다. | 타임아웃(기본 5분) 초과 시 지정 횟수 재시도, 최종 실패는 응답 파일 `status=error`로 기록(무음 실패 금지). |
| **FR-1.5** | 사람 개입 지점 | 로그인·CAPTCHA·이상 UI를 사람에게 위임한다. | 자동 진행 불가 상황을 감지하면 해당 요청을 `needs_human`으로 표시하고 알림을 남긴 뒤 대기(파이프라인 전체를 막지 않음). |

#### FR-2: 위임 작업 5종 (제2조)

| ID | 위임 작업 | 설명 | 수용 기준 |
|---|---|---|---|
| **FR-2.1** | 수집 계획 수립 (`plan`) | 구독 주제·기존 소스를 근거로 무엇을·어디서·어떤 주기로 수집할지 계획을 요청한다. | 응답이 소스 후보·수집 주기·우선순위를 구조화(JSON/표)해 반환하고, `sources.yaml`(제3조)에 반영 가능한 형태를 갖춘다. |
| **FR-2.2** | 크롤러 코드 생성·수리 (`crawler_gen`) | 신규 소스용 크롤러 초안 또는 깨진 크롤러의 수정본을 요청한다. | 기존 크롤러 규약(소스 prefix, `raw_inputs\*.txt` 공통 스키마)을 지킨 Python 코드를 `artifacts`로 반환한다. **자동 실행 금지** — 반드시 §2.4 검증 게이트를 통과해야 한다. |
| **FR-2.3** | 로컬용 프롬프트 최적화 (`prompt_opt`) | 로컬 모델(`hermes3:8b` 요약 / `qwen2.5:14b` 브리핑)용 요약·브리핑 프롬프트 개선을 요청한다. | 대상 모델·용도를 명시한 프롬프트 텍스트를 반환한다. reasoning 모델(`qwen3.5:9b`)을 브리핑에 쓰지 않는 현행 제약과 모순되지 않는다. |
| **FR-2.4** | 트렌드·실시간 소스 발굴 (`source_discovery`) | 구독 주제의 최신 트렌드·실시간 소스(RSS/피드 우선)를 발굴 요청한다. | 소스명·URL·피드 유형·신뢰도 메모를 포함한 후보 목록을 반환한다. RSS/피드가 있으면 우선 표기(제3조 정책 정합). |
| **FR-2.5** | 브리핑 품질 검수 (`briefing_qa`) | 로컬이 생성한 `FINAL_ACTION_REPORT.md` 브리핑의 사실성·누락·논조를 검수 요청한다. | 지적 사항·수정 제안을 구조화해 반환한다. 검수 결과는 리포트를 **자동 덮어쓰지 않고** 별도 제안으로 축적된다. |

---

### 2.2 프롬프트 브릿지 폴더 규약 (P0, 파일 기반 비동기 핸드오프)

로컬 파이프라인과 브라우저 자동화 워커는 **파일시스템만을 공유 채널로** 사용한다. 프로세스 간 직접 호출·소켓·API를 두지 않으므로 어느 한쪽이 꺼져 있어도 요청/응답이 유실되지 않는다.

#### 2.2.1 디렉터리 구조

기존 `workspaces\` 규약과 나란히 프로젝트 루트에 `bridge\`를 신설한다.

```text
D:\로컬LLM\
 └── bridge\
      ├── requests\      # 로컬이 생성한 요청 파일 (pending 상태로 진입)
      ├── responses\     # 워커가 되돌린 응답 파일 (done/error)
      ├── processing\    # 워커가 처리 중 점유한 요청 (in_progress 잠금)
      ├── artifacts\     # 브레인이 생성한 산출물(코드/설정) 원본 보관
      │    └── <request_id>\   # 요청별 하위 폴더 (예: crawler_xxx.py, prompt_xxx.txt)
      └── archive\       # 완료·실패 후 이동된 요청/응답 이력 (감사·재현용)
```

- **파일명 규약:** `<created_at 압축>__<task_type>__<request_id>.json`
  예) `20260821T1430__crawler_gen__req-8f3a1c.json`
- `request_id`는 전역 고유(UUID 권장). 요청·응답·아카이브·artifacts 하위폴더가 동일 `request_id`로 연결된다.

#### 2.2.2 요청 파일 스키마 (`bridge\requests\*.json`)

```json
{
  "request_id": "req-8f3a1c",
  "task_type": "crawler_gen",
  "payload": {
    "goal": "루리웹 인기글 신규 크롤러 초안 생성",
    "context": "raw_inputs .txt 공통 스키마 준수, prefix='ruli_'",
    "inputs": ["기존 crawl_humor.py 규약 요약", "대상 URL 패턴"]
  },
  "created_at": "2026-08-21T14:30:00+09:00",
  "status": "pending",
  "meta": {
    "priority": "P1",
    "timeout_sec": 300,
    "max_retries": 2
  }
}
```

- `payload`는 task_type별 자유 구조이되, 브라우저 자동화가 그대로 프롬프트로 조립할 수 있도록 `goal`·`context`를 필수로 둔다.
- 로컬 파이프라인은 요청 생성 후 곧바로 후속 로컬 작업을 이어갈 수 있다(응답을 블로킹 대기하지 않음).

#### 2.2.3 응답 파일 스키마 (`bridge\responses\*.json`)

```json
{
  "request_id": "req-8f3a1c",
  "result": "요청하신 크롤러 초안입니다. raw_inputs 스키마를 준수했습니다. …",
  "artifacts": [
    { "type": "crawler_code", "path": "bridge/artifacts/req-8f3a1c/crawl_ruliweb.py" },
    { "type": "note",         "path": "bridge/artifacts/req-8f3a1c/README.txt" }
  ],
  "status": "done",
  "error": null,
  "review": { "gate": "pending" },
  "completed_at": "2026-08-21T14:36:12+09:00"
}
```

- `artifacts`의 `path`는 **항상 `bridge\artifacts\<request_id>\` 하위 상대경로**로 기록한다. 코드/설정은 응답 본문(`result`)이 아니라 파일로 분리해 검증 게이트가 파일 단위로 다루게 한다.
- `result`는 사람이 읽는 요약, `artifacts`는 기계가 처리할 산출물로 역할을 분리한다.

#### 2.2.4 상태 전이 & 파일 이동 규칙

```text
[로컬]  요청 생성 ─▶ requests\  (status=pending)
                         │
[워커]  점유(잠금) ─────▶ processing\  (status=in_progress)   ← 원자적 이동으로 중복 처리 방지
                         │
                 ┌───────┴───────┐
          성공   ▼               ▼   실패/타임아웃(재시도 소진)
   responses\ (status=done)   responses\ (status=error)
   artifacts\<id>\ 산출물 저장
                 │
[로컬]  응답 소비·검증(§2.4) 후
                 ▼
            archive\  (요청+응답 원본 이력 보존)
```

| 전이 | 트리거 | 파일 이동 |
|---|---|---|
| `pending → in_progress` | 워커가 요청을 집어 처리 시작 | `requests\` → `processing\` (rename = 잠금) |
| `in_progress → done` | 응답 수집 성공 | 응답을 `responses\`에 기록, artifacts 저장, 요청은 `processing\`에서 제거 |
| `in_progress → error` | 타임아웃·차단·재시도 소진 | 응답을 `responses\`에 `error`로 기록(`error` 사유 포함) |
| `in_progress → needs_human` | 로그인/CAPTCHA/이상 UI (FR-1.5) | 요청을 `processing\`에 둔 채 알림, 사람 개입 후 재개 |
| `done/error → archived` | 로컬이 응답을 소비·검증 완료 | 요청·응답 원본을 `archive\`로 이동 |

- **원자성:** 요청 점유는 파일 rename(`requests\` → `processing\`)으로 수행해 다수 워커/재기동 시 중복 처리를 막는다.
- **멱등성:** 이미 `processing\` 또는 `responses\`에 동일 `request_id`가 있으면 재생성하지 않는다.
- **무음 실패 금지:** 모든 실패는 반드시 `status=error` 응답 파일을 남긴다(현행 파이프라인의 폴백·실패 명시 철학과 일치).

---

### 2.3 브라우저 자동화 요구사항 & 리스크

#### 2.3.1 동작 요구사항

| 항목 | 요구사항 |
|---|---|
| 세션/로그인 | 전용 브라우저 프로필로 `claude.ai` 로그인 세션을 재사용. 만료 시 FR-1.5의 사람 개입 지점으로 전환. |
| 요청 주입 | `payload`를 프롬프트로 조립 → 대화창 입력 → 전송. 긴 프롬프트는 잘림 없이 전량 입력. |
| 응답 수집 | 스트리밍 **완결 감지** 후 전체 텍스트 추출, 코드블록 분리. 부분 응답을 완결로 오인하지 않음. |
| 실패/타임아웃 | `timeout_sec`(기본 300) 초과 시 `max_retries`만큼 재시도, 최종 실패는 `error`. |
| 사람 개입 | 로그인·CAPTCHA·레이트리밋·UI 변경 감지 시 자동 진행 중단·알림·대기(전체 파이프라인 비차단). |
| 속도 조절 | 요청 간 지연·동시성 1을 기본으로 하여 과도한 자동 조작을 억제. |

#### 2.3.2 리스크 & 완화책

| 리스크 | 영향 | 완화책 |
|---|---|---|
| **약관/정책 위반 소지** (웹 UI 자동 조작) | 계정 제재·차단 | 저빈도·저동시성 운영, 사람 개입 지점 상시 확보, API 전환을 향후 대안으로 명시(제1조는 브라우저 자동화 확정이나 재검토 여지 기록). |
| **UI 변경으로 인한 파손** | 주입/수집 실패 급증 | 셀렉터·완결 감지를 한 곳에 모듈화, 실패 시 `error`로 폴백해 로컬 파이프라인은 계속 진행. |
| **세션 만료·로그인 요구** | 자동화 중단 | 세션 지속(프로필 재사용), 만료 감지 → `needs_human` 전환·알림. |
| **CAPTCHA/봇 탐지** | 요청 차단 | 자동 우회 시도 금지, 즉시 사람 개입 위임(우회는 리스크·정책상 배제). |
| **레이트리밋·응답 지연** | 타임아웃 | 재시도·백오프, 큐 적체 시 우선순위(`meta.priority`) 기반 처리. |
| **응답 신뢰성(환각·오류 코드)** | 잘못된 산출물 반영 | §2.4 검증 게이트로 **자동 실행 차단** — 사람/자동 검토 통과 전 반영 금지. |

---

### 2.4 위임 결과의 안전 반영 (Verification Gate)

브레인이 생성한 **크롤러 코드·프롬프트·설정은 자동으로 실행·적용되지 않는다.** 모든 산출물(`artifacts`)은 다음 게이트를 통과해야 파이프라인에 반영된다.

```text
responses\ + artifacts\  ─▶  [검증 게이트]  ─▶  승인 시에만 프로젝트에 반영
                              review.gate:
                                pending → approved → 반영
                                        → rejected → 아카이브(반영 안 함)
```

| 대상 | 게이트 검사 | 반영 조건 |
|---|---|---|
| **크롤러 코드** (`crawler_gen`) | ① 정적 검토(위험 호출·파일 삭제 범위·prefix 준수 확인) ② `raw_inputs\*.txt` 공통 스키마 준수 ③ **격리 시험 실행**(제한 건수, 임시 작업폴더) ④ 사람 승인 | 4단계 통과 후에만 프로젝트 크롤러로 채택. 특히 **크롤러의 `.txt` 삭제 로직은 자기 prefix 한정**인지 반드시 확인(현행 소스 공존 규약 위반 방지). |
| **프롬프트** (`prompt_opt`) | 대상 모델·용도 확인, 샘플 입력으로 로컬 모델 결과 비교. reasoning 모델을 브리핑에 배정하지 않았는지 확인. | 기존 대비 품질 저하가 없을 때만 채택. |
| **수집 계획/소스** (`plan`, `source_discovery`) | URL 유효성·피드 유형·중복 확인 | 검토 후 `sources.yaml`(제3조)에 수동/확인 반영. |
| **브리핑 검수** (`briefing_qa`) | 제안을 리포트에 자동 덮어쓰지 않음 | 별도 제안으로 축적, 사람이 선택 반영. |

- **원칙:** 브릿지는 **제안 채널**이지 **실행 채널**이 아니다. `review.gate=approved` 이전에는 어떤 산출물도 `crawl_*.py`·프롬프트·`sources.yaml`을 변경하지 않는다.

---

### 2.5 선행/후행 의존성

- **선행:** Ollama 로컬 파이프라인(코드 v2.2.0)이 정상 동작해야 하며, 브레인 접속용 브라우저 프로필과 `bridge\` 폴더 구조가 준비되어야 한다.
- **후행:** 본 브릿지의 산출물은 제3조(소스 레지스트리 `sources.yaml`·주제 구독)와 제8조 후속 항목(스케줄러·시계열 브리핑·품질 검수 루프)이 소비한다.

---

## 3. 소스·주제 확장 (Source Registry & Universal Ingestion)

본 조는 결정사항 제3조에 따라, 현재 하드코딩된 3종 크롤러(`crawl_ai_portraits` / `crawl_youtube_sports` / `crawl_humor`)를 **선언형 소스 레지스트리(`sources.yaml`)** 기반의 범용 수집 구조로 전환하기 위한 요구사항과 데이터 스키마를 정의한다. 목표는 "코드 수정 없이 YAML 항목 추가만으로 새 소스를 편입"하는 것이며, 기존 `pipeline_orchestrator.py`(요약·브리핑·리포트·캐시)는 **무변경 재사용**을 원칙으로 한다. 우선순위는 제8조 기준 **P0**이다.

### 3.1 기능 요구사항 (FR-3.x)

| FR | 요구사항 | 설명 | 수용기준 (Acceptance) |
|---|---|---|---|
| **FR-3.1** | 소스 레지스트리(`sources.yaml`) | 모든 수집 소스를 단일 YAML 파일에 선언(§3.2 스키마). 러너(`ingest_runner.py` 신규)가 파싱하여 `enabled: true`인 항목만 수집. | 유효한 `sources.yaml`에 항목 1개를 추가하고 러너를 실행하면 **코드 변경 없이** 해당 소스의 `raw_inputs\<prefix>_*.txt`가 생성된다. `enabled: false`는 스킵된다. 스키마 위반 항목은 오류로 집계되고 나머지 소스 수집은 계속된다. |
| **FR-3.2** | 주제 구독 + 브레인 소스 발굴 | 사용자는 관심 `topic`을 등록하고, 클라우드 브레인(제1조=브라우저 자동화, 제2조=소스 발굴 위임)이 해당 주제의 후보 소스를 **`sources.yaml` 엔트리 초안 형태**로 제안한다. 자동 반영이 아니라 **사람 검토 후 머지**한다. | 브레인이 산출한 후보가 스키마에 맞는 YAML 블록으로 프롬프트 브릿지 폴더(제8조 P0)에 떨어지고, 사람이 검토·병합하면 다음 러너 실행에서 정상 수집된다. 브레인 산출물이 그대로 프로덕션 소스를 오염시키지 않는다(검토 게이트 존재). |
| **FR-3.3** | RSS/피드 우선 수집 | `type: rss` 소스는 HTML 파싱보다 우선하여 피드 파서로 항목을 획득한다. 신규 의존성 **`feedparser`** 도입(현행 패키지 목록에 없음, §3.3). | `type: rss` 소스 실행 시 피드의 각 엔트리(제목·링크·요약/본문·발행일)를 파싱해 개별 `.txt`로 저장한다. 피드 획득 실패 시 해당 소스는 실패로 집계되되 러너 전체는 중단되지 않는다. |
| **FR-3.4** | 범용 본문 추출기 | `type: html` 소스는 (a) 지정 `selector` 우선(기존 `crawl_humor` 방식), (b) selector 미지정·미매치 시 **본문 자동추출 폴백**(신규 의존성, §3.3)을 적용한다. RSS 본문 부족 시에도 원문 링크에 폴백 추출 적용 가능. | `selector`가 매치되면 그 영역을 본문으로 저장한다. 미매치 시 폴백 추출기가 본문을 채운다. **폴백까지 실패해도 `.txt` 파일은 생성**되며(`[본문 전문]`이 비어도 가능) 실패 건수가 리포트 헤더에 집계된다(무음 실패 금지 — 기존 폴백 철학 계승). |
| **FR-3.5** | 기존 3종 크롤러 레지스트리 이관 | 현행 3종 크롤러를 레지스트리 엔트리로 이관한다(§3.4 매핑 표). 이관 후에도 **소스별 prefix 삭제 계약**(자기 `<prefix>_*.txt`만 삭제, 타 소스 보존 — v2.2.0 구현)을 유지한다. | 이관된 소스를 순차 실행해도 서로의 `raw_inputs` 데이터를 덮어쓰지 않는다. `pipeline_orchestrator.py`는 수정 없이 이관된 소스의 산출물을 요약·브리핑·렌더링한다. |
| **FR-3.6** | raw_inputs `.txt` 공통 스키마 준수 | 모든 소스(기존·신규)는 §3.5의 공통 `.txt` 스키마로 저장한다. | 새 소스의 출력물이 파이프라인의 파서·해시 캐시(`SRC-HASH`)·소스별 카드 렌더러와 호환된다(§3.5 수용조건 참조). |

### 3.2 데이터 스키마 — `sources.yaml`

파일 위치: `D:\로컬LLM\sources.yaml` (러너가 읽는 단일 레지스트리)

```yaml
# sources.yaml — 소스 레지스트리 (v3.0)
version: 1

sources:
  # ── RSS 소스 예시 ───────────────────────────────
  - id: hankyung_it
    name: 한국경제 IT/과학
    type: rss                      # rss | html | api
    url: https://www.hankyung.com/feed/it
    enabled: true
    topic: tech_kr                 # 주제 구독 키(브레인 발굴/시계열 브리핑 그룹)
    prefix: hankyung_it_           # raw_inputs 파일 prefix (고유·소문자·'_'로 종료)
    limit: 15                      # 수집 항목 상한
    extract:
      fulltext: fallback           # feed | fallback | link
      # feed=피드 본문 사용, link=원문 링크에서 폴백추출, fallback=피드 부족 시 폴백
    schedule: "0 */6 * * *"        # 스케줄 힌트(P1 스케줄러가 소비, 본 조 범위 밖)
    render_hint: article           # HTML 리포트 카드 유형 힌트(§3.5 후행 의존)

  # ── HTML 소스 예시 (기존 crawl_humor 이관형) ──────
  - id: ruliweb_humor
    name: 루리웹 유머 베스트
    type: html
    url: https://m.ruliweb.com/best/humor/now
    enabled: true
    topic: community_kr
    prefix: humor_                 # 기존 prefix 유지(하위호환)
    limit: 5
    list_selector: ".list_item .subject a"   # 목록 링크 selector
    extract:
      # 본문 영역 selector 후보(순차 폴백) — crawl_humor 방식 계승
      content_selector:
        - .view_content
        - .article_content
        - "#article_content"
        - .board_main
      fulltext: fallback           # selector 미매치 시 본문 자동추출로 폴백
      keep_media: true             # <img>/<video>/<iframe> 태그 보존 → [미디어영역]
    headers:
      User-Agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) ... Safari/605.1.15"
      Accept-Language: "ko-KR,ko;q=0.9"
    schedule: "0 8,20 * * *"
    render_hint: humor
```

**필드 설명**

| 필드 | 필수 | 타입 | 설명 |
|---|---|---|---|
| `id` | ✅ | string | 소스 고유 식별자(영문·`_`). 시계열 브리핑·아카이브의 안정 키(제4조 후행 의존). |
| `name` | ✅ | string | 사람이 읽는 표시명(리포트 카드 헤더). |
| `type` | ✅ | enum | `rss` \| `html` \| `api`. 수집 전략 분기. (deterministic 스톡 생성기는 §3.4 참조 — 본 3종에는 미포함.) |
| `url` | ✅ | string | RSS 피드 URL / HTML 목록 URL / API 엔드포인트. |
| `enabled` | ✅ | bool | `false`면 러너가 스킵. |
| `topic` | ✅ | string | 주제 구독 키. 브레인 소스 발굴(FR-3.2)·시계열 브리핑 그룹핑 기준. |
| `prefix` | ✅ | string | `raw_inputs` 파일 접두사. **고유**하며 `[a-z0-9_]`만 허용, 반드시 `_`로 종료. 소스별 삭제 계약·`SRC-HASH` 캐시·카드 렌더러의 조인 키이므로 중복 금지. |
| `limit` | | int | 수집 항목 상한(기본값은 러너 정의). |
| `list_selector` | html | string | (html 전용) 목록 페이지에서 상세 링크를 뽑는 CSS selector. |
| `extract.fulltext` | | enum | `feed`(피드 본문) \| `link`(원문 링크 폴백추출) \| `fallback`(우선 시도 후 부족 시 폴백). |
| `extract.content_selector` | html | list | (html 전용) 본문 영역 selector **후보 리스트**(순차 폴백). `crawl_humor`의 `select_one` 체인과 동형. |
| `extract.keep_media` | | bool | 본문 내 `<img>/<video>/<iframe>` 태그 보존 여부 → `[미디어영역]` 반영. |
| `headers` | | map | 요청 헤더(User-Agent 등). WAF/차단 회피용. |
| `schedule` | | string(cron) | **스케줄 힌트**. 본 조는 파싱·보존만 하며 실제 실행은 P1 스케줄러(제5·8조)가 소비. |
| `render_hint` | | string | HTML 리포트 카드 유형 힌트(`article`/`humor`/`gallery`/`video` 등). 신규 소스의 렌더링 경로 결정(§3.5 후행 의존). |

### 3.3 범용 본문 추출기 요구사항

수집 전략은 소스 `type`에 따라 분기하며, 다음 계층을 따른다.

1. **RSS (`type: rss`) — 피드 파서 우선.** `feedparser` 계열로 피드 엔트리를 순회한다(제목/링크/summary·content/발행일). 피드에 본문이 충분하면 그대로 사용(`fulltext: feed`), 부족하면 원문 링크에 폴백 추출을 적용(`fulltext: fallback`/`link`).
2. **HTML (`type: html`) — selector 우선 + 폴백.** `list_selector`로 상세 링크 목록을 얻고, 각 상세 페이지에서 `content_selector` 후보를 **순차 시도**(기존 `crawl_humor.extract_full_content_and_media`의 `select_one` 폴백 체인과 동일 철학). 매치 영역이 없으면 **본문 자동추출 폴백**으로 넘어간다. `keep_media: true`면 본문 내 미디어 태그를 정규화(`//` → `https:`, 상대경로 절대화)하여 `[미디어영역]`에 보존한다.
3. **폴백 본문 자동추출 (신규 의존성).** selector·피드가 모두 실패한 경우를 위한 범용 추출기. 도입 후보는 **`trafilatura`**(1순위) 또는 `readability-lxml`. 본 조에서 **하나를 신규 의존성으로 채택**한다.

> **신규 의존성 명시:** 현행 패키지 목록(`requests`, `beautifulsoup4`, `openai`, `streamlit`, `litellm`, `open-interpreter`)에는 **RSS·폴백 추출기가 없다.** 본 조 도입으로 `feedparser`와 `trafilatura`(또는 `readability-lxml`)를 **신규 추가 의존성**으로 등록한다.

> **폴백 철학 계승(무음 실패 금지):** 추출이 끝까지 실패해도 `.txt` 파일은 **반드시 생성**하되 `[본문 전문]`을 비우고, 실패를 러너 카운터에 집계한다. 이는 기존 파이프라인이 "Ollama 오류 시 원문 발췌로 대체하고 실패 건수를 리포트 헤더에 명시"하던 방식과 일치한다.

**기존 crawl_* 3종 → 레지스트리 이관 매핑 표**

| 기존 크롤러 | 대상 | 이관 `type` | prefix | 이관 방식 / 비고 |
|---|---|---|---|---|
| `crawl_humor.py` | 루리웹 유머 본문+미디어(5건) | `html` | `humor_` | **완전 이관(레퍼런스 구현).** `list_selector` + `content_selector` 후보 체인 + `keep_media`로 그대로 표현. selector 방식의 표준 예시. |
| `crawl_youtube_sports.py` | 유튜브 스포츠 검색 임베드(~50건) | `html` (전용 유형) | `sports_` | **부분 이관.** 유튜브 검색 결과는 RSS가 아니므로 `html`로 두되, iframe 임베드 블록 생성·`[미디어영역]` 처리는 전용 어댑터 로직을 유지(범용 selector로 완전 대체 불가). |
| `crawl_ai_portraits.py` | Unsplash 스톡 50건(고정 URL·seed) | — | `ai_portrait_` | **이관 보류(전용 크롤러 유지).** `rss`/`html`/`api` 어디에도 해당하지 않는 **결정론적 데이터셋 생성기**. 고정 seed의 결정론성이 `SRC-HASH` 캐시 유효성(재크롤 후 50회 재호출 절약)의 근거이므로 억지 이관하지 않는다. 향후 `type: generated`(정적) 확장 시 편입 검토. |

### 3.4 기존 코드와의 호환 — raw_inputs `.txt` 공통 스키마

모든 소스는 아래 공통 스키마로 저장하여 `pipeline_orchestrator.py`(파서·`SRC-HASH` 캐시·소스별 카드 렌더러)가 **무변경**으로 처리하게 한다.

```text
제목: ...                 ← 필수
원문링크: https://...      ← 필수

[메타데이터]              ← 선택(소스에 메타가 있을 때만; 예: portrait/sports)
- key: value

[미디어영역]              ← 선택(이미지 URL / iframe 블록; keep_media·미디어 보유 시)
...

[본문 전문]               ← 필수(폴백 실패 시 비어 있을 수 있음)
...

[출처 URL]                ← 필수
https://...
```

- **필수 블록:** `제목:`, `원문링크:`, `[본문 전문]`, `[출처 URL]`.
- **선택 블록:** `[메타데이터]`, `[미디어영역]` — 소스가 해당 정보를 가질 때만 출력. (현행 humor는 이 두 블록이 없고, portrait/sports는 있음. 즉 **스키마는 소스별로 균일하지 않으며**, 신규 소스도 보유 정보에 맞춰 선택 블록을 생략할 수 있다.)
- **호환 수용조건:** 신규 소스의 `.txt`가 (1) 원문 SHA-256 기반 `SRC-HASH` 캐시로 정상 재사용/재요약되고, (2) `refined_data\*.md` 개별 요약과 `FINAL_ACTION_REPORT.md` 종합 브리핑에 포함되며, (3) `pipeline_orchestrator.py`를 **수정하지 않고** 처리된다. `.md` 리포트는 이미 `raw_inputs`의 **전 소스**를 커버하므로 신규 소스는 자동 반영된다.

### 3.5 선행·후행 의존

- **선행 작업:** 제3조 내부에 차단성 선행은 없다(제8조에서 아카이브와 함께 **P0**). 단, 브레인 소스 발굴(FR-3.2)은 제1조(브라우저 자동화 연동)와 제8조 프롬프트 브릿지 폴더 규약의 존재를 전제로 한다.
- **후행 작업:** (1) **HTML 리포트 렌더러 확장** — 현행 렌더러는 portrait/sports/humor 카드에 특화되어 있어, 신규 `topic`/`type` 소스는 `render_hint` 기반 **기본(범용) 카드 경로**가 추가로 필요하다(미해소 시 신규 소스가 HTML에 렌더되지 않음). (2) **P1 스케줄러**가 `schedule` 힌트를 소비하고, (3) **시계열 브리핑**(제4조)이 안정적인 `id`·`topic` 키에 의존한다.

---

## 4. 아카이브 & 시계열 브리핑 (Archive & Time-series)

> **결정 근거:** PRD 결정사항 v3.0 제4조("데이터 축적 정책 = 아카이브 + 시계열 브리핑"), 제8조(아카이브·소스 레지스트리 P0, 시계열 브리핑 P1).
> **현재 한계:** 코드 v2.2.0은 매 실행이 `final_outputs\FINAL_ACTION_REPORT.md/.html`를 **덮어씀**(이력 없음). 본 조는 이를 날짜·실행 단위로 보존하고, 축적된 스냅샷을 비교해 "어제 대비 / 지난주 대비" 변화 요약을 생성하는 것을 목표로 한다.

### 4.0 의존성 (선행/후행)

- **선행:** 제3조 **소스 레지스트리(`sources.yaml`)** 가 안정적인 `source_id`를 제공해야 스냅샷 메타의 소스 식별이 하드코딩된 3종 prefix에 묶이지 않는다(둘 다 P0).
- **후행:** 제5조 **스케줄러+알림**이 본 조가 생성한 스냅샷 diff(신규/변경/삭제 건수)를 알림 페이로드로 소비한다.

---

### 4.1 기능 요구사항 (FR-4.x)

| ID | 요구사항 | 우선순위 | 설명 | 수용 기준 |
|---|---|---|---|---|
| **FR-4.1** | 실행 결과 아카이브 저장 | P0 | 매 파이프라인 실행 시 `FINAL_ACTION_REPORT.md`와 스냅샷 메타(`manifest.json`)를 덮어쓰지 않고 실행 단위 폴더에 보존. 기존 `final_outputs\`의 "최신본"은 그대로 유지. | 1회 실행 시 `archive\YYYY-MM-DD\run_HHMMSS\`가 새로 생성되고 `manifest.json` + `report.md`가 존재. 같은 날 2회 실행해도 서로 덮어쓰지 않음. |
| **FR-4.2** | 스냅샷 버전관리(메타 기록) | P0 | 각 실행의 `run_id`, 수집시각, **소스별 수집 건수**, 사용 모델, 원문 해시 목록을 구조화 JSON으로 기록. `latest` 포인터와 일자 롤업 갱신. | `manifest.json`이 §4.2 스키마를 만족. `archive\latest.json`이 최신 `run_id`를 가리킴. 필드 누락 시 검증 실패. |
| **FR-4.3** | 아이템 중복 제거(dedup) | P0 | 스냅샷 간 아이템 동일성을 **정규화 URL(신원) + 콘텐츠 해시(변화 감지)** 로 판정하여 신규/변경/기존/삭제로 분류. | 동일 URL·동일 해시 → `기존`, 동일 URL·해시 변경 → `변경`, 신규 URL → `신규`, 직전 스냅샷엔 있었으나 이번에 없는 소스의 아이템 → `삭제`. 결정론적 소스(portrait)는 2회차부터 전량 `기존`으로 나와야 정상. |
| **FR-4.4** | 시계열 브리핑 생성 | P1 | 최근 N일 스냅샷을 입력받아 diff를 계산하고 `qwen2.5:14b`로 "변화 요약"(어제 대비/지난주 대비 트렌드)을 생성해 리포트에 주입. | `FINAL_ACTION_REPORT.md`에 "🕒 시계열 브리핑" 섹션이 추가되고, 비교 대상 스냅샷이 1개 이상일 때 신규/변경/삭제 건수와 서술 요약이 포함됨. 비교 대상이 없으면(첫 실행) 섹션에 "기준 스냅샷 없음"을 명시하고 실패하지 않음. |

**분류 주의(설계 제약):**
- **결정론적 소스(`ai_portrait_`)** 는 고정 URL·seed로 매 실행 동일 콘텐츠를 생성한다. URL+해시 dedup 하에서 2회차부터 전량 `기존`이 되어 **트렌드 delta가 구조적으로 항상 비어 있다.** 따라서 portrait는 시계열 브리핑 대상에서 **제외**하고 manifest 건수(reference-only)로만 축적한다.
- **실질 변화 소스는 `humor_`(5건, 베스트 리스트 교체)** 이다. 베스트에서 빠지는 아이템(`삭제`)이 "어제 대비"의 핵심 신호이므로 diff는 반드시 삭제 상태를 포함한다.

---

### 4.2 아카이브 저장소 스키마

#### 디렉터리 구조

```text
workspaces\
 ├── raw_inputs\            # (기존) 최신 크롤 원본
 ├── refined_data\          # (기존) 요약 캐시 .md, SRC-HASH 헤더
 ├── images\                # (기존) 콘텐츠 해시 기반 공유 이미지 풀 (아카이브가 공유)
 ├── final_outputs\         # (기존) 항상 "최신본" — 덮어쓰기 유지
 │    ├── FINAL_ACTION_REPORT.md
 │    └── FINAL_ACTION_REPORT.html
 └── archive\               # ★ 신규: 실행 이력 축적소
      ├── latest.json                       # 최신 run_id 포인터
      ├── 2026-08-21\
      │    ├── _daily.json                  # 일자 롤업(그날 run 목록·합계)
      │    ├── run_091500\
      │    │    ├── manifest.json           # 스냅샷 메타(아래 스키마)
      │    │    └── report.md               # 그 시점 FINAL_ACTION_REPORT.md 사본
      │    └── run_173000\
      │         ├── manifest.json
      │         └── report.md
      └── 2026-08-22\
           └── run_090000\ ...
```

**설계 결정(엑박 방지):** 아카이브에는 **`.md` + `manifest.json`만** 저장하고 **HTML은 복제하지 않는다.** 현재 HTML은 이미지를 `../images/<file>`(= `final_outputs\` 기준 상대경로)로 바인딩하므로, 한 단계 깊은 `archive\...\run_.../`로 그대로 복사하면 전량 엑박이 된다. 이미지는 콘텐츠 해시 기반이라 파일명이 안정적이므로 **공유 `images\` 풀에 그대로 두고**, 과거 시점 시각화가 필요하면 뷰어가 최신 HTML + 특정 `manifest.json`을 조합해 재구성한다.

**`run_id` / 시각 규칙:** 제5조 스케줄 실행은 하루 다회 발생하므로 날짜만으로는 충돌한다. `run_id = YYYYMMDD-HHMMSS`, 폴더는 `YYYY-MM-DD\run_HHMMSS\`.

#### `manifest.json` 스키마 (JSON 예시)

```json
{
  "schema_version": "1.0",
  "run_id": "20260821-091500",
  "collected_at": "2026-08-21T09:15:00+09:00",
  "models": {
    "summary": "hermes3:8b",
    "briefing": "qwen2.5:14b"
  },
  "sources": [
    {
      "source_id": "humor",
      "prefix": "humor_",
      "crawled_this_run": true,
      "collected_at": "2026-08-21T09:14:50+09:00",
      "count": 5,
      "items": [
        {
          "stem": "humor_재밌는_짤_모음",
          "title": "재밌는 짤 모음",
          "url_raw": "https://bbs.ruliweb.com/community/board/300143/read/12345678",
          "url_norm": "ruliweb.com/community/board/300143/read/12345678",
          "identity_key": "sha256:9f3a...(url_norm 해시, 아이템 신원)",
          "content_hash": "1a2b3c4d5e6f7a8b",
          "refined_ref": "refined_data/humor_재밌는_짤_모음.md",
          "summary_inline": "루리웹 베스트에 오른 유머 모음으로 ...(2~3문장)",
          "meta": null,
          "media": null
        }
      ]
    },
    {
      "source_id": "ai_portrait",
      "prefix": "ai_portrait_",
      "crawled_this_run": false,
      "collected_at": "2026-08-20T22:00:00+09:00",
      "count": 50,
      "reference_only": true,
      "items": []
    }
  ],
  "totals": { "sources": 2, "items": 55, "fallback_count": 0 }
}
```

**스키마 주의점:**
- **`crawled_this_run` (필수):** 각 크롤러는 자기 prefix만 삭제·재수집하므로, 어떤 실행의 `raw_inputs\`에는 **이번에 크롤한 소스 + 이전 잔존 소스가 혼재**한다. 이 플래그(및 소스별 `collected_at`)가 없으면 잔존 소스가 "오늘 수집된 것"으로 기록되어 시계열 diff가 왜곡된다. **diff는 양쪽 스냅샷에 모두 존재하고 `crawled_this_run=true`인 소스만 비교한다.**
- **`meta` / `media` 는 nullable:** `humor_` 원본에는 `[메타데이터]`·`[미디어영역]`이 없다(portrait/sports만 존재).
- **`content_hash`:** 현재 코드 `_content_hash()` 와 동일 규격 — **SHA-256의 앞 16 hex**(`hashlib.sha256(...).hexdigest()[:16]`). refined_data의 `SRC-HASH` 헤더와 동일 값이라 그대로 재사용.
- **`source_id`:** 하드코딩 prefix가 아니라 제3조 `sources.yaml` 레지스트리 키를 사용(선행 의존성).

#### 저장소 방식: 파일 기반 vs SQLite

| 항목 | 파일 기반 JSON(**권장**) | SQLite 옵션 |
|---|---|---|
| 외부 의존성 | **0** (표준 라이브러리 `json`) | 0 (`sqlite3` 표준 포함) 이나 스키마/마이그레이션 부담 |
| 현 아키텍처 정합성 | `.txt`/`.md` 파일 파이프라인과 동일 철학, `git`·탐색기로 직접 열람·diff 가능 | 별도 조회 도구 필요, 바이너리라 diff 불가 |
| 이력 조회 성능 | 스냅샷 수 수백 단위까지 충분(글롭+로드) | 수천~수만 아이템 누적 시 인덱스로 우세 |
| 동시성 | 실행 단위 폴더 분리로 충돌 거의 없음 | 파일 락 관리 필요 |
| 백업/이식 | 폴더 복사로 끝 | 단일 파일이라 간편하나 잠금 주의 |
| **판단** | **v3.0 1차 채택.** 의존성 0·투명성 우선, 데이터 규모(소스 3~수십·건수 소량)에 충분 | 소스가 대폭 늘어 누적 아이템이 수만 건을 넘고 집계 질의가 잦아지면 **P2 전환 옵션**으로 보류 |

---

### 4.3 아이템 동일성 판정 & 분류 규칙

**식별 원칙(2단계):** 정규화 URL = **신원(identity)**, 콘텐츠 해시 = **변화 감지기(change detector)**.

**URL 정규화 규칙:**
- 공통: scheme(`http/https`)·`www.`·트래킹 쿼리(`utm_*`, `fbclid` 등)·후행 슬래시·fragment(`#...`) 제거, 소문자 호스트.
- **유튜브(`sports_`):** 저장 원본이 iframe 임베드 블록이라 원문 해시가 노이즈에 취약하므로, `watch?v=` / `youtu.be/` / `embed/` 를 모두 **video ID** 로 수렴시켜 `youtube:<VIDEO_ID>` 를 identity로 사용.
- `identity_key` = 정규화 URL의 SHA-256(스냅샷 간 조인 키).

**분류 규칙(직전 비교 스냅샷 대비):**

| 분류 | 조건 |
|---|---|
| **신규(new)** | `identity_key`가 직전 스냅샷에 없음 |
| **변경(changed)** | `identity_key` 동일하나 `content_hash` 상이 (제목/본문 수정, 리스트 순위 변동 등) |
| **기존(unchanged)** | `identity_key` 동일 + `content_hash` 동일 |
| **삭제/이탈(removed)** | 직전 스냅샷에 있었으나(같은 소스, 양쪽 `crawled_this_run=true`) 이번 스냅샷에 `identity_key` 부재 — 예: 베스트에서 밀려남 |

> 비교는 **양쪽 스냅샷에서 실제 재크롤된 소스**로 한정한다(§4.2 `crawled_this_run`). 잔존 소스는 비교에서 제외해 유령 diff를 방지한다.

---

### 4.4 시계열 브리핑 요구사항

- **입력:** 최근 `TIMESERIES_DAYS`(기본 7)일 범위의 스냅샷들. 기준선은 (a) 직전 실행 스냅샷(어제 대비), (b) N일 전 스냅샷(지난주 대비) 2종.
- **처리:** §4.3 분류로 소스별 신규/변경/삭제 목록과 건수를 계산 → 그 diff와 각 아이템 `summary_inline`(요약)을 컨텍스트로 LLM 종합.
- **모델:** 종합 브리핑과 동일하게 **`qwen2.5:14b`**(`BRIEFING_MODEL`). ⚠️ `qwen3.5:9b`는 reasoning 모델이라 `content` 없이 사고과정만 반환 → 사용 금지(기존 제약과 동일).
- **프롬프트 개요:**
  > "다음은 어제(또는 지난주)와 오늘 수집분의 변화 데이터다. [신규 목록], [변경 목록], [사라진 목록]과 각 요약을 근거로 (1) 새로 등장한 주제·흐름, (2) 사라진 주제, (3) 지속 화제, (4) 실무 시사점을 한국어로 4~6문장 요약하라. 데이터에 없는 사실을 지어내지 말 것."
  > 결정론적 소스(portrait)는 입력에서 제외한다.
- **결과 저장 위치:** `FINAL_ACTION_REPORT.md` 상단(종합 브리핑 아래)에 **"🕒 시계열 브리핑"** 섹션을 추가하고, 동일 내용을 `archive\...\run_.../report.md` 사본에도 포함해 그 시점 상태로 보존. 비교 대상이 없으면(첫 실행) "기준 스냅샷 없음"으로 표기하고 파이프라인은 계속 진행(폴백 철학 유지).

**신규 환경변수(기존 CLI 규약 준수):**

| 변수 | 기본값 | 설명 |
|---|---|---|
| `ARCHIVE_ROOT` | `workspaces\archive` | 아카이브 저장 루트 |
| `ARCHIVE` | `1` | 아카이브 저장 on/off (`MAX_FILES`·`DOWNLOAD_IMAGES` 스타일) |
| `TIMESERIES` | `1` | 시계열 브리핑 생성 on/off |
| `TIMESERIES_DAYS` | `7` | 비교 대상 최근 스냅샷 범위(일) |

---

### 4.5 기존 `refined_data` 해시 캐시와의 관계

- **동일 해시 규격 재사용:** manifest의 `content_hash`는 코드 `_content_hash()`(SHA-256 앞 16 hex)와 **동일 값**이며, `refined_data\<stem>.md`의 `SRC-HASH` 헤더와 일치한다. 아카이브는 이 해시를 **변화 감지기로 그대로 차용**하므로 별도 해시 재계산이 없다.
- **단, refined_data는 이력 저장소가 아니다:** 캐시는 콘텐츠 해시로 키잉되어 내용이 바뀌면 **덮어써진다.** 따라서 스냅샷이 refined 파일을 **포인터(`refined_ref`)로만** 참조하면, 아이템이 변경되는 순간 과거 스냅샷의 포인터가 **깨진 참조(dangling)** 가 된다.
- **해결(채택):** 스냅샷은 요약 본문을 `manifest.json`의 **`summary_inline`으로 인라인 복사**한다(수 KB, 의존성 0, 자기완결). `refined_ref`는 최신본 추적용 참고 링크로만 유지한다. 이로써 refined_data는 **"최신 실행 가속용 캐시"** 역할을 유지하고, **과거 시점 정합성은 아카이브가 독립적으로 보장**한다.

---

## 5. 스케줄러 & 알림 (Scheduler & Notification)

> **결정 근거:** PRD 결정사항 제5조 — *자동화 수준: 스케줄 + 결과 알림* (제8조에서 P1 릴리스 범위). 현재 시스템(코드 v2.2.0)은 크롤링→파이프라인을 배치 파일(`0_`~`5_`) 또는 Streamlit 대시보드(`app.py`) 버튼으로 **수동 실행**한다. 본 조는 이 흐름을 **주기적 자동 실행 + 완료/실패 알림**으로 확장하는 요구사항과 설정 스키마를 정의한다.

### 5.0 범위 및 의존성

- **자동화 대상 흐름:** `crawl(소스 N종) → pipeline_orchestrator.py(요약·브리핑·리포트) → archive(리포트 보존) → 시계열 브리핑`을 하나의 잡(run)으로 묶어 주기 실행한다.
- **선행 의존성(제4조):** 아카이브 정책이 선행되어야 한다. 스케줄러는 매 실행 산출물(`FINAL_ACTION_REPORT.md/.html`)을 덮어쓰지 않고 실행 단위로 아카이브에 적재하며, 시계열 브리핑은 이 아카이브 누적 데이터를 입력으로 삼는다.
- **후행 연계:** 관측성(§5.5)과 대시보드 실행 이력 뷰는 스케줄러가 남긴 실행 로그·상태 파일을 소비한다.
- **비범위:** 다중 PC 분산 실행, 외부 큐/브로커(예: Celery), 클라우드 스케줄러는 v3.0 범위 밖(단일 로컬 Windows PC 전제).

### 5.1 기능 요구사항 (FR-5.x)

| ID | 요구사항 | 설명 | 수용 기준 |
|---|---|---|---|
| **FR-5.1** | 스케줄 실행 | `schedule.yaml`에 정의된 잡을 cron 또는 interval 주기로 자동 트리거한다. | 지정 시각/주기에 사람 개입 없이 잡이 시작되고, `enabled: false` 잡은 트리거되지 않는다. PC 재부팅 후에도 스케줄이 자동 복원된다. |
| **FR-5.2** | 잡 정의 | 하나의 잡은 `steps`(crawl 소스목록 → pipeline → archive → 시계열 브리핑)의 순차 파이프라인으로 선언된다. | `schedule.yaml`만 수정해 소스 조합·단계 on/off를 바꿀 수 있고, 코드 수정 없이 잡 추가/삭제가 가능하다. 각 스텝은 선언 순서대로 실행되고 앞 스텝 성공 시에만 다음 스텝이 진행된다. |
| **FR-5.3** | 실패 재시도 | 스텝 실패 시 지정 횟수만큼 백오프 간격으로 재시도하고, 최종 실패 시 잡을 실패 종료한다. | `retry.max_attempts`, `retry.backoff_sec` 설정이 반영된다. 재시도 소진 후에도 실패하면 실행 상태가 `failed`로 기록되고 실패 알림이 발송된다. Ollama 미실행 등으로 pipeline이 폴백 처리된 경우(무음 실패 아님)는 `partial`로 구분한다. |
| **FR-5.4** | 결과 알림 | 잡 완료/실패 시 설정된 채널로 결과 페이로드(§5.4)를 발송한다. | 성공·부분성공·실패 각각에 대해 알림이 발송되고, 페이로드에 `status`·`run_id`·소스별 건수·소요시간·리포트 경로가 포함된다. 로컬 채널(토스트/파일/콘솔)은 외부 자격증명 없이 동작한다. |
| **FR-5.5** | 실행 이력 로깅 | 매 실행의 시작·종료·스텝별 결과·에러를 구조화 로그로 영속화한다. | 실행마다 고유 `run_id`로 로그 레코드가 남고, 최근 N회 실행 상태를 파일에서 조회할 수 있다. 로그는 append-only이며 실패 사유(스택/폴백 건수)를 포함한다. |

### 5.2 스케줄러 방식 비교

| 방식 | 장점 | 단점 | 의존성 | 권장 시나리오 |
|---|---|---|---|---|
| **(a) Windows 작업 스케줄러 + 배치** | OS 기본 제공(추가 패키지 0). 재부팅 후 자동 복원. 상주 프로세스 불필요 → 유휴 시 자원 0. 로그아웃 상태에서도 실행 가능. | 잡 정의·재시도·백오프를 OS UI/XML로 관리 → 세밀한 제어 어려움. `schedule.yaml` 기반 다중 잡·소스 조합 표현이 빈약. 실행 이력이 OS 로그에 흩어짐. | 없음(OS 내장) + 기존 `.bat` | 단일 잡·고정 주기, 최소 구성으로 "돌기만 하면 되는" 경우. |
| **(b) APScheduler (파이썬 상주)** | `schedule.yaml`을 그대로 해석해 cron/interval·다중 잡·재시도·백오프를 코드로 정밀 제어. 알림·로깅·아카이브를 파이썬 한 흐름에 통합. 기존 스택(`requests`/`openai`)과 동일 런타임. | 상주 프로세스가 살아있어야 함 → 프로세스가 죽으면 스케줄 정지. 재부팅 자동기동을 별도 구성해야 함(자기 자신은 부팅 복원 못 함). | `pip install apscheduler` (신규) | 다중 소스·잡, 재시도/알림/이력까지 통합 제어가 필요한 경우. |
| **(c) 대시보드 내장 스케줄** | 별도 프로세스 없이 대시보드(`app.py`)에서 스케줄 설정·상태를 한 화면에서 확인. UX 일원화. | Streamlit은 세션/rerun 모델이라 백그라운드 타이머의 신뢰성이 낮음(브라우저·세션 종료 시 정지 위험). 장시간 잡이 UI 스레드를 점유. 상용 스케줄러로 부적합. | 기존 `streamlit` | 스케줄 실행 자체가 아니라 **상태 조회·수동 트리거 UI**로만 활용. |

**단일 로컬 Windows PC 권장안 — (a)로 부팅/기동을 보장하고, (b)로 잡 로직을 제어하는 하이브리드.**

- **Windows 작업 스케줄러**는 "부팅/로그온 시 1회" 트리거로 파이썬 스케줄러 러너(`run_scheduler.py`, APScheduler 기반)를 기동하는 역할만 맡는다. → 재부팅 자동 복원 확보((b)의 최대 약점 해소).
- **APScheduler 러너**가 `schedule.yaml`을 읽어 실제 잡·재시도·알림·이력을 담당한다. 각 스텝은 기존 크롤러/`pipeline_orchestrator.py`를 그대로 호출한다.
- **대시보드(c)**는 스케줄을 "실행"하지 않고, 실행 이력·최근 상태 **조회**와 잡 수동 트리거(on-demand) 버튼만 제공한다.
- 대안(최소 구성): 다중 잡이 필요 없고 고정 단일 주기면 순수 (a) — 작업 스케줄러가 `run_job.bat`(단일 잡 러너)를 직접 주기 호출 — 만으로도 FR-5.1~5.5를 충족할 수 있다.

### 5.3 잡/스케줄 설정 스키마 (`schedule.yaml`)

프로젝트 루트에 `schedule.yaml`을 두고 러너가 시작 시 로드한다. 소스 식별자는 제3조 소스 레지스트리(`sources.yaml`)의 소스 ID와 정합해야 한다.

```yaml
# schedule.yaml — 스케줄러 잡 정의
version: 1

defaults:                       # 잡별로 재정의 가능한 전역 기본값
  retry:
    max_attempts: 2             # 스텝 실패 시 총 시도 = 1 + 재시도
    backoff_sec: 120            # 재시도 간 대기(초), Ollama 콜드로드 대비
  notify:
    channels: [toast, file]     # 로컬 우선 기본 채널
  timezone: "Asia/Seoul"

jobs:
  - job_id: daily_full_brief          # 잡 고유 ID (로그/알림 키)
    enabled: true                     # false면 트리거 안 함(정의는 보존)
    description: "매일 아침 전 소스 수집→브리핑→아카이브"
    schedule:
      cron: "0 8 * * *"               # 매일 08:00 (cron/interval 중 택1)
    steps:
      - crawl:
          sources: [ai_portraits, youtube_sports, humor]   # 수집 소스 목록
      - pipeline:
          briefing_model: "qwen2.5:14b"   # 비-reasoning 모델(qwen3.5:9b 금지)
          download_images: true
          max_files: 0                    # 0=전체
      - archive:
          retain: 90                      # 아카이브 보존 일수(제4조)
      - timeseries_brief:                 # 시계열 브리핑(제4조 후행)
          window_days: 7
    notify:
      channels: [toast, file]
      on: [success, partial, failure]     # 알림 발송 조건

  - job_id: hourly_humor_watch
    enabled: false
    description: "유머 소스만 잦은 주기로 감시(예시)"
    schedule:
      interval:
        hours: 3                          # interval 방식 예시
    steps:
      - crawl: { sources: [humor] }
      - pipeline: { max_files: 5 }
      - archive: { retain: 30 }
    retry:
      max_attempts: 1                     # 잡 단위 재정의
    notify:
      channels: [console]
      on: [failure]
```

**필드 설명**

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `version` | int | ✔ | 스키마 버전(마이그레이션 대비). |
| `defaults` | map |  | 모든 잡에 적용되는 기본값. 잡 내 동일 키로 재정의 가능. |
| `jobs[]` | list | ✔ | 잡 정의 배열. |
| `jobs[].job_id` | string | ✔ | 잡 고유 식별자. 로그·알림·이력 키로 사용, 중복 불가. |
| `jobs[].enabled` | bool | ✔ | `false`면 정의는 유지하되 트리거하지 않음(FR-5.1). |
| `jobs[].description` | string |  | 사람이 읽는 설명. |
| `jobs[].schedule.cron` | string | △ | 5필드 cron 표현식. `interval`과 **택1**. |
| `jobs[].schedule.interval` | map | △ | `{days,hours,minutes}` 주기. `cron`과 택1. |
| `jobs[].steps[]` | list | ✔ | 순차 실행 스텝. 앞 스텝 성공 시 다음 진행(FR-5.2). |
| `steps[].crawl.sources` | list[string] | ✔ | 수집 소스 ID 목록(`sources.yaml`와 정합). |
| `steps[].pipeline` | map |  | `briefing_model`·`download_images`·`max_files` 등 `pipeline_orchestrator.py` 파라미터(MANUAL 환경변수와 1:1 매핑). |
| `steps[].archive.retain` | int |  | 아카이브 보존 일수(제4조). |
| `steps[].timeseries_brief.window_days` | int |  | 시계열 브리핑 집계 기간(제4조). |
| `jobs[].retry.max_attempts` | int |  | 스텝별 총 시도 수(1=재시도 없음)(FR-5.3). |
| `jobs[].retry.backoff_sec` | int |  | 재시도 간 대기 초. |
| `jobs[].notify.channels` | list[string] |  | 알림 채널(`toast`/`file`/`console`/`email`/`webhook`). |
| `jobs[].notify.on` | list[string] |  | 알림 발송 조건(`success`/`partial`/`failure`). |
| `defaults.timezone` | string |  | cron 해석 타임존(기본 `Asia/Seoul`). |

> **주의:** `pipeline.briefing_model`에는 reasoning 모델(`qwen3.5:9b`)을 지정하지 않는다 — `content` 없이 사고과정만 반환해 브리핑이 비게 된다(MANUAL §8, 기본값 `qwen2.5:14b` 유지).

### 5.4 알림 채널 요구사항

**로컬 우선(기본, 자격증명 불필요):**

| 채널 | 방식 | 비고 |
|---|---|---|
| `toast` | Windows 데스크톱 토스트 알림 | 로컬 GUI 환경 기본. 성공/실패 요약을 즉시 표시. |
| `file` | 알림 페이로드를 `workspaces\logs\notifications\<run_id>.json`으로 기록 | 오프라인·무인 실행에서도 항상 남는 1차 기록. |
| `console` | 러너 표준출력/로그에 출력 | 포그라운드 실행·디버깅용. |

**선택적 확장(옵트인):**

| 채널 | 방식 | 비고 |
|---|---|---|
| `email` | SMTP 발송 | 자격증명은 코드/`schedule.yaml`에 두지 않고 **환경변수 또는 OS 자격증명 저장소**에서 로드. |
| `webhook` | HTTP POST(예: 사내 챗봇) | URL·토큰은 환경변수로 주입. |

**알림 페이로드 스키마(모든 채널 공통):**

```json
{
  "status": "success",
  "run_id": "daily_full_brief-20260821T080012",
  "job_id": "daily_full_brief",
  "started_at": "2026-08-21T08:00:12+09:00",
  "duration_sec": 214,
  "sources": {
    "ai_portraits": { "crawled": 50, "summarized": 50, "fallback": 0 },
    "youtube_sports": { "crawled": 48, "summarized": 48, "fallback": 0 },
    "humor": { "crawled": 5, "summarized": 5, "fallback": 0 }
  },
  "report_paths": {
    "md": "workspaces/final_outputs/FINAL_ACTION_REPORT.md",
    "html": "workspaces/final_outputs/FINAL_ACTION_REPORT.html",
    "archive": "workspaces/archive/20260821T080012/"
  },
  "failure_reason": null
}
```

- `status`는 전체 성공(`success`), 폴백 발생 등 부분 성공(`partial`), 잡 실패(`failure`)를 구분한다. 폴백 건수는 `sources.*.fallback`으로도 노출한다.
- **민감정보/자격증명 하드코딩 금지:** SMTP 비밀번호·웹훅 토큰·API 키는 `schedule.yaml`·소스코드·로그·알림 페이로드 어디에도 평문으로 저장하지 않는다. 오직 환경변수 또는 OS 자격증명 저장소에서 런타임 로드하며, 로그·페이로드에 출력 시 마스킹한다.

### 5.5 관측성 (Observability)

- **실행 로그 위치:** `workspaces\logs\scheduler\` 하위에 실행 이력을 append-only로 적재한다.
  - `runs.jsonl` — 실행 1건 = 1 라인(JSON Lines). 각 라인은 §5.4 페이로드 + 스텝별 결과를 담아 프로그램적 조회에 사용(FR-5.5).
  - `<run_id>.log` — 해당 실행의 상세 텍스트 로그(스텝 진행·재시도·에러 스택).
  - `notifications\<run_id>.json` — `file` 채널이 남기는 알림 사본.
- **로그 포맷:** 기계 판독은 JSONL(구조화 필드: `run_id`·`job_id`·`status`·`duration_sec`·`sources`·`failure_reason`), 사람 판독은 타임스탬프 프리픽스 텍스트 로그. 모든 레코드는 `run_id`로 상호 연결된다.
- **대시보드 상태 확인:** `app.py`에 "실행 이력" 탭/섹션을 추가해 `runs.jsonl` 최근 N개를 읽어 **잡별 최근 실행 상태(성공/부분/실패)·소요시간·리포트 링크·폴백 건수**를 표로 표시한다. 대시보드는 스케줄을 실행하지 않고 조회·수동 트리거만 담당한다(§5.2 (c) 권장안과 정합).
- **상태 요약 파일(선택):** `workspaces\logs\scheduler\last_status.json`에 잡별 최신 실행 요약을 유지해 대시보드·외부 툴이 전체 로그를 파싱하지 않고도 최근 상태를 즉시 읽게 한다.

---

## 6. 분류·태깅 & Reasoning 모델 (Classification & Reasoning)

> 본 조는 제6조 결정("요약+브리핑+분류·태깅 확장")과 제8조 릴리스 범위("P2 품질 검수 루프", "P2 reasoning 모델 흡수")를 구체화한다. 기존 요약(`hermes3:8b`)·브리핑(`qwen2.5:14b`) 파이프라인은 그대로 두고, **각 아이템에 구조화된 메타(category/tags 등)를 부여하는 단계**를 요약과 브리핑 사이에 삽입하며, 현재 브리핑에서 배제된 **reasoning 모델(`qwen3.5:9b`)을 분류·검수 보조 경로로 흡수**한다.

### 6.1 기능 요구사항 (FR-6.x)

| ID | 요구사항 | 설명 / 수용기준 | 우선순위 |
|---|---|---|---|
| **FR-6.1** | 카테고리 자동 분류 | 각 아이템에 **공통 택소노미 + 소스별 라벨** 중 정확히 1개의 `category`를 부여한다. 수용기준: 택소노미에 없는 값이 나오면 스키마 검증에서 반려되고 재시도(FR-6.5) 후에도 실패 시 `"미분류"`로 강제 확정. 분류는 **캐시된 요약문**을 입력으로 사용(원문 전체 재입력 금지, 비용·지연 절감). | P1 |
| **FR-6.2** | 태깅 | 각 아이템에 0~N개의 자유/반통제 `tags[]`(소문자·공백→`-`, 최대 8개)를 부여한다. 수용기준: 중복·빈 문자열 제거, 개수 상한 초과 시 앞에서부터 절단, 배열 타입 검증 통과. | P1 |
| **FR-6.3** | 감성 스코어 (선택) | `sentiment ∈ {positive, neutral, negative}` (또는 -1.0~+1.0). 수용기준: **소스별 활성화** — portrait/humor 등 감성이 무의미한 소스는 기본 비활성(`null`). 뉴스·이슈성 소스에만 적용. | P2 |
| **FR-6.4** | 중요도 스코어 (선택) | `importance ∈ 0~100`(또는 low/med/high). 수용기준: **제4조 아카이브가 누적된 뒤** 소스 내 상대 기준선으로 산정(단발 판단 금지). 아카이브 부재 시 `null` 반환 및 그 사유를 리포트 헤더에 1회 표기. | P2 |
| **FR-6.5** | 구조화 출력 검증·재시도 | 분류 응답을 JSON 스키마(6.2)로 검증하고 실패 시 최대 N회(기본 2) 재시도한다. 수용기준: 파싱 실패/필드 누락/enum 위반은 재시도, 최종 실패는 폴백(FR-6.7). `temperature`는 결정론 지향(기본 0.1 이하). | P1 |
| **FR-6.6** | 분류 캐시(요약과 독립) | 분류 결과는 요약 캐시(SRC-HASH)와 **별개 키**로 캐싱한다. 수용기준: 택소노미 버전(`class_schema_ver`) 또는 분류 모델(`class_model`)이 바뀌면 요약 재호출 없이 **분류만** 무효화·재실행(6.3 무효화 규칙). | P1 |
| **FR-6.7** | 분류 폴백(무음 실패 방지) | 분류 실패는 브리핑을 **차단하지 않는다**. 수용기준: 실패 아이템은 `category:"미분류"`, `confidence:0`으로 확정하고, 실패 건수를 기존 요약/브리핑 폴백과 동일하게 `FINAL_ACTION_REPORT.md` 헤더에 합산 표기(현행 폴백 정책과 동일 형태). | P1 |
| **FR-6.8** | reasoning 모델 흡수(계측·경로) | `qwen3.5:9b`를 심층 분류/품질 사전검수 경로로 활용한다. 수용기준: `/v1` 응답 객체의 **실제 필드 구성(content 유무·reasoning 필드명)을 계측·기록**하고, `think` 제어가 `/v1`에서 무효하면 native `/api/chat` 경로를 추가한다(6.5). 브리핑 기본 모델은 계속 `qwen2.5:14b` — 본 FR은 브리핑 모델을 교체하지 않는다. | P2 |
| **FR-6.9** | 리포트/대시보드 노출 | 분류·태그를 HTML 카드 배지 및 브리핑 입력에 반영한다. 수용기준: 카드에 `category` 배지 + `tags` 칩 렌더, 브리핑 프롬프트에 **카테고리/태그 분포**를 구조화 입력으로 전달. | P2 |

### 6.2 태깅 / 분류 스키마

각 아이템(원본 `.txt` 1건)에 부여하는 메타 필드:

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `category` | string(enum) | O | 공통 또는 소스별 택소노미 중 1개. 실패 시 `"미분류"`. |
| `tags` | string[] | O | 0~8개, 정규화(소문자·`-`). |
| `sentiment` | enum \| null | X | `positive`/`neutral`/`negative`. 비활성 소스는 `null`. |
| `importance` | int(0~100) \| null | X | 아카이브 기준선 산정. 부재 시 `null`. |
| `confidence` | float(0~1) | O | 분류 신뢰도. 폴백 시 `0`. |
| `class_model` | string | O | 분류 수행 모델(예: `qwen2.5:7b`). |
| `class_schema_ver` | string | O | 택소노미/스키마 버전(예: `t1`). |
| `classified_at` | ISO8601 | O | 분류 시각. |

**예시 JSON**

```json
{
  "src_hash": "3f9a1c2b7d0e4f88",
  "category": "경기결과",
  "tags": ["축구", "국가대표", "하이라이트"],
  "sentiment": "positive",
  "importance": 72,
  "confidence": 0.86,
  "class_model": "qwen2.5:7b",
  "class_schema_ver": "t1",
  "classified_at": "2026-08-21T10:32:00+09:00"
}
```

**저장 방식 — 권장: 사이드카 메타 파일(비파괴).**
현행 `refined_data\<name>.md`는 1행이 `<!-- SRC-HASH: ... -->`, 2행이 `<!-- MODEL: ... -->`로 시작한다(MANUAL §6). YAML 프런트매터는 1행부터만 파싱되므로 이 주석과 충돌한다. 따라서 **기본안(권장)** 은 요약 `.md`를 건드리지 않고 형제 파일 `refined_data\<name>.meta.json`에 위 객체를 저장한다(요약 캐시 리더·기존 포맷 무변경).
**대안(프런트매터 흡수):** `.md` 1행부터 `---` YAML 블록으로 전환하고 `src_hash`/`model`을 그 안에 통합. 단 이는 **캐시 리더의 파괴적 변경**이므로, 리더는 "선두 `---`가 없으면 기존 주석 스캔으로 폴백"하는 하위호환 규칙을 반드시 함께 구현한다. 본 PRD는 기본안(사이드카)을 채택한다.

**택소노미 예시**

- 공통(소스 무관): `정보/뉴스`, `엔터테인먼트`, `기술`, `이미지/비주얼`, `토론/여론`, `기타`, `미분류`
- 소스별(제3조에 따라 **코드가 아니라 `sources.yaml` 엔트리에 선언**):
  - `sports_*`: `경기결과`, `이적/계약`, `선수동향`, `일정/프리뷰`
  - `humor_*`: `유머`, `이슈`, `짤/움짤`, `정보성글`
  - `ai_portrait_*`: `인물/포트레이트`, `스타일/컨셉`, `프롬프트예시`

> 제3조에서 기존 3종 크롤러가 소스 레지스트리 엔트리로 이관되므로, 소스별 라벨을 코드에 하드코딩하지 않고 각 `sources.yaml` 엔트리의 `taxonomy:` 키로 선언한다. 신규 소스 추가 시 코드 수정 없이 라벨만 확장된다.

### 6.3 분류 프롬프트 요구사항

- **모델:** 소형 instruct 모델(`hermes3:8b` 또는 현재 파이프라인 미사용 상태인 `qwen2.5:7b`)로 수행. 환경변수 `CLASSIFY_MODEL`(기본 `qwen2.5:7b`)로 교체 가능.
- **구조화 출력 유도:** `/v1` 경로에서는 `response_format={"type":"json_object"}`로 JSON을 강제하고, 프롬프트에 **허용 category enum 목록과 정확한 필드 스키마**를 명시한다. native `/api/chat` 경로를 채택할 경우에만 스키마 제약 `format`(JSON schema)을 사용한다.
- **결정론성:** `temperature ≤ 0.1`, `top_p` 보수적 설정. 동일 입력→동일 분류를 지향(캐시 일관성 확보).
- **검증·재시도(FR-6.5):** 응답을 스키마로 검증하고, enum 위반·필드 누락·파싱 실패 시 "직전 출력이 스키마를 위반했다"는 지시를 덧붙여 최대 2회 재시도. 최종 실패는 폴백(FR-6.7).
- **입력:** 원문 전체가 아닌 **캐시된 요약문**을 분류 입력으로 사용(비용·지연 절감, 브리핑 품질과 일관).
- **무효화 규칙:** 분류 캐시는 `SRC-HASH` **또는** `class_schema_ver` **또는** `class_model` 중 하나라도 바뀌면 재실행. 요약 캐시(SRC-HASH 단독)와 독립적으로 동작하여, 택소노미만 수정한 경우 50건 요약을 재호출하지 않고 분류만 갱신한다.

### 6.4 Reasoning 모델(`qwen3.5:9b`) 흡수

`qwen3.5:9b`는 `/v1` 응답에서 `content`가 비고 reasoning(사고과정)만 반환하는 특성이 있어 현재 브리핑에서 제외돼 있다(MANUAL §2/§8). 두 경로를 비교·병행한다.

| 경로 | 방식 | 장점 | 한계 / 조건 |
|---|---|---|---|
| **(a) thinking 끄기** | Ollama `think=false`로 사고과정을 끄고 일반 `content` 사용 | 기존 `llm_chat()` 흐름 그대로 재사용, 일반 instruct처럼 취급 | `think`는 **native `/api/chat`** 파라미터. `/v1`(openai 클라이언트, LiteLLM 경유 가능)에서 `extra_body`로 전달 시 유효한지 **계측 필요**. 무효면 (a)는 native 경로에서만 성립 |
| **(b) reasoning 활용** | `content` 대신 **reasoning 필드**를 분석·검수 근거로 수집 | 사고과정 자체가 품질검수·근거 추출에 유용 | `/v1`에서의 정확한 **필드명 계측 필요**. 근거 텍스트라 정형 출력엔 부적합 |

**계측 요구(FR-6.8):** 기존 `llm_chat()`의 "빈 content 감지→폴백" 지점이 계측 훅이다. 이 지점에서 `qwen3.5:9b`의 `/v1` 실제 응답 객체(있는 필드, reasoning 필드명)를 기록하고, `think` 제어가 `/v1`에서 무효로 판명되면 native `/api/chat` 경로를 추가한다.

**작업 매핑(어디에 reasoning을 쓰나):**
- **일반 요약/브리핑:** reasoning 모델 **미사용**. 요약=`hermes3:8b`, 브리핑=`qwen2.5:14b` 유지.
- **심층 분류(모호·경계 아이템):** `qwen2.5:7b` 1차 분류의 `confidence`가 낮은 아이템만 경로 (b)로 재판정.
- **품질 사전검수(1차 게이트):** 브리핑 산출물에 대한 **로컬 1차 선별**. 단 제2조가 "브리핑 품질 검수"를 클라우드 브레인에 이미 위임했으므로, 로컬 reasoning은 **1차 게이트(사전 선별·플래깅)** 로 한정하고 **최종 검수는 클라우드 브레인**이 수행(중복 책임 방지).

### 6.5 파이프라인 삽입 위치

```
원본(.txt) → [요약: hermes3:8b] → refined_data\*.md (SRC-HASH 캐시)
                                        │
                                        ▼
                      ★ [분류·태깅: qwen2.5:7b]  ← 본 조 신설 단계
                         입력=캐시된 요약문, 출력=*.meta.json
                         (저confidence 아이템 → qwen3.5:9b 재판정)
                                        │
                                        ▼
                   [종합 브리핑: qwen2.5:14b]  ← 카테고리/태그 분포를 구조화 입력으로 수신
                                        │
                                        ▼
            FINAL_ACTION_REPORT.md / .html (카드에 category 배지·tags 칩)
```

- **위치:** 개별 요약 **직후**, 종합 브리핑 **직전**. 분류는 요약문을 소비하고, 브리핑은 분류 결과(카테고리/태그 분포)를 입력으로 받으므로 순서가 고정된다.
- **토글:** 기존 `DOWNLOAD_IMAGES`와 동형으로 `CLASSIFY`(기본 `1`)를 두어 분류 단계를 on/off. 관련 환경변수: `CLASSIFY_MODEL`(기본 `qwen2.5:7b`), `CLASSIFY_TEMP`(기본 `0.1`), `CLASSIFY_SCHEMA_VER`.
- **폴백 정합:** 분류 실패는 브리핑을 막지 않으며, 실패 건수는 기존 요약/브리핑 폴백 카운트와 함께 `.md` 헤더에 합산 표기된다.

### 6.6 선행 / 후행 의존성

- **선행:** 제3조 소스 레지스트리(`sources.yaml`) — 소스별 택소노미 라벨 선언의 근거지. (선택 필드 FR-6.4는 제4조 아카이브 누적을 전제.)
- **후행:** 제4조 시계열 브리핑/아카이브(카테고리별 시계열 집계), 제5조 알림(중요도 임계 기반 트리거), 제2조 클라우드 브레인 최종 품질검수(로컬 reasoning 1차 게이트의 상위 검수).

---

## 7. 트랙 B 거취 — 동결 (Track B: Frozen)

제7조 결정에 따라 **트랙 B(LiteLLM 프록시 + Open Interpreter 대화형 에이전트)는 v3.0 범위에서 동결**한다.

| 항목 | 방침 |
|---|---|
| 신규 개발 | 하지 않음 |
| 기존 자산 | `1_서버실행_LiteLLM.bat`, `2_에이전트실행_Interpreter.bat`, `config.yaml` 보존(삭제 금지) |
| 의존성 | Streamlit 설치로 `open-interpreter`와 패키지 충돌 상태 → 트랙 B 사용 시 **전용 venv 분리** 권장(MANUAL §8) |
| 해제 조건 | v3.0 릴리스 후 별도 결정으로 재개 |

> 트랙 B의 `config.yaml` 모델 매핑(`local-agent`=hermes3:8b, `local-qwen`=qwen3.5:9b)은 트랙 A 파이프라인과 무관하며 변경하지 않는다.

---

## 8. 품질 검수 루프 (Quality Assurance Loop)

### 8.1 개요

`pipeline_orchestrator.py`가 생성한 **개별 요약(`hermes3:8b`)** 과 **종합 브리핑(`qwen2.5:14b`)** 의 품질을 자동/반자동으로 점검하고, 임계값 미달 시 **재생성**하거나 **클라우드 브레인 검수로 에스컬레이션**하는 루프를 정의한다. 제2조에서 "브리핑 품질 검수"를 클라우드 브레인에 위임하기로 결정했으며(제1조: 브라우저 자동화 연동), 제8조 릴리스 계획상 본 루프는 **P2(2차 고도화)** 범위다.

검수는 3단계 게이트로 구성된다: **(1) 규칙기반 자동 검증**(비용 0, 로컬) → **(2) LLM-judge 점수화**(로컬 모델, 결정론적) → **(3) 클라우드 브레인 최종 검수**(브릿지 경유, 반자동). 앞단에서 통과하면 뒷단을 호출하지 않는 **조기 종료(early-exit)** 원칙을 따라 로컬 비용과 브레인 호출을 최소화한다.

> 설계 원칙: 기존 파이프라인의 **폴백 정책**(Ollama 실패 시 원문 발췌 대체 + 실패 건수 헤더 명시)과 충돌하지 않는다. 폴백으로 생성된 산출물은 규칙기반 게이트에서 `is_fallback=true`로 즉시 검출되어 재생성/에스컬레이션 후보가 된다.

---

### 8.2 기능 요구사항 (FR-8.x)

| ID | 요구사항 | 설명 / 수용기준 |
|---|---|---|
| **FR-8.1** | 품질 지표 산출 | 각 요약·브리핑 산출물에 대해 규칙기반 지표와 LLM-judge 점수를 산출한다. **수용기준:** 모든 산출물에 `scores{}`(규칙+judge)와 `passed`(bool)가 부착되며, 산출물별 QA 메타가 저장된다(§8.5). |
| **FR-8.2** | 자동 검증 규칙 | 규칙기반 검사(길이·빈응답·폴백여부·금칙어·원문 근거)를 통과/실패로 판정한다. **수용기준:** 규칙 5종을 모두 평가하고, 하나라도 위반 시 `rule_pass=false` 및 위반 규칙명 목록을 기록한다. 규칙 위반은 LLM-judge를 호출하지 않고 즉시 재생성 큐로 보낸다. |
| **FR-8.3** | LLM-judge 점수화 | 로컬 모델이 요약 **충실도(faithfulness)**·**간결성(conciseness)**·**완결성(completeness)** 을 1~5점으로 채점한다. **수용기준:** `temperature=0`(결정론) 호출로 동일 입력에 동일 점수를 반환하며, 평균 점수가 임계값(§8.4) 이상이면 `judge_pass=true`. |
| **FR-8.4** | 재생성 루프 | 검증 미달 산출물을 최대 **N회(기본 2회)** 재생성한다. **수용기준:** 재시도마다 `attempts` 증가, 프롬프트를 실패 사유(길이 초과/근거 부족 등)에 맞게 보정한 재프롬프트로 호출한다. N회 후에도 미달이면 `escalated` 후보로 전환한다. |
| **FR-8.5** | 클라우드 브레인 에스컬레이션 | N회 재생성 후에도 미달인 산출물을 브릿지 폴더 `bridge\requests\`에 검수 요청으로 기록한다. **수용기준:** 요청 JSON에 산출물 본문·원문 근거·실패 사유·QA 메타를 포함하고, 상태를 `escalated`로 표기한다. 브레인 응답 수신은 프롬프트 브릿지 규약(제2조/제8조 P0)을 재사용한다. |
| **FR-8.6** | 상태 기록 & 리포트 반영 | 각 산출물의 QA 결과와 전체 QA 요약(통과율·재생성 건수·에스컬레이션 건수)을 리포트 헤더에 명시한다. **수용기준:** `FINAL_ACTION_REPORT.md` 헤더에 폴백 건수와 함께 QA 통계가 노출되어 무음 실패를 방지한다. |
| **FR-8.7** | 검수 스킵/비활성 옵션 | 환경변수로 QA 루프를 켜고 끌 수 있다. **수용기준:** `QA_ENABLED=0`이면 기존 v2.2.0 동작(검수 없음)과 동일하게 파이프라인이 완주한다. |

---

### 8.3 품질 지표 정의

#### (a) 규칙기반 지표 (로컬, 비용 0)

| 지표 | 산식 / 판정 | 임계값(예시) |
|---|---|---|
| 길이 적정성 | 요약: 문장 수 ∈ [2, 4] 또는 `len(chars)` ∈ [80, 600] · 브리핑: `len(chars)` ≥ 400 | 범위 밖이면 실패 |
| 빈응답 | `content`가 공백/None이거나 `len(strip) < 20` | `< 20자` → 실패 |
| 폴백 여부 | 산출물 생성 경로가 원문 발췌 폴백이면 `is_fallback=true` | `true` → 실패(재생성 후보) |
| 금칙어 | LLM 상용구·거절문(예: "죄송하지만", "As an AI", "I cannot", "요약할 수 없") 포함 여부 | 1건 이상 → 실패 |
| 원문 근거 포함 | 요약 토큰과 원문 토큰의 겹침 비율(자카드/키워드 매칭) = `overlap(summary, source)` | `< 0.15` → 실패(환각 의심) |

> 규칙기반 게이트는 정규식·문자열 검사만 사용하며 LLM을 호출하지 않는다. `is_fallback`은 기존 파이프라인의 폴백 플래그를 재사용한다.

#### (b) LLM-judge 지표 (로컬 모델, 결정론적)

| 지표 | 정의 | 산식 | 임계값(예시) |
|---|---|---|---|
| 충실도(faithfulness) | 원문에 없는 내용을 지어내지 않았는가 | 1~5 정수 점수 | ≥ 4 |
| 간결성(conciseness) | 불필요한 반복·군더더기 없이 핵심만 담았는가 | 1~5 정수 점수 | ≥ 3 |
| 완결성(completeness) | 원문의 핵심 논점을 빠짐없이 반영했는가 | 1~5 정수 점수 | ≥ 3 |
| **종합 판정** | 세 지표 가중 평균 | `score = 0.5·faith + 0.25·concise + 0.25·complete` | **≥ 3.8** → `judge_pass=true` |

- **judge 모델:** 기본 `qwen2.5:14b`(브리핑과 동일 고품질 instruct). `JUDGE_MODEL` 환경변수로 교체 가능하되, **`qwen3.5:9b`(reasoning 모델)는 금지** — `content` 없이 사고과정만 반환하여 점수 파싱이 불가하다(기존 브리핑 제외 사유와 동일).

#### (c) 클라우드 브레인 최종 검수 (반자동)

- 로컬 게이트를 N회 통과하지 못한 산출물만 브레인에 위임한다. 브레인은 **재작성안 또는 반려 사유**를 반환하며, 이는 로컬 점수보다 상위 권위를 갖는다(제2조 위임 결정).
- 임계: 로컬에서 `judge_pass=false`가 재생성 후에도 지속될 때만 트리거. 브레인 검수 결과는 `scores.brain_verdict`(`approved` / `revised` / `rejected`)로 기록한다.

---

### 8.4 검수 루프 흐름

```text
요약/브리핑 생성 (hermes3:8b / qwen2.5:14b)
        │
        ▼
[게이트1] 규칙기반 자동 검증  ── 통과 ──┐
        │ 실패                         │
        ▼                              │
[게이트2] LLM-judge 점수화     ── 통과 ─┤──▶ passed=true → 산출물 확정
 (temperature=0)                       │
        │ 미달                         │
        ▼                              │
   attempts < N ?  ── 예 ──▶ 프롬프트 보정 후 재생성 ──┘  (attempts++)
        │ 아니오(N회 소진)
        ▼
[게이트3] 클라우드 브레인 에스컬레이션
   bridge\requests\qa_<산출물ID>.json 기록 (escalated=true)
        │
        ▼
   브릿지 규약으로 브레인 응답 수신 → scores.brain_verdict 반영 → 리포트 갱신
```

- **N(재시도 횟수):** 기본 2회. `QA_MAX_RETRY` 환경변수로 조정.
- **조기 종료:** 게이트1 또는 게이트2를 통과하면 이후 단계를 호출하지 않는다.
- **상태 기록:** 매 단계에서 QA 메타(§8.5)를 갱신하고, 파이프라인 종료 시 전체 통계를 `FINAL_ACTION_REPORT.md` 헤더에 요약한다(폴백 건수 표기와 동일 위치).

---

### 8.5 품질 메타 스키마

각 산출물에 QA 결과 객체를 부착한다. 저장 위치는 두 가지다.

- **개별 요약:** `workspaces\refined_data\<파일>.md`의 헤더 주석에 `<!-- QA: {...} -->` 한 줄로 임베드(기존 `SRC-HASH`/`MODEL` 주석과 동일 관례).
- **집계:** `workspaces\final_outputs\qa_report.json`에 전 산출물 QA 결과를 배열로 축적.
- **에스컬레이션 요청:** `bridge\requests\qa_<산출물ID>.json`.

```json
{
  "artifact_id": "humor_20260821_003",
  "artifact_type": "summary",
  "model": "hermes3:8b",
  "src_hash": "a1b2c3d4e5f60789",
  "scores": {
    "rule_pass": false,
    "rule_violations": ["원문근거부족", "금칙어"],
    "judge": { "faithfulness": 3, "conciseness": 4, "completeness": 3, "weighted": 3.25 },
    "judge_pass": false,
    "brain_verdict": "revised"
  },
  "passed": false,
  "attempts": 2,
  "escalated": true,
  "is_fallback": false,
  "checked_at": "2026-08-21T14:32:10+09:00"
}
```

- `passed`: 최종 통과 여부(게이트1·2 통과 또는 브레인 `approved`/`revised` 반영 시 `true`).
- `attempts`: 재생성 횟수(0=최초 통과).
- `escalated`: 브레인 위임 발생 여부.
- `is_fallback`: 원문 발췌 폴백으로 생성된 산출물 여부.

---

### 8.6 LLM-judge 프롬프트 개요 및 결정론성 요구

- **역할 고정:** "너는 요약 품질 평가자다. 주어진 [원문]과 [요약]을 읽고 충실도·간결성·완결성을 각각 1~5점으로 채점하라."
- **입력:** 원문 본문(또는 발췌) + 평가 대상 요약/브리핑.
- **출력 강제:** 반드시 **JSON 한 줄**로만 응답하도록 지시 — `{"faithfulness":N,"conciseness":N,"completeness":N,"reason":"..."}`. 여분 텍스트·마크다운 금지(파싱 안정성).
- **결정론성 요구:** judge 호출은 **`temperature=0`**(가능하면 `top_p=1`, `seed` 고정)으로 실행하여 동일 입력에 동일 점수를 재현한다. 이는 캐시(원문 SHA-256)와 결합해 **동일 콘텐츠 재검수 시 재호출을 생략**할 수 있게 한다.
- **모델 제약:** judge 모델은 `content`에 최종 답을 담는 instruct 계열이어야 하며, reasoning 모델(`qwen3.5:9b`)은 사용하지 않는다.

---

### 8.7 선행/후행 의존성

- **선행:** 개별 요약·종합 브리핑 산출(파이프라인 `pipeline_orchestrator.py`, `hermes3:8b`/`qwen2.5:14b`)과 원문 근거 산정을 위한 `raw_inputs` 원문·SHA-256 해시에 의존한다.
- **후행:** 에스컬레이션은 **프롬프트 브릿지 폴더 규약(제2조 P0)** 의 `bridge\requests\` 경로와 브레인 응답 수신 절차에 의존하며, 브라우저 자동화 기반 클라우드 브레인 연동(제1조)을 전제로 한다.

---

## 9. 마일스톤 & 우선순위 (Milestones)

제8조의 P0/P1/P2와 섹션 간 의존성을 반영한 순차 마일스톤이다. **각 마일스톤 내부 항목은 병렬 개발 가능**하되, 마일스톤 간에는 의존성이 있어 순차 진행한다.

### 의존성 그래프
```text
[M1 · P0]                         [M2 · P1]                    [M3 · P2]
소스 레지스트리 ─────────────▶ 스케줄러+알림
아카이브 ───────────────────▶ 시계열 브리핑
프롬프트 브릿지 ──┬──────────▶ (브레인 소스발굴/코드생성) ──▶ 품질 검수 루프
                 └───────────────────────────────────────▶ (브리핑 품질검수 위임)
요약/브리핑(기존) ─────────────────────────────────────▶ 분류·태깅 + reasoning 흡수
```

### M1 — 기반 (P0)
| 항목 | 산출물 | 의존 |
|---|---|---|
| 소스 레지스트리 + 범용 수집 (§3) | `sources.yaml`, 범용 추출기, 크롤러 이관 | 없음 |
| 아카이브 (§4) | `workspaces\archive\` 스냅샷·manifest | 없음 |
| 프롬프트 브릿지 폴더 규약 (§2) | `bridge\` 요청/응답 프로토콜 | 없음 |

### M2 — 자동화 (P1)
| 항목 | 산출물 | 의존 |
|---|---|---|
| 스케줄러 + 알림 (§5) | `schedule.yaml`, 실행기, 알림 | M1(레지스트리·아카이브) |
| 시계열 브리핑 (§4) | 최근 N일 비교 브리핑 | M1(아카이브) |

### M3 — 지능화 (P2)
| 항목 | 산출물 | 의존 |
|---|---|---|
| 분류·태깅 + reasoning 흡수 (§6) | 태깅 스키마, reasoning 통합 | 기존 요약 단계 |
| 품질 검수 루프 (§8) | QA 지표·재생성·에스컬레이션 | M1(브릿지), 요약/브리핑 |

### 수용(릴리스) 기준 개요
- **M1:** `sources.yaml`로 최소 2개 소스(RSS 1 + HTML 1) 수집·리포트 생성. 실행 결과가 날짜별 아카이브에 남는다. `bridge\`로 요청/응답 파일 왕복 1건 성공.
- **M2:** 스케줄로 무인 실행 1회 성공 + 완료 알림 수신. 어제 대비 시계열 브리핑 1건 생성.
- **M3:** 아이템에 category/tags 자동 부여. QA 루프가 폴백/저품질을 감지해 재생성 또는 에스컬레이션.

---

## 10. 통합 데이터 스키마 (Consolidated Schemas)

_각 섹션의 스키마를 통합·정합한 목록. (§2–§6, §8 확정 후 정리)_

| 스키마 | 위치 | 정의 섹션 |
|---|---|---|
| 소스 레지스트리 | `sources.yaml` | §3 |
| 아카이브 매니페스트 | `workspaces\archive\<date>\manifest.json` | §4 |
| 브릿지 요청/응답 | `bridge\requests\*.json`, `bridge\responses\*.json` | §2 |
| 스케줄 정의 | `schedule.yaml` | §5 |
| 아이템 태깅/분류 | refined 프런트매터 또는 메타 파일 | §6 |
| QA 결과 | 산출물별 QA 메타 | §8 |

> raw_inputs `.txt` 공통 스키마(제목/원문링크/[메타데이터]/[미디어영역]/[본문 전문]/[출처 URL])는 v2.2.0과 **하위호환 유지**한다.

---

## 11. 리스크 & 오픈 이슈 (Risks)

| # | 리스크 | 영향 | 완화책 |
|---|---|---|---|
| R1 | 클라우드 브레인 **브라우저 자동화**의 불안정성·약관 리스크(제1조 비권장 선택) | 위임 작업 실패 | 사람 개입 지점 명시, 실패 시 로컬 단독 폴백, 브레인 산출물 검증 게이트(§2) |
| R2 | 무인 스케줄 실행 중 크롤 차단/네트워크 오류 | 빈 리포트 | 재시도·부분성공 허용, 실패 알림, 폴백 표기 |
| R3 | 아카이브 무한 증가(디스크) | 저장공간 | 보존기간(TTL)·이미지 중복제거 정책(§4) |
| R4 | reasoning 모델(qwen3.5:9b) 통합 시 빈 content/지연 | 브리핑 품질 저하 | think 제어 또는 용도 한정(§6), 비-reasoning 폴백 |
| R5 | Streamlit ↔ open-interpreter 패키지 충돌 | 트랙 B 오작동 | venv 분리(§7) |
| R6 | 크롤러 자동 생성 코드의 안전성 | 임의 코드 실행 | 브레인 생성 코드는 검토·검증 후 반영(§2) |

---

_본 문서는 상위 결정사항(PRD_결정사항_v3.md)을 구현 가능한 요구사항으로 구체화한 초안이며, §2–§6·§8은 병렬 작성 결과를 통합하여 확정한다._
