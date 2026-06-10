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

## API Shape

The backend follows the same resource style as the Legommenders service:

- `GET/POST /evaluations/`
- `GET/DELETE /evaluations/<signature>`
- `GET /evaluations/export`
- `GET/POST/PUT /experiments/`
- `GET /experiments/<session>`
- `POST /experiments/<session>/register`
- `GET /experiments/log`

Unlike the reference project, the metadata model is specialized for
Secommenders and stores benchmark-facing fields such as `data_name`,
`model_name`, `task_type`, `repr_type`, `run_id`, and
`compile_prepare_id`.
