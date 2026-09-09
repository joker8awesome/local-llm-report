# CEO Operations Hub

Public-safe snapshot managed by 지피티비서. Structured local registry is canonical; data/ is its public projection and index.html is a derived view.

Updates: report → source classification → checkpoint validation → registry → public-safe filter → HTML/data → diff → commit/push. No-change commits are prohibited.

Branch: ceo-ops. Scope: ceo-ops/. Main and Pages remain unchanged. No scheduler or Telegram integration is enabled.

Schedule policy: 14:00 MIDDAY_BRIEF / 19:00 EVENING_CHECK / 00:00 MIDNIGHT_WRAP, Asia/Seoul. These are targets, not registered jobs.

## Static snapshot contract

CANONICAL_INTERNAL_STATE → PUBLIC_FILTER → PUBLIC_JSON → HTML_REBUILD → CONSISTENCY_CHECK

STATIC_HTML ≠ LIVE_DATA. JSON updates alone do not update HTML. index.html contains a build-time snapshot, not runtime fetches. All data/*.json files are independently public, whether or not visible in HTML.

Data baseline SNAPSHOT_REVISION: CEO-OPS-PUBLIC-MINIMIZATION-r2. UI_REVISION: CEO-OPS-UI-r3 in every public data file and HTML meta snapshot-revision. Neither is a new operational verification timestamp. The r2 public page was read back; this r3 candidate is not published. N5 action timing is the explicitly authorized correction, not a new approval.
Environment and CEO decision cards use minimized public projections; internal evidence remains private. A decision record does not grant execution approval.

## Reproduce r3 QA

```sh
PYTHONDONTWRITEBYTECODE=1 python3 build_dashboard.py
PYTHONDONTWRITEBYTECODE=1 python3 build_dashboard.py --empty-fixture
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_dashboard.py
python3 -m http.server 8767 --bind 127.0.0.1
```

Inspect `/` and `/fixtures/empty.html` at 390×900 and 1440×1000 in the local server. The empty fixture is TEST_ONLY; it never edits data/. Screenshots and measured results: qa/.

CEO task fields CEO_ACTION_STATE / CEO_ACTION / PREREQUISITE are joined through PROJECT_IDS to both N5 project cards. Top decisions are deduplicated by task ID. Supported states: ACTION_NOW, ACTION_AFTER_PREREQUISITE, NO_CEO_ACTION. Project public projections mirror those fields; the builder uses the task as the authoritative action source.

Keep old checkpoints in collapsed, explicitly historical details. Do not replace operational confirmation times with build or publication times. No runtime fetch, external asset, JavaScript, scheduler, notification, or approval action is included.
