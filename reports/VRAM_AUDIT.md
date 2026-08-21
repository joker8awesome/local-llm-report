# VRAM_AUDIT.md — VRAM 측정 규명 (DEV-05 Task 1)

## 0. 요약 판정

**측정 스코프 오류 + 실제 상주 결함 병존.** 베이스라인 v1의 전 단계 ~11.7GB 균일 수치는 (a) `memory.used`가 **GPU 전체**(Ollama + 데스크톱/브라우저)를 측정했고, (b) 브리핑 모델 `qwen2.5:14b`가 실행 후에도 **언로드되지 않고 상주**(keep_alive)하며 VRAM 압박으로 CPU 오프로딩(15%)까지 발생한 상태가 겹친 결과다.

## 1. 프로세스별 측정 한계 (Windows WDDM)

`nvidia-smi --query-compute-apps=...,used_memory` 의 `used_memory`가 이 환경(Windows WDDM 드라이버)에서 **전부 `[N/A]`** 로 반환된다 — 프로세스별 VRAM 측정은 불가. 따라서 Ollama 점유는 **`ollama ps` + 모델 격리 로드(전/후 총 VRAM 차이)** 로 산출한다.

```
2296, [Insufficient Permissions], [N/A]
3864, C:\Windows\System32\ShellHost.exe, [N/A]
10736, C:\Windows\SystemApps\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\CrossDeviceResume.exe, [N/A]
4544, C:\Windows\explorer.exe, [N/A]
12368, C:\Windows\System32\ApplicationFrameHost.exe, [N/A]
12448, C:\Windows\SystemApps\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\SearchHost.exe, [N/A]
12524, C:\Windows\SystemApps\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\StartMenuExperienceHost.exe, [N/A]
12496, C:\Program Files\WindowsApps\Microsoft.MicrosoftStickyNotes_6.1.4.0_x64__8wekyb3d8bbwe\Microsoft.
```

## 2. 격리 측정 결과 (전체 GPU memory.used 기준)

| 상태 | 총 GPU 사용(MB) | Ollama 점유(추정, MB) |
| --- | ---: | ---: |
| 모델 언로드(데스크톱만) | 1450 | 0 (baseline) |
| EXAONE 3.5 7.8B 단독 | 8242 | **6792** |
| qwen2.5:14b 단독 | 11590 | **10140** |
| 감사 종료(언로드 후) | 1445 | 0 |

- **데스크톱/브라우저 상시 점유(other_used) ≈ 1450 MB** (explorer·Chrome·Edge WebView·NVIDIA Overlay·Docker·Claude 등)
- **실가용 VRAM(데스크톱 제외) ≈ 10832 MB** — 12282이 아니라 이 값이 모델 예산의 상한이다.

## 3. 상주(keep_alive) 결함

- 감사 진입 시 `ollama ps`에 `qwen2.5:14b`가 **`UNTIL 2 hours from now`, `15%/85% CPU/GPU`** 로 상주 중이었다.
- `POST /api/generate {keep_alive:0}` 로 언로드하자 총 VRAM이 **11614 → 1455 MB** 로 급감 → qwen 점유 ≈ 10.1GB 확인.
- **결함 판정:** 브리핑(qwen2.5:14b) 종료 후 모델이 언로드되지 않아 다음 실행의 요약(EXAONE) 구간과 겹칠 위험.
  EXAONE(≈6792MB) + qwen(≈10140MB) = 16932MB 로 **동시 상주는 실가용(10832)을 초과** → 반드시 순차 로드.

## 4. 적용 조치 (결함 수정 — 최적화 성과 아님)

- `pipeline_orchestrator.py`에 **단계 경계 keep_alive:0 언로드** 도입(`UNLOAD_MODELS=1` 기본):
  요약(EXAONE) 종료 → EXAONE 언로드 → 브리핑(qwen) → qwen 언로드. 동시 상주 원천 차단(DEV-03 §0 선행 적용).
- 계측(`metrics.py`)의 VRAM 기록을 `ollama ps` 기반 Ollama 점유로 보강(Task 2와 연계).

## 5. DEV-03 §0 VRAM 예산표 유효성 결론

- 실가용 VRAM은 12GB가 아니라 **≈10832MB**(데스크톱 1450MB 상시 점유). 예산표는 이 값 기준으로 재해석해야 한다.
- `qwen2.5:14b 단독`(예산표 ~9.6GB): 실측 **10140MB** → 실가용에 **근접**(여유 692MB). CPU 오프로딩 발생 관찰 → '단독 ✅'는 성립하나 여유가 거의 없음.
- `EXAONE 단독`(~6GB): 실측 **6792MB** → 여유 충분.
- `EXAONE + faster-whisper 동시상주`: ✅ **GPU 복구됨(DEV-03 Phase 1.0)** — `nvidia-cublas-cu12`+`nvidia-cudnn-cu12` 휠 설치 + DLL 경로 등록으로 GPU 추론 복구(CPU 대비 9.1배). 예산표 원안 성립: EXAONE 6,792MB + Whisper large-v3 int8 ≈2,500MB ≈ **9.3GB ≤ 실가용 10,832MB**. (이전 "CPU 실행/VRAM 0"은 복구 전 상태 — `whisper_gpu_compare.md` 참조)
- `EXAONE + qwen2.5:14b 동시`: 16932MB로 실가용 초과 → **금지, 순차 로드 필수**(조치 §4로 강제).

## 6. 완료 기준 점검
- [x] VRAM_AUDIT.md 산출, 판정 명시(측정오류+상주결함 병존)
- [x] 조치 후 요약 단계 Ollama 점유가 예산표 기대치(EXAONE ≈6GB대)와 부합: 실측 **6792MB**
