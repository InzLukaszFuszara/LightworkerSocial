#!/bin/sh
# Start the web server. Migrations run first unless RUN_MIGRATIONS=0
# (e.g. when they are configured as Railway's pre-deploy command).
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

exec gunicorn config.wsgi:application
