"""Offline contract tests. Run: python3 -m unittest -v test_dashboard.py"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent

def records(name):
    return json.loads((ROOT / 'data' / (name + '.json')).read_text())['RECORDS']

class DashboardTests(unittest.TestCase):
    def test_public_safe(self):
        import re
        from html.parser import HTMLParser
        patterns = [r'(?:/Users/|/home/|/private/|/var/|[A-Z]:\\)', r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', r'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|[0-9]{7,}:[A-Za-z0-9_-]{30,})', r'(?i)bearer\s+[A-Za-z0-9._-]{12,}', r'(?i)"(?:password|secret|token|api_key|account|email|pid|db_path|database_path)"\s*:', r'(?i)\.(?:sqlite3?|db)\b']
        class OfflineHTML(HTMLParser):
            def handle_starttag(parser, tag, attrs):
                self.assertNotIn(tag, ('script', 'iframe', 'object', 'embed', 'form'))
                for key, value in attrs:
                    self.assertFalse(key.startswith('on'))
                    if key in ('src', 'href', 'action', 'srcset'):
                        self.assertTrue(value.startswith('#'))
        for p in sorted(ROOT.rglob('*')):
            if p.suffix not in ('.json', '.html'):
                continue
            content = p.read_text()
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, content), str(p.relative_to(ROOT)))
            if p.suffix == '.html':
                OfflineHTML().feed(content)
                self.assertNotIn('url(', content.lower())
                self.assertNotIn('@import', content.lower())

    def test_reproducible_build(self):
        import build_dashboard as build
        self.assertEqual((ROOT / 'index.html').read_text(), build.render(build.load()))
        empty = json.loads((ROOT / 'fixtures' / 'empty.json').read_text())
        self.assertTrue(empty['TEST_ONLY'])
        self.assertEqual((ROOT / 'fixtures' / 'empty.html').read_text(), build.render(empty['DATA']))

    def test_revision_contract(self):
        for p in sorted((ROOT / 'data').glob('*.json')):
            data = json.loads(p.read_text())
            self.assertEqual(data.get('UI_REVISION'), 'CEO-OPS-UI-r3')
            self.assertEqual(data['SNAPSHOT_REVISION'], 'CEO-OPS-PUBLIC-MINIMIZATION-r2')

    def test_upcoming_task_deduplicated(self):
        import build_dashboard as build
        html = build.render(build.load())
        self.assertEqual(html.count('data-task="CEO_R3C"'), 1)
        self.assertIn('N5 r3C 최종 채택 또는 수정 방향', html.split('aria-label="핵심 상태"')[0])

    def test_empty_fixture(self):
        import build_dashboard as build
        data = build.load()
        original = json.dumps(data, ensure_ascii=False, sort_keys=True)
        empty = {key: [] for key in data}
        html = build.render(empty)
        self.assertIn('현재 표시할 항목이 없습니다', html)
        self.assertNotIn('class="project"', html)
        self.assertNotIn('N5 대본', html)
        self.assertEqual(json.dumps(build.load(), ensure_ascii=False, sort_keys=True), original)

    def test_readability(self):
        html = (ROOT / 'index.html').read_text()
        self.assertIn('font:17px/1.55', html)
        self.assertIn('.core p{font-size:16px}', html)

    def test_shared_task_source(self):
        import build_dashboard as build
        data = build.load()
        task = data['ceo_tasks'][0]
        self.assertEqual(set(task.get('PROJECT_IDS', [])), {'SHORTS_PIPELINE', 'STORY_ENGINE'})
        for state in ('ACTION_NOW', 'ACTION_AFTER_PREREQUISITE', 'NO_CEO_ACTION'):
            task['CEO_ACTION_STATE'] = state
            html = build.render(data)
            for ident in task['PROJECT_IDS']:
                self.assertIn('data-project="' + ident + '" data-action="' + state + '"', html)
            if state == 'ACTION_NOW':
                self.assertNotIn('CEO 지금 할 일</h2><p class="answer">없음', html)

    def test_static_render(self):
        html = (ROOT / 'index.html').read_text()
        self.assertIn('<h1>지피티비서 운영 대시보드</h1>', html)
        self.assertIn('snapshot r3', html)
        self.assertIn('CEO 지금 할 일</h2><p class="answer">없음', html)
        self.assertIn('r2 게시 확인 · r3 후보 미게시', html)
        self.assertNotIn('UNKNOWN', html)
        self.assertNotIn('<script', html)
        self.assertEqual(html.count('class="project"'), len(records('projects')))
        self.assertIn('STATIC_HTML != LIVE_DATA', html)
        self.assertIn('정보 확인 시각: 미확인', html)
        for r in records('projects'):
            self.assertIn('data-project="' + r['ID'] + '" data-action="' + r['CEO_ACTION_STATE'] + '"', html)

    def test_action_contract(self):
        projects = records('projects')
        task = records('ceo_tasks')[0]
        story = next(p for p in projects if p['ID'] == 'STORY_ENGINE')
        self.assertEqual(story.get('CEO_ACTION_STATE'), 'ACTION_AFTER_PREREQUISITE')
        for key in ('CEO_ACTION_STATE', 'CEO_ACTION', 'PREREQUISITE'):
            self.assertEqual(task[key], story[key])
        self.assertEqual(story['PREREQUISITE'], 'Telegram TEST_ONLY 운영 E2E 결과 확인')
        self.assertFalse(story['CEO_ACTION_REQUIRED'])
        self.assertEqual(sum(p['CEO_ACTION_STATE'] == 'ACTION_NOW' for p in projects), 0)
        self.assertTrue(all(p['CEO_ACTION_STATE'] in {'ACTION_NOW', 'ACTION_AFTER_PREREQUISITE', 'NO_CEO_ACTION'} for p in projects))

if __name__ == '__main__':
    unittest.main()
