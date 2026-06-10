# Secommender Backend

Minimal Django backend for publishing Secommenders experiment runs.

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Auth

Set `SECOMMENDER_BACKEND_AUTH_TOKEN` in the environment. The client sends it
through the `Authentication` header.
