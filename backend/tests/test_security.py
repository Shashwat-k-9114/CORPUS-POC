from fastapi.testclient import TestClient

from app.main import app


def test_health_is_public_but_corpus_api_requires_review_token(monkeypatch):
    monkeypatch.setenv("CORPUS_REVIEW_TOKEN", "review-secret")
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/v1/custodians").status_code == 401
    assert client.get("/v1/custodians", headers={"X-Corpus-Review-Token": "wrong"}).status_code == 401
