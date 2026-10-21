"""Verify initialization in a source copy without workspace fallback dependencies."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / "tmp" / ("clean-setup-" + uuid4().hex[:10])
target.mkdir(parents=True)
for directory in ("procurement", "migrations"):
    shutil.copytree(
        ROOT / directory, target / directory, ignore=shutil.ignore_patterns("__pycache__")
    )
for filename in ("run.py", "alembic.ini"):
    shutil.copy2(ROOT / filename, target / filename)
environment = dict(os.environ)
for key in (
    "PYTHONPATH",
    "DATABASE_URL",
    "DEPLOYMENT",
    "SECRET_KEY",
    "TEST_DATABASE_URL",
    "GEMINI_API_KEY",
    "AI_MODEL",
):
    environment.pop(key, None)
for command in ("migrate", "seed-demo", "migrate"):
    subprocess.run([sys.executable, "run.py", command], cwd=target, env=environment, check=True)
check = """
import json
from pathlib import Path
from run import app
client = app.test_client()
response = client.get('/login')
assert response.status_code == 200
assert b'id="initial-state"' in response.data
manifest = json.loads(Path('procurement/static/app/.vite/manifest.json').read_text(encoding='utf-8'))
entry = manifest['src/main.tsx']
for asset in [entry['file'], *entry.get('css', [])]:
    assert client.get('/static/app/' + asset).status_code == 200
view = client.get('/login', headers={'Accept': 'application/json'}).get_json()
assert view['page'] == 'login' and view['user'] is None
print('Clean source copy: React bootstrap, JS/CSS and JSON view HTTP 200')
"""
subprocess.run([sys.executable, "-c", check], cwd=target, env=environment, check=True)
print("Verified clean source copy:", target)
