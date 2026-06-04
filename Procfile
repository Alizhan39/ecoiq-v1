release: python manage.py migrate --no-input
web: gunicorn ecoiq.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --worker-class gthread --threads 4 --timeout 120 --max-requests 300 --max-requests-jitter 50 --log-file -
