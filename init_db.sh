#!/bin/bash

# Initialize and seed database for LMS project

set -e

# Create versions directory for Alembic migrations if it doesn't exist
mkdir -p app/infrastructure/database/migrations/versions

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h ${POSTGRES_SERVER} -p ${POSTGRES_PORT} -U ${POSTGRES_USER}; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Create initial migration
echo "Creating initial migration..."
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
echo "Applying migrations..."
alembic upgrade head

# Seed database with initial data
echo "Seeding database with initial data..."
python -m app.infrastructure.database.seed_data

echo "Database initialization and seeding completed successfully!"
