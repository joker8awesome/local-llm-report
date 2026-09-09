"""Build the offline r3 candidate from public JSON; no operational actions."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIONS = {'ACTION_NOW': '지금 결정 필요', 'ACTION_AFTER_PREREQUISITE': '선행조건 후 결정', 'NO_CEO_ACTION': '추가 결정 없음'}
LABELS = {'UNKNOWN': '미확인', 'WAITING': '대기', 'READY': '준비 완료', 'PARTIAL': '일부 준비', 'PLANNED': '계획', 'ADOPTED': '채택', 'OBSERVED': '관측됨', 'FACT': '직접 확인 기록', 'MANAGER_REPORTED': '매니저 보고', 'CEO_SCRIPT_APPROVAL': '대본 최종 승인', 'TELEGRAM_OPERATIONAL_E2E_REPORT': 'Telegram 운영 E2E 결과', 'INDEPENDENT_REVIEW_REPORT': '독립 재검수 결과', 'LOCAL_SOURCE_UNAVAILABLE': '원본 접근 불가'}

def text(value):
    if isinstance(value, list):
        return ' · '.join(text(v) for v in value) or '없음'
    value = str(value)
    return escape(LABELS.get(value, value.replace('UNKNOWN', '미확인')))

def load():
    return {p.stem: json.loads(p.read_text())['RECORDS'] for p in sorted((ROOT / 'data').glob('*.json'))}

def evidence(r):
    keys = [('LAST_CONFIRMED_STATE', '마지막 확정 기록'), ('NEXT_ACTION', '기록 당시 다음 행동'), ('CURRENT_ACTIVITY', '현재 활동'), ('BLOCKERS', '제약'), ('SOURCE_TYPE', '근거 종류'), ('SOURCE', '출처'), ('LAST_CONFIRMED_AT', '확정 시각'), ('VERIFIED_AT', '정보 확인 시각'), ('FRESHNESS', '최신성'), ('LOCAL_SOURCE_STATUS', '직접 검증')]
    return '<dl>' + ''.join(f'<dt>{label}</dt><dd>{text(r[key])}</dd>' for key, label in keys if key in r) + '</dl>'

def render(data):
    projects = [dict(p) for p in data['projects']]
    tasks = data['ceo_tasks']
    for task in tasks:
        for p in projects:
            if p['ID'] in task['PROJECT_IDS']:
                p.update({k: task[k] for k in ('CEO_ACTION_STATE', 'CEO_ACTION', 'PREREQUISITE')})
    for p in projects:
        assert p['CEO_ACTION_STATE'] in ACTIONS
    now = [p for p in projects if p['CEO_ACTION_STATE'] == 'ACTION_NOW']
    after = [p for p in projects if p['CEO_ACTION_STATE'] == 'ACTION_AFTER_PREREQUISITE']
    by_id = {p['ID']: p for p in projects}
    def action(p):
        return ACTIONS[p['CEO_ACTION_STATE']] + (' · ' + text(p['CEO_ACTION']) if p['CEO_ACTION_STATE'] != 'NO_CEO_ACTION' else '')
    css = '''
:root{color-scheme:dark;--bg:#101720;--panel:#192432;--line:#34465b;--text:#edf3fa;--muted:#b4c5d8;--mint:#85e2c0;--amber:#ffcf88}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif}main{max-width:1180px;margin:auto;padding:26px 24px 48px}h1{font-size:26px;line-height:1.25;margin:5px 0 12px;letter-spacing:-.7px}h2{font-size:18px;margin:0 0 12px}h3{font-size:17px;margin:0}p{margin:6px 0}.eyebrow,.muted,dt{color:var(--muted)}.eyebrow{font-size:12px;letter-spacing:1px}.meta{font-size:13px;margin-bottom:18px}.pill{display:inline-block;border:1px solid var(--line);border-radius:99px;padding:3px 10px;font-size:12px;color:var(--mint)}.hero{border:1px solid #4c806f;border-radius:14px;background:#172d2b;padding:20px;margin:16px 0}.hero-grid{display:grid;grid-template-columns:1fr 2fr;gap:24px}.hero h2{font-size:14px;color:var(--mint);margin-bottom:6px}.answer{font-size:25px;font-weight:700;line-height:1.3}.next{font-size:18px;font-weight:650}.condition{border-top:1px solid #3b5953;margin-top:14px;padding-top:12px;color:var(--amber)}.core{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0 24px}.core>article,.project,.small{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.core p{font-size:16px}.core h3{font-size:14px;color:var(--muted)}.section-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-top:22px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.project header{display:flex;justify-content:space-between;align-items:start;gap:10px;margin-bottom:12px}.project header .pill{white-space:nowrap}.project dl{display:grid;grid-template-columns:62px 1fr;gap:7px 12px;margin:0}dt,dd{margin:0}dd{overflow-wrap:anywhere}.ceo-after{color:var(--amber)}details{border-top:1px solid var(--line);margin-top:12px;padding-top:10px}summary{cursor:pointer;color:var(--muted);font-size:13px;min-height:28px}summary:focus-visible,a:focus-visible{outline:2px solid var(--mint);outline-offset:4px}details dl{margin-top:12px!important}details p{overflow-wrap:anywhere}.history{margin-top:24px}nav{display:flex;gap:18px;margin-top:14px}a{color:var(--mint);text-decoration:underline;text-underline-offset:4px}.schedule{display:flex;flex-wrap:wrap;gap:10px}.schedule p{padding:10px 14px;border:1px solid var(--line);border-radius:8px}.empty{padding:28px;border:1px dashed var(--line);border-radius:12px;color:var(--muted)}footer{color:var(--muted);font-size:12px;margin-top:28px}.small{margin-top:10px}
@media(max-width:600px){main{padding:18px 16px 32px}h1{font-size:23px}.hero{padding:16px}.hero-grid{grid-template-columns:1fr;gap:14px}.answer{font-size:23px}.next{font-size:17px}.core{grid-template-columns:1fr;gap:8px;margin-bottom:20px}.core>article{padding:10px 13px}.core p{margin:3px 0}.grid{grid-template-columns:1fr}.meta{line-height:1.6}.project{padding:14px}.section-head{margin-top:18px}nav{font-size:14px}.project dl{grid-template-columns:58px 1fr;gap:6px 10px}}
'''
    out = ['<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; connect-src \'none\'; form-action \'none\'; base-uri \'none\'"><meta name="snapshot-revision" content="CEO-OPS-UI-r3"><title>지피티비서 운영 대시보드</title><style>' + css + '</style></head><body><main><header><div class="eyebrow">CEO OPERATIONS · 수동 갱신</div><h1>지피티비서 운영 대시보드</h1><div class="meta"><span class="pill">snapshot r3 · 로컬 후보</span><p>r2 게시 확인 · r3 후보 미게시</p><p class="muted">STATIC_HTML != LIVE_DATA · 실시간 상태 아님<br>정보 확인 시각: 미확인 · 게시 시각과 다릅니다.</p></div></header>']
    out.append('<section class="hero" aria-label="CEO 우선순위"><div class="hero-grid"><div><h2>CEO 지금 할 일</h2><p class="answer">' + ('없음' if not now else text([p['NAME'] + ': ' + p['CEO_ACTION'] for p in now])) + '</p></div><div><h2>다음 확인</h2><p class="next">' + (text(after[0]['PREREQUISITE']) + ' 대기' if after else '새 보고 대기') + '</p></div></div>')
    for task in {t['ID']: t for t in tasks if t['CEO_ACTION_STATE'] == 'ACTION_AFTER_PREREQUISITE'}.values():
        out.append(f'<p class="condition" data-task="{task["ID"]}" data-action="{task["CEO_ACTION_STATE"]}">{text(task["TITLE"])}<br>선행조건 후 결정 · 지금 요청 아님</p>')
    out.append('</section><section class="core" aria-label="핵심 상태">')
    if 'STORY_ENGINE' in by_id and 'SHORTS_PIPELINE' in by_id:
        out.append('<article><h3>N5 대본 · 제작</h3><p>' + text(by_id['STORY_ENGINE']['LAST_CONFIRMED_STATE']).replace('CEO_SCRIPT_APPROVAL=', '승인 ') + '</p><p>' + text(by_id['SHORTS_PIPELINE']['LAST_CONFIRMED_STATE']).replace('PRODUCTION_GATE=', '제작 ') + '</p></article>')
    for ident in ('TELEGRAM_SCRIPT_APPROVAL', 'WINDOWS_ANTI_HALLUCINATION'):
        if ident in by_id:
            p = by_id[ident]
            out.append('<article><h3>' + text(p['NAME']) + '</h3><p>' + text(p['CEO_SUMMARY']) + '</p></article>')
    out.append('</section><nav aria-label="페이지 이동"><a href="#projects">프로젝트</a><a href="#schedule">목표 일정</a><a href="#history">근거·이력</a></nav><section id="projects"><div class="section-head"><h2>프로젝트</h2><span class="muted">' + str(len(projects)) + '개 · 마지막 확인 기준</span></div><div class="grid">')
    if not projects:
        out.append('<p class="empty">현재 표시할 항목이 없습니다</p>')
    for p in projects:
        current_next = p['NEXT_ACTION']
        if p['ID'] == 'CEO_OPERATIONS_DASHBOARD':
            current_next = 'r3 후보 검토 후 별도 게시 승인 대기'
        wait = p['PREREQUISITE'] if p['CEO_ACTION_STATE'] == 'ACTION_AFTER_PREREQUISITE' else p['WAITING_FOR']
        out.append(f'<article class="project" data-project="{p["ID"]}" data-action="{p["CEO_ACTION_STATE"]}"><header><h3>{text(p["NAME"])}</h3><span class="pill">{text(p["STATUS"])}</span></header><dl><dt>담당</dt><dd>{text(p["OWNER"])}</dd><dt>다음</dt><dd>{text(current_next)}</dd><dt>CEO 행동</dt><dd class="{"ceo-after" if p["CEO_ACTION_STATE"] == "ACTION_AFTER_PREREQUISITE" else ""}">{action(p)}</dd><dt>대기</dt><dd>{text(wait)}</dd></dl><details><summary>확정 기록·출처·미확인 항목</summary>{evidence(p)}</details></article>')
    out.append('</div></section><section id="schedule"><div class="section-head"><h2>목표 일정</h2><span class="muted">Asia/Seoul</span></div><p class="muted">계획만 · 자동 실행 비활성 · 다음 실제 실행 없음</p><div class="schedule">')
    schedule_names = {'MIDDAY_BRIEF': '낮 브리프', 'EVENING_CHECK': '저녁 점검', 'MIDNIGHT_WRAP': '하루 마감'}
    for r in data['schedules']:
        assert r['LOCAL_TIME'] in ('14:00', '19:00', '00:00') and r['TIMEZONE'] == 'Asia/Seoul'
        assert r['STATUS'] == 'PLANNED' and not any(r[k] for k in ('ENABLED', 'AUTO_EXECUTION', 'PROACTIVE_NOTIFICATION'))
        out.append('<p><strong>' + text(r['LOCAL_TIME']) + '</strong> ' + schedule_names[r['ID']] + ' · 계획 / 비활성</p>')
    out.append('</div></section><section id="history" class="history"><h2>근거·이력</h2><p class="muted">기록 당시 상태입니다. 과거 게시 준비·미승인 문구는 현재 게시 상태가 아닙니다.</p>')
    for title, key in [('AI 팀 · 운영 주체', 'systems'), ('체크포인트 이력', 'checkpoints'), ('채택 결정 이력', 'decisions'), ('환경 기록', 'environments')]:
        out.append('<details><summary>' + title + '</summary>')
        for r in data[key]:
            out.append('<article class="small"><h3>' + text(r['NAME']) + '</h3>' + evidence(r) + '</article>')
        out.append('</details>')
    out.append('<details><summary>결정 경계 · 정보 최신성 · 게시 확인</summary><p>r2 공개 페이지의 snapshot 식별자를 직접 확인했습니다. r3는 이 로컬 후보이며 게시하지 않았습니다.</p><p>snapshot r3는 UI 개정 번호이며 운영 정보의 재검증·게시 시각이 아닙니다. 매니저 보고의 정확한 확정 시각과 현재 작업은 미확인입니다. 보고 대기는 실패 판정이 아닙니다.</p>')
    for task in tasks:
        out.append('<p>' + text(task['TITLE']) + ' · ' + ACTIONS[task['CEO_ACTION_STATE']] + '</p><p>' + text(task['APPROVAL_BOUNDARY']) + '</p>')
    out.append('</details></section><footer>공개 JSON → 정적 HTML · JSON 변경 후 다시 빌드해야 반영됩니다.<br>자동 보고·실행·승인 기능 없음. 준비 검증과 운영 E2E 성공은 다릅니다.</footer></main></body></html>')
    return '\n'.join(out)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--empty-fixture', action='store_true')
    args = parser.parse_args()
    data = load()
    if args.empty_fixture:
        fixture = json.loads((ROOT / 'fixtures' / 'empty.json').read_text())
        assert fixture['TEST_ONLY'] is True
        data = fixture['DATA']
        target = ROOT / 'fixtures' / 'empty.html'
    else:
        target = ROOT / 'index.html'
    target.write_text(render(data))
    print('Built ' + target.name + ' (r3 candidate, offline)')
