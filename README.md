# Secommenders Backend

Minimal Django backend for publishing Secommenders experiment runs.

## Quick Start

```bash
pip install -r requirements.txt
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_DATABASE=secommenders_backend
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Create the MySQL database first, for example:

```sql
CREATE DATABASE secommenders_backend CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Auth

Set `SECOMMENDER_BACKEND_AUTH_TOKEN` in the environment. The client sends it
through the `Authentication` header.

## API Shape

The backend follows the same resource style as the Legommenders service:

- `GET/POST /evaluations/`
- `GET/DELETE /evaluations/<signature>`
- `GET /evaluations/leaderboard`
- `GET/POST/PUT /experiments/`
- `GET /experiments/<session>`
- `POST /experiments/<session>/register`
- `GET /experiments/log`
- `GET /stats/runtime-hours`

Unlike the reference project, the metadata model is specialized for
Secommenders and stores benchmark-facing fields such as `data_name`,
`model_name`, `task_type`, `repr_type`, `run_id`, and
`compile_prepare_id`.

`/evaluations/leaderboard` is the single ranking export interface now. It
accepts `metric`, `replicate`, `data_name`, `model_name`, `task_type`,
`repr_type`, and `limit`.
