#!/bin/bash
set -e

echo "=========================================="
echo "SGDI Backend - Starting..."
echo "=========================================="

# Wait for database
echo "Waiting for database..."
python -c "
import time
import psycopg2
from urllib.parse import urlparse
import os

db_url = os.getenv('DATABASE_URL', 'postgresql://sgdi_user:sgdi_password@db:5432/sgdi_db')
parsed = urlparse(db_url)

for i in range(30):
    try:
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432
        )
        conn.close()
        print('Database is ready!')
        break
    except Exception as e:
        if i == 29:
            print(f'Database not ready after 30 attempts: {e}')
            exit(1)
        print(f'Waiting for database... ({i+1}/30)')
        time.sleep(1)
"

# Run database initialization
echo "Running database initialization..."
python seed_admin.py

# Verify CORS configuration
echo "Verifying CORS configuration..."
python -c "
from app.main import app
cors_found = False
for middleware in app.user_middleware:
    if 'CORS' in str(type(middleware.cls)):
        cors_found = True
        print('✅ CORS Middleware found and configured')
        print(f'   Origins: {middleware.kwargs.get(\"allow_origins\", [])}')
        print(f'   Methods: {middleware.kwargs.get(\"allow_methods\", [])}')
        break
if not cors_found:
    print('❌ WARNING: CORS Middleware NOT found!')
    exit(1)
"

echo "Seeding completed successfully!"
echo "Starting application..."

# Start uvicorn with proper settings
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --access-log \
    --no-use-colors

