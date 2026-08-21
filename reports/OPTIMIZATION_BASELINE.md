# OPTIMIZATION_BASELINE.md — 파이프라인 베이스라인 (v2, DEV-05 Task 3)

> v1 혼합 중앙값(70.0s)은 **폐기**. 이후 모든 최적화는 아래 **웜/콜드 중 어느 상태 대비** 개선인지 명시해야 한다.
> 측정 범위: 수집로드→이미지→요약(EXAONE 구조화)→브리핑(qwen2.5:14b)→렌더. 전사/VLM/TTS/전송/인덱싱 미포함.
> 토큰은 Ollama 실측(prompt_eval/eval → usage), schema_ver=2. 요약 단계 keep_alive 언로드(§Task1) 적용 상태.

## 1. 웜 베이스라인 (캐시 적중 — 일상 운영)

### 웜

- 실행 실측치: 189.2, 36.6, 33.1 s
- **중앙값: 36.6s** · 편차(max-min): **156.1s** (개선율이 이 편차 이내면 '개선 없음' 판정)

| 단계 | 소요(s, 중앙값) |
| --- | ---: |
| load | 0.10 |
| images | 0.05 |
| summary | 0.06 |
| briefing | 31.20 |
| render | 0.09 |

LLM 실호출(캐시 미스, schema_ver=2):

| 단계 | 실호출수 | prompt_tokens합 | output_tokens합 | 평균응답(s, 실호출만) |
| --- | ---: | ---: | ---: | ---: |
| briefing | 3 | 10494 | 1643 | 30.11 |
| summary | 106 | 25744 | 10763 | 1.41 |

캐시 반환: summary 212건

피크 VRAM(GPU 전체, MB): briefing 11636, images 1600, load 1429, render 1422, summary 8230

## 2. 콜드 베이스라인 (캐시 비움 — 신규 대량 유입)

### 콜드

- 실행 실측치: 184.8, 181.5 s
- **중앙값: 183.2s** · 편차(max-min): **3.3s** (개선율이 이 편차 이내면 '개선 없음' 판정)

| 단계 | 소요(s, 중앙값) |
| --- | ---: |
| load | 0.06 |
| images | 0.04 |
| summary | 148.57 |
| briefing | 27.30 |
| render | 0.10 |

LLM 실호출(캐시 미스, schema_ver=2):

| 단계 | 실호출수 | prompt_tokens합 | output_tokens합 | 평균응답(s, 실호출만) |
| --- | ---: | ---: | ---: | ---: |
| briefing | 2 | 6996 | 938 | 27.24 |
| summary | 212 | 51488 | 21526 | 1.40 |

캐시 반환: 없음

피크 VRAM(GPU 전체, MB): briefing 11573, images 1453, load 1432, render 1434, summary 8257

## 3. 병목 해석

- **웜**: 브리핑(qwen2.5:14b 단일 호출)이 지배적 — 요약은 전부 캐시 반환.
- **콜드**: 요약(EXAONE × 문서수 실호출)이 지배적 — 브리핑은 1회.
- 선행 최적화 대상(무효화 안 됨): num_ctx 적정화(Task 4, 요약 실호출·VRAM), 프롬프트 다이어트(Task 5, 토큰).
- ⚠️ Task 4~5 **채택 판정은 품질 베이스라인(Task 3.2) 확보 후**. 그 전에는 실험·기록만.
