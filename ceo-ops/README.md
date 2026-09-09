# CEO Operations Hub

Public-safe snapshot managed by 지피티비서. Structured local registry is canonical; data/ is its public projection and index.html is a derived view.

Updates: report → source classification → checkpoint validation → registry → public-safe filter → HTML/data → diff → commit/push. No-change commits are prohibited.

Branch: ceo-ops. Scope: ceo-ops/. Main and Pages remain unchanged. No scheduler or Telegram integration is enabled.

Schedule policy: 14:00 MIDDAY_BRIEF / 19:00 EVENING_CHECK / 00:00 MIDNIGHT_WRAP, Asia/Seoul. These are targets, not registered jobs.

## Static snapshot contract

CANONICAL_INTERNAL_STATE → PUBLIC_FILTER → PUBLIC_JSON → HTML_REBUILD → CONSISTENCY_CHECK

STATIC_HTML ≠ LIVE_DATA. JSON updates alone do not update HTML. index.html contains a build-time snapshot, not runtime fetches. All data/*.json files are independently public, whether or not visible in HTML.

Snapshot revision: CEO-OPS-PUBLIC-MINIMIZATION-r2 (publication revision, not a new operational verification timestamp).
Environment and CEO decision cards use minimized public projections; internal evidence remains private. A decision record does not grant execution approval.
