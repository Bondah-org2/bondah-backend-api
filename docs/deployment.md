# Deploying to a VPS

The production stack runs with Docker Compose on one server:

| Service | What it does |
|---|---|
| `web` | Gunicorn serving the API on `127.0.0.1:8000`. Runs migrations on start. |
| `worker` | Celery worker: emails, push notifications |
| `beat` | Celery beat: nightly visibility expiry, hourly underage-account cleanup |
| `db` | PostgreSQL 16 (data in the `postgres_data` volume) |
| `redis` | Redis 7: cache and Celery broker |

nginx on the host terminates TLS (Let's Encrypt via certbot) and proxies to `web`.

## 1. Prepare the server (Ubuntu 22.04/24.04)

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER     # log out and back in
```

Point your API domain's DNS A record (e.g. `api.bondah.org`) at the server IP.

## 2. Get the code and configure

```bash
git clone https://github.com/Bondah-org2/bondah-backend-api.git
cd bondah-backend-api
cp .env.example .env
nano .env        # set SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS, keys…
```

Secret files (Firebase service account, Google Play key) go in a `secrets/` folder (git-ignored). Mount them by adding them to `docker-compose.yml`, or put the Firebase JSON in `FIREBASE_CREDENTIALS_JSON`.

## 3. Start the stack

```bash
docker compose up -d --build
docker compose ps                 # all services should be healthy/running
docker compose logs -f web
docker compose exec web python manage.py createsuperuser
```

## 4. nginx + HTTPS

```bash
sudo cp deploy/nginx/bondah.conf /etc/nginx/sites-available/bondah
sudo sed -i 's/api.bondah.org/YOUR_DOMAIN/' /etc/nginx/sites-available/bondah
sudo ln -s /etc/nginx/sites-available/bondah /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

Check: `curl https://YOUR_DOMAIN/health/`

## Updating

```bash
git pull
docker compose up -d --build      # migrations run automatically when web starts
```

## Moving data from the old (Railway) database

```bash
pg_dump --no-owner --no-acl "$OLD_DATABASE_URL" > bondah.sql
docker compose exec -T db psql -U bondah -d bondah < bondah.sql
```

Do this before the first `docker compose up` of `web`, or on an empty database.

## Backups

```bash
docker compose exec -T db pg_dump -U bondah bondah | gzip > backup-$(date +%F).sql.gz
```

Schedule it with cron and copy the files off the server.
