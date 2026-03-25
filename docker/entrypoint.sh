#!/bin/sh
set -e

echo "Running migrations..."
uv run python manage.py migrate --noinput

if [ "$DJANGO_LOAD_TEST_DATA" = "1" ]; then
    echo "Loading initial test data..."
    uv run python manage.py loaddata app/auth/fixtures/initial_test_data.json
fi

echo "Starting server..."
exec "$@"
