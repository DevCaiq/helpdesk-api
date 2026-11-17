FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.8
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN SECRET_KEY=build-only-placeholder-not-used-at-runtime-0123456789 \
    DATABASE_URL=postgres://build:build@localhost/build \
    uv run --no-sync manage.py collectstatic --noinput --settings=config.settings.prod
RUN useradd --create-home app && mkdir /data && chown app:app /data
USER app
EXPOSE 8000
CMD ["/app/.venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]
