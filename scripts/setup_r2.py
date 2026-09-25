#!/usr/bin/env python3
"""R2 저장소를 명령 한 줄로 준비한다 — python3 scripts/setup_r2.py <버킷이름> [--prefix episodes]
   1) 로그인 확인(npx wrangler whoami)  2) 버킷 생성  3) r2.dev 공개 주소 켜기  4) kit.config.json 의 storage 칸 기입.
   사람이 미리 할 것: Cloudflare 가입(https://dash.cloudflare.com/sign-up) 후 `npx wrangler login` (브라우저에서 Allow)."""
import json, os, re, subprocess, sys
ROOT = os.environ.get('ALLIRANG_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if not args: sys.exit('사용법: python3 scripts/setup_r2.py <버킷이름> [--prefix episodes]')
name = args[0]; prefix = sys.argv[sys.argv.index('--prefix') + 1] if '--prefix' in sys.argv else 'episodes'
def w(*a):
    r = subprocess.run(['npx', 'wrangler', *a], capture_output=True, text=True); return r.returncode, r.stdout + r.stderr
rc, out = w('whoami')
if rc or 'You are not authenticated' in out or 'not logged in' in out.lower():
    sys.exit('wrangler 로그인이 안 돼 있다 → 먼저 `npx wrangler login` 을 실행하고(브라우저에서 Allow) 다시 돌려라')
rc, out = w('r2', 'bucket', 'create', name)
if rc and 'already exists' not in out: sys.exit('버킷 생성 실패:\n' + out[-800:])
print(f'버킷 {name}: ' + ('이미 있음' if rc else '생성됨'))
rc, out = w('r2', 'bucket', 'dev-url', 'enable', name, '-y')
m = re.search(r'https://pub-[a-z0-9]+\.r2\.dev', out)
if not m:
    rc, out = w('r2', 'bucket', 'dev-url', 'get', name); m = re.search(r'https://pub-[a-z0-9]+\.r2\.dev', out)
if not m: sys.exit('공개 주소를 못 켰다 — 대시보드에서 버킷 → Settings → Public access → R2.dev subdomain → Allow Access 를 손으로:\n' + out[-600:])
url = m.group(0); print(f'공개 주소: {url}')
p = os.path.join(ROOT, 'kit.config.json'); cfg = json.load(open(p)) if os.path.exists(p) else {}
cfg['storage'] = {'r2_bucket': name, 'r2_prefix': prefix, 'media_base_url': f'{url}/{prefix}'}
json.dump(cfg, open(p, 'w'), ensure_ascii=False, indent=2)
print(f'kit.config.json storage 기입 완료 → r2_bucket={name} · media_base_url={url}/{prefix}')
