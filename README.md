# Secommenders Backend

Minimal Django backend for publishing Secommenders experiment runs.

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Create `mysql.local.conf` in the repo root:

```ini
[client]
host = localhost
port = 3306
database = secommenders_backend
user = root
password = your_password
default-character-set = utf8mb4
```

Then create the MySQL database, for example:

```sql
CREATE DATABASE secommenders_backend CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Auth

The backend reads the expected auth token from the `config_configentry` table
with key `auth`.

You can initialize it with Django shell:

```bash
python manage.py shell -c "from config.models import ConfigEntry; ConfigEntry.set('auth', 'your_token')"
```

The client still sends that token through the `Authentication` header.

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
