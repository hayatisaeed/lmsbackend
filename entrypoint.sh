#!/bin/bash
set -e

# Function to wait for database
wait_for_db() {
    echo "Waiting for database..."
    while ! nc -z $DB_HOST $DB_PORT; do
        sleep 1
    done
    echo "Database is ready!"
}

# Wait for database if needed
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
    wait_for_db
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Import locations (only if not already imported or in production)
if [ "$DJANGO_ENV" = "production" ]; then
    echo "Importing locations..."
    python manage.py import_locations --skip-existing
else
    echo "Importing locations (development)..."
    python manage.py import_locations
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Execute the main command
exec "$@"