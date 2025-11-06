#!/bin/sh
set -e

# ensure database schema is up-to-date
flask db upgrade || python -c "from app import init_db; init_db()"

exec "$@"
