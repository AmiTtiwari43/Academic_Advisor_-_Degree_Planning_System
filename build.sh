#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "===> Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements/base.txt

echo "===> Building Frontend SPA..."
cd frontend
npm install
npm run build
cd ..

echo "===> Collecting static files..."
python manage.py collectstatic --noinput

echo "===> Applying database migrations..."
python manage.py migrate

echo "===> Seeding genuine demo data if database is empty..."
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from accounts.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Running seed script...')
    from scripts import seed_genuine_data
    seed_genuine_data.main()
else:
    print('Database already populated.')
" || true

echo "===> Build completed successfully!"
