#!/bin/sh
set -e

echo ">>> Alembic migration çalıştırılıyor..."
alembic upgrade head

echo ">>> Sunucu başlatılıyor..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
