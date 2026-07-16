#!/bin/sh
# docker-entrypoint.sh
# Runs at container startup before the web server.
# 1. Waits for the database to be ready (important in docker-compose).
# 2. Applies any pending Alembic database migrations.
# 3. Creates the auto-certificate trigger (not managed by Alembic).
# 4. Starts gunicorn with uvicorn workers.

set -e  # Exit immediately if any command fails

echo "==> Waiting for database to be ready..."
# Retry loop: wait up to 60 seconds for MySQL to accept connections.
MAX_TRIES=30
COUNT=0
until python -c "
import os, sys
from sqlalchemy import create_engine, text
url = 'mysql+pymysql://{user}:{pw}@{host}:{port}/{db}'.format(
    user=os.environ.get('DB_USER','root'),
    pw=os.environ.get('DB_PASSWORD','root'),
    host=os.environ.get('DB_HOST','localhost'),
    port=os.environ.get('DB_PORT','3306'),
    db=os.environ.get('DB_NAME','course_platform'),
)
try:
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('DB is ready.')
    sys.exit(0)
except Exception as e:
    print(f'DB not ready: {e}')
    sys.exit(1)
" 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$MAX_TRIES" ]; then
        echo "ERROR: Database did not become ready in time. Check DB_HOST, DB_USER, DB_PASSWORD, DB_NAME."
        exit 1
    fi
    echo "  Attempt $COUNT/$MAX_TRIES — retrying in 2s..."
    sleep 2
done

echo "==> Running Alembic migrations..."
alembic upgrade head

echo "==> Creating MySQL trigger (auto-certificate on course completion)..."
python -c "
import os
from sqlalchemy import create_engine, text
url = 'mysql+pymysql://{user}:{pw}@{host}:{port}/{db}'.format(
    user=os.environ.get('DB_USER','root'),
    pw=os.environ.get('DB_PASSWORD','root'),
    host=os.environ.get('DB_HOST','localhost'),
    port=os.environ.get('DB_PORT','3306'),
    db=os.environ.get('DB_NAME','course_platform'),
)
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text('DROP TRIGGER IF EXISTS after_enrollment_completed'))
    conn.execute(text('''
        CREATE TRIGGER after_enrollment_completed
        AFTER UPDATE ON ENROLLMENT
        FOR EACH ROW
        BEGIN
            IF NEW.CourseStatus = \"Completed\" AND OLD.CourseStatus != \"Completed\" THEN
                INSERT IGNORE INTO CERTIFICATE(StudentID, CourseID, IssueDate)
                VALUES(NEW.StudentID, NEW.CourseID, CURDATE());
            END IF;
        END
    '''))
    conn.commit()
print('Trigger created successfully.')
"

echo "==> Starting LearnArc API..."
# WEB_CONCURRENCY: number of gunicorn worker processes.
# Defaults to 2 if not set by the deployment platform.
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WEB_CONCURRENCY:-2}" \
    --bind "0.0.0.0:8000" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
