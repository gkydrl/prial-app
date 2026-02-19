#!/bin/sh
set -e

echo ">>> Alembic migration çalıştırılıyor..."
python -c "
import asyncio
import os
import subprocess
import sys

url = os.getenv('DATABASE_MIGRATION_URL') or os.getenv('DATABASE_URL')
url = url.replace('postgresql+asyncpg://', 'postgresql://')
env = os.environ.copy()
env['DATABASE_MIGRATION_URL'] = url
result = subprocess.run(['alembic', 'upgrade', 'head'], env=env)
sys.exit(result.returncode)
"

echo ">>> Sunucu başlatılıyor..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
