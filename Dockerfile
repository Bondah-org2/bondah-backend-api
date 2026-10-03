FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements/ requirements/
RUN pip install -r requirements/base.txt

COPY . .

# Static files are baked into the image and served by WhiteNoise.
# Dummy values only satisfy prod.py's required-settings check during the build.
RUN SECRET_KEY=build JWT_SECRET_KEY=build DATABASE_URL=sqlite:////tmp/build.db REDIS_URL=redis://localhost \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 app && chown -R app:app /app \
    && chmod +x docker/entrypoint.sh
USER app

EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["web"]
