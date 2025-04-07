#!/bin/bash

set -e

echo "⏳ Waiting for PostgreSQL at $POSTGRES_SERVER:$POSTGRES_PORT..."
until pg_isready -h "$POSTGRES_SERVER" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 1
done
echo "✅ PostgreSQL is ready!"

echo "📦 Running Alembic migrations..."
alembic upgrade head

echo "🚀 Starting backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
