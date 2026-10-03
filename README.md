# Bondah Backend API

Django REST API for the Bondah dating app: love seekers, Bondmakers (matchmakers), Bondcoin wallet, chat, feed, live sessions and the admin console.

## Project layout

```
bondah-backend-api/
├── manage.py
├── config/                 Django project: settings, root URLs, WSGI/ASGI, Celery app
│   └── settings/           base.py (shared) · dev.py · prod.py · test.py
├── core/                   Cross-cutting middleware
├── dating/                 The main app
│   ├── models/             Database models, one file per area
│   ├── views/              API views, one file per area (auth, chat, wallet, bondmakers, …)
│   ├── serializers/        DRF serializers, same areas as views/
│   ├── services/           Business logic (matching, wallet, visibility, payments, analytics)
│   ├── integrations/       Third-party wrappers: Brevo, Firebase, Expo, OAuth, liveness, circuit breakers
│   ├── openapi/            API-docs helpers (drf-spectacular schemas and hooks)
│   ├── tests/              Test suite, one file per area
│   ├── management/commands/
│   ├── migrations/
│   ├── tasks.py            Celery tasks (emails, push notifications, scheduled jobs)
│   ├── signals.py
│   └── urls.py             All /api/v1/ routes
├── templates/emails/       Transactional email templates
├── requirements/           base.txt (prod) · dev.txt
├── Dockerfile · docker-compose.yml · docker/entrypoint.sh
├── deploy/nginx/           Host nginx config for the VPS
├── docs/                   api/ · guides/ · deployment.md · archive/
└── archive/                Old one-off scripts, SQL patches and Railway files (not used)
```

`dating/views/__init__.py` and `dating/serializers/__init__.py` re-export everything, so `from dating.views import X` keeps working.

## Local development

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (source venv/bin/activate on Linux/macOS)
pip install -r requirements/dev.txt
cp .env.example .env           # optional for dev; defaults work
python manage.py migrate
python manage.py runserver
```

Dev settings (`config.settings.dev`, the default for `manage.py`) use SQLite and a local Redis at `redis://127.0.0.1:6379/0`. Set `DATABASE_URL` in `.env` to use Postgres.

- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/docs/ · ReDoc: /api/redoc/
- Admin: http://localhost:8000/admin/ (`python manage.py createsuperuser`)

Background jobs need Redis plus:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## Tests

```bash
python manage.py test --settings=config.settings.test
```

The test settings need no Redis or external services.

## Deployment

Production runs on a VPS with Docker Compose (web, Celery worker, Celery beat, Postgres, Redis) behind nginx. See [docs/deployment.md](docs/deployment.md).

## Settings

| Module | Used by |
|---|---|
| `config.settings.dev` | `manage.py`, Celery (default) |
| `config.settings.prod` | `config/wsgi.py`, Docker image |
| `config.settings.test` | the test suite |

All secrets come from environment variables; see [.env.example](.env.example).
