#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for i in range(60):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as exc:
        print(f"  retry {i+1}/60: {exc}")
        time.sleep(2)
else:
    raise SystemExit("Database not reachable")
PY

echo "Running migrations..."
alembic upgrade head

case "$1" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    exec python scripts/run_worker.py --interval "${WORKER_POLL_SECONDS:-15}"
    ;;
  *)
    exec "$@"
    ;;
esac
