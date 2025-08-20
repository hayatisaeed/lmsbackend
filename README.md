# MentorHub API

Minimal Django/DRF project skeleton.

## How to run

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# start Celery worker (in another terminal)
celery -A config worker -l info
```

Visit [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs) for API docs.
