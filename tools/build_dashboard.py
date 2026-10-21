"""김해공장 대시보드를 비밀번호로 잠긴 단일 HTML로 만든다.
사용법: python3 build_dashboard.py --page index.html --d3 d3.min.js --snapshot 2026-10-21 --password '...' --out index.html \
        --data transactions=t.json --data status=s.json --data price_changes=p.json --data ai_report=a.json --data market=m.json
"""
import json, re, sys, argparse
ap = argparse.ArgumentParser()
ap.add_argument('--page', required=True); ap.add_argument('--d3', required=True)
ap.add_argument('--snapshot', required=True); ap.add_argument('--password', required=True)
ap.add_argument('--out', required=True); ap.add_argument('--data', action='append', default=[])
A = ap.parse_args()
page = open(A.page, encoding='utf8').read()
d3 = open(A.d3, encoding='utf8').read()
data = {k: json.load(open(v, encoding='utf8')) for k, v in (x.split('=', 1) for x in A.data)}
for need in ['transactions', 'status', 'price_changes', 'ai_report', 'market']:
    if need not in data: sys.exit('missing --data ' + need)
snapshot = A.snapshot
password = A.password

style = re.search(r'<style>(.*?)</style>', page, re.S).group(1)
body = re.sub(r'<style>.*?</style>', '', page, count=1, flags=re.S)
# separate markup and scripts
scripts = re.findall(r'<script>(.*?)</script>', body, re.S)
markup = re.sub(r'<script>.*?</script>', '', body, flags=re.S).strip()

tokens = '''
:root {
  --color-bg: #f6f7f9; --color-panel: #ffffff; --color-fg: #1b1f27; --color-fg-muted: #5d6573;
  --color-border-line: #dfe3ea; --color-ok: #1f7a4d; --color-warn: #a35a00; --color-bad: #c0392b;
  --cds-chart-grid: #eceff4; --cds-chart-axis: #b9c0cc; --cds-chart-reference: #8a93a3; --cds-chart-muted: #9aa3b2;
  --cds-surface-popover: #ffffff; --cds-border: #dfe3ea; --cds-shadow-popover: 0 6px 20px rgba(20,30,50,.12); --cds-text-secondary: #5d6573;
  --cds-radius: 10px; --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 14px; --cds-gap-lg: 22px; --cds-gap-xl: 32px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 14px; --cds-pad-lg: 20px; --cds-pad-xl: 28px;
  --cds-font-size-caption: 12.5px; --cds-font-size-body: 14.5px; --cds-font-size-heading: 17px; --cds-font-size-title: 30px;
  --cds-font-weight-medium: 600; --cds-dur-slow: .3s; --cds-ease-out: cubic-bezier(.2,.7,.2,1);
  --font-anthropic-sans: "Noto Sans KR", "Malgun Gothic", "Apple SD Gothic Neo", system-ui, sans-serif;
  --font-anthropic-serif: "Noto Serif KR", "Batang", Georgia, serif;
  --dash-gutter: clamp(16px, 4vw, 40px);
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #12151b; --color-panel: #1a1e26; --color-fg: #e8ebf0; --color-fg-muted: #a3abb8;
    --color-border-line: #2c323d; --color-ok: #4cc38a; --color-warn: #e0a24a; --color-bad: #ef6b5b;
    --cds-chart-grid: #232833; --cds-chart-axis: #3a4250; --cds-chart-reference: #6d7686; --cds-chart-muted: #6d7686;
    --cds-surface-popover: #222733; --cds-border: #333a47; --cds-shadow-popover: 0 6px 20px rgba(0,0,0,.4); --cds-text-secondary: #a3abb8;
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; }
body { background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); font-size: var(--cds-font-size-body); }
#dash-root { max-width: 1400px; margin: 0 auto; padding: 24px var(--dash-gutter) 48px; }
.snap { max-width: 1400px; margin: 0 auto; padding: 10px var(--dash-gutter) 0; color: var(--color-fg-muted); font-size: 12px; }
.dash-skeleton { color: transparent !important; background: var(--cds-chart-grid); border-radius: 6px; }
a { color: inherit; }
[hidden] { display: none !important; }
'''

colors_light = ['#2f6fdb', '#e07b39', '#2a9d8f', '#8e5bd6', '#d1495b', '#5c8a2e', '#b58b00', '#4a5568']
shim = r'''
(function () {
  const RAW = window.__DATA__;
  const calcs = {}; const cache = {};
  let params = { item: '전체' };
  const subs = [];
  function compute(id) {
    if (id in cache) return cache[id];
    if (RAW[id]) return (cache[id] = RAW[id]);
    const c = calcs[id]; if (!c) return null;
    const args = c.inputs.map((i) => compute(i));
    return (cache[id] = c.fn(...args));
  }
  function data(id) {
    const d = compute(id);
    if (d == null) return { status: 'missing', data: [], rows: [], columns: [], meta: [] };
    const columns = Array.isArray(d) && d[0] ? Object.keys(d[0]) : [];
    return { status: 'ok', data: d, rows: d, columns, meta: [], refreshing: false };
  }
  function fire() { subs.forEach((f) => { try { f(); } catch (e) { console.error(e); } }); }
  let w = window.innerWidth; let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => { if (window.innerWidth !== w) { w = window.innerWidth; fire(); } }, 150); });
  window.dash = {
    calc: (id, o) => { calcs[id] = o; },
    loader: () => {},
    data,
    onData: (f) => { subs.push(f); f(); },
    params: () => ({ ...params }),
    setParams: (p) => { params = { ...params, ...p }; fire(); },
    resetParams: () => { params = { item: '전체' }; fire(); },
    setLink: (name) => { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
    refresh: () => {},
    colors: COLORS,
  };
})();
'''.replace('COLORS', json.dumps(colors_light))


import os, base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
ITER = 600000
salt = os.urandom(16); iv = os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(password.encode('utf8'))
payload = json.dumps({'data': data, 'markup': markup, 'scripts': [shim] + scripts}, ensure_ascii=False).encode('utf8')
ct = AESGCM(key).encrypt(iv, payload, None)
b64 = lambda b: base64.b64encode(b).decode()
gate_css = """
.gate { min-height: 100vh; display: grid; place-items: center; padding: 24px var(--dash-gutter); }
.gate-box { width: min(100%, 380px); background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: 14px; padding: 28px 24px; display: grid; gap: 14px; box-shadow: 0 10px 30px rgba(20,30,50,.08); }
.gate-box h1 { margin: 0; font-family: var(--font-anthropic-serif); font-weight: 400; font-size: 24px; line-height: 1.3; word-break: keep-all; }
.gate-box p { margin: 0; color: var(--color-fg-muted); font-size: 14px; line-height: 1.6; word-break: keep-all; }
.gate-box input { font: inherit; font-size: 17px; padding: 12px 14px; border: 1px solid var(--color-border-line); border-radius: 10px; background: var(--color-bg); color: var(--color-fg); width: 100%; }
.gate-box input:focus-visible { outline: 2px solid var(--color-fg); outline-offset: 1px; }
.gate-box button { font: inherit; font-weight: 700; font-size: 16px; padding: 12px; border-radius: 10px; border: 0; background: #111; color: #fff; cursor: pointer; }
.gate-box button:disabled { opacity: .6; cursor: default; }
.gate-err { color: var(--color-bad) !important; min-height: 1.4em; }
"""
gate_js = """
(function () {
  const P = { salt: '%s', iv: '%s', ct: '%s', iter: %d };
  const $ = (id) => document.getElementById(id);
  const b = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  async function open() {
    const pw = $('gate-pw').value; if (!pw) return;
    $('gate-go').disabled = true; $('gate-err').textContent = '확인 중…';
    try {
      if (!window.crypto || !crypto.subtle) throw new Error('nocrypto');
      const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
      const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: b(P.salt), iterations: P.iter, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
      const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b(P.iv) }, key, b(P.ct));
      const app = JSON.parse(new TextDecoder().decode(plain));
      window.__DATA__ = app.data;
      $('dash-root').innerHTML = app.markup;
      $('gate').remove(); $('app').hidden = false;
      for (const code of app.scripts) { const s = document.createElement('script'); s.textContent = code; document.body.appendChild(s); }
    } catch (e) {
      $('gate-go').disabled = false;
      $('gate-err').textContent = e && e.message === 'nocrypto' ? '이 브라우저에서는 열 수 없습니다. 크롬이나 사파리로 열어 주세요.' : '비밀번호가 맞지 않습니다.';
      $('gate-pw').select();
    }
  }
  $('gate-go').addEventListener('click', open);
  $('gate-pw').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.isComposing) open(); });
})();
""" % (b64(salt), b64(iv), b64(ct), ITER)

html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>함안자원 김해공장 AI 데이터 자동화</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@400;600&display=swap">
<style>{tokens}
{style}
{gate_css}</style>
</head>
<body>
<div class="gate" id="gate">
  <div class="gate-box">
    <h1>함안자원 김해공장<br>AI 데이터 자동화</h1>
    <p>임직원 전용 페이지입니다. 비밀번호를 입력해 주세요.</p>
    <input id="gate-pw" type="password" autocomplete="current-password" aria-label="비밀번호" placeholder="비밀번호">
    <button id="gate-go" type="button">열기</button>
    <p class="gate-err" id="gate-err" aria-live="polite"></p>
  </div>
</div>
<div id="app" hidden>
<div class="snap">{snapshot} 기준</div>
<div id="dash-root"></div>
</div>
<script>{d3}</script>
<script>{gate_js}</script>
</body>
</html>
"""
out = A.out
open(out, 'w', encoding='utf8').write(html)
print(len(html.encode('utf8')))
