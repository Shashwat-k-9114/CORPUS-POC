from fastapi.testclient import TestClient

from app.main import app


def test_health_is_public_but_corpus_api_requires_review_token(monkeypatch):
    monkeypatch.setenv("CORPUS_REVIEW_TOKEN", "review-secret")
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/v1/custodians").status_code == 401
    assert client.get("/v1/custodians", headers={"X-Corpus-Review-Token": "wrong"}).status_code == 401


def test_review_token_errors_preserve_allowed_cors_origin(monkeypatch):
    monkeypatch.setenv("CORPUS_REVIEW_TOKEN", "review-secret")
    client = TestClient(app)

    response = client.get(
        "/v1/custodians",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_does_not_require_review_token(monkeypatch):
    monkeypatch.setenv("CORPUS_REVIEW_TOKEN", "review-secret")
    client = TestClient(app)

    response = client.options(
        "/v1/custodians",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "accept,x-corpus-review-token",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
