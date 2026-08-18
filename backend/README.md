# Corpus backend

FastAPI application. See root `../PROJECT.md`, `../DECISIONS.md`, `../REQUIREMENTS.md`
for product/architecture context, and `../BUILD_LOG.md` for current implementation
status.

## Setup

```
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

## Run (development)

```
uvicorn app.main:app --reload
```

Serves on `http://127.0.0.1:8000`. Interactive API docs at `/docs`.

## Test

```
pytest
```
