release: python manage.py migrate --no-input
web: gunicorn ecoiq.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 300 --log-file -
