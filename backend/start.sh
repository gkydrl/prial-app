#!/bin/sh
set -e

echo ">>> Pre-flight: Python import kontrolü..." >&2
python -c "
import sys
print(f'Python {sys.version}', flush=True)
try:
    import app.main
    print('Import OK: app.main', flush=True)
except Exception as e:
    print(f'IMPORT HATASI: {e}', flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1

echo ">>> Alembic migration çalıştırılıyor..." >&2
alembic upgrade head 2>&1
echo ">>> Migration tamamlandı." >&2

echo ">>> Sunucu başlatılıyor (port=${PORT:-8000})..." >&2
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
