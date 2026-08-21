FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/tests ./tests
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/entrypoint.sh ./entrypoint.sh
COPY backend/app/render_supervisor.py ./app/render_supervisor.py
RUN chmod +x ./entrypoint.sh

EXPOSE 8000
CMD ["./entrypoint.sh"]
