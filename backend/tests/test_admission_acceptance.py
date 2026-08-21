import hashlib
import os
from uuid import uuid4

import httpx
import pytest

from tests.pdf_fixtures import valid_pdf_with_text

BASE_URL = os.environ.get("CORPUS_ACCEPTANCE_API_URL")
pytestmark = pytest.mark.acceptance


def _new_custodian(client: httpx.Client) -> tuple[str, str]:
    response = client.post(
        "/v1/custodians",
        json={"slug": f"acceptance-{uuid4().hex[:12]}", "name": "Admission acceptance"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["custodian"]["id"], body["default_corpus"]["id"]


def _admit(
    client: httpx.Client,
    custodian_id: str,
    corpus_id: str,
    content: bytes,
    request_headers: dict[str, str] | None = None,
):
    return client.post(
        "/v1/admissions",
        files={"file": ("acceptance.pdf", content, "application/pdf")},
        data={
            "custodian_id": custodian_id,
            "corpus_id": corpus_id,
            "arrival_channel": "acceptance-test",
        },
        headers=request_headers,
    )


@pytest.mark.skipif(not BASE_URL, reason="CORPUS_ACCEPTANCE_API_URL is not configured")
def test_live_admission_duplicate_idempotency_isolation_and_queries():
    content = valid_pdf_with_text()
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        custodian_id, corpus_id = _new_custodian(client)
        key = f"admission-{uuid4()}"
        first = _admit(client, custodian_id, corpus_id, content, {"Idempotency-Key": key})
        assert first.status_code == 201, first.text
        first_body = first.json()
        assert first_body["processing_job"]["state"] == "queued"
        assert first_body["idempotent_replay"] is False

        replay = _admit(client, custodian_id, corpus_id, content, {"Idempotency-Key": key})
        assert replay.status_code == 201, replay.text
        replay_body = replay.json()
        assert replay_body["idempotent_replay"] is True
        assert replay_body["arrival"]["id"] == first_body["arrival"]["id"]

        repeated = _admit(client, custodian_id, corpus_id, content)
        assert repeated.status_code == 201, repeated.text
        repeated_body = repeated.json()
        assert repeated_body["exact_duplicate"] is True
        assert repeated_body["source"]["id"] == first_body["source"]["id"]
        assert repeated_body["arrival"]["id"] != first_body["arrival"]["id"]
        assert repeated_body["processing_job"]["id"] == first_body["processing_job"]["id"]

        changed = _admit(client, custodian_id, corpus_id, content + b"x")
        assert changed.status_code == 201, changed.text
        assert changed.json()["source"]["id"] != first_body["source"]["id"]

        listing = client.get(
            "/v1/sources",
            params={"custodian_id": custodian_id, "corpus_id": corpus_id, "limit": 1, "offset": 0},
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 2
        assert len(listing.json()["items"]) == 1
        next_page = client.get(
            "/v1/sources",
            params={"custodian_id": custodian_id, "corpus_id": corpus_id, "limit": 1, "offset": 1},
        )
        assert next_page.status_code == 200
        assert next_page.json()["items"][0]["source"]["id"] != listing.json()["items"][0]["source"]["id"]

        source_id = first_body["source"]["id"]
        detail = client.get(f"/v1/custodians/{custodian_id}/sources/{source_id}")
        assert detail.status_code == 200
        arrivals = client.get(
            f"/v1/sources/{source_id}/arrivals", params={"custodian_id": custodian_id}
        )
        enrollments = client.get(
            f"/v1/sources/{source_id}/enrollments", params={"custodian_id": custodian_id}
        )
        assert arrivals.status_code == 200 and len(arrivals.json()) == 2
        assert enrollments.status_code == 200 and len(enrollments.json()) == 1

        download = client.get(
            f"/v1/custodians/{custodian_id}/sources/{source_id}/canonical"
        )
        assert download.status_code == 200
        assert download.content == content
        assert download.headers["x-content-sha256"] == hashlib.sha256(content).hexdigest()

        other_custodian, other_corpus = _new_custodian(client)
        isolated = _admit(client, other_custodian, other_corpus, content)
        assert isolated.status_code == 201, isolated.text
        isolated_body = isolated.json()
        assert isolated_body["source"]["id"] != source_id
        assert isolated_body["canonical_object"]["storage_key"] != first_body["canonical_object"]["storage_key"]

        mismatch = _admit(client, other_custodian, corpus_id, content)
        assert mismatch.status_code == 409


@pytest.mark.skipif(not BASE_URL, reason="CORPUS_ACCEPTANCE_API_URL is not configured")
def test_live_admission_rejects_non_pdf_without_source():
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        custodian_id, corpus_id = _new_custodian(client)
        response = _admit(client, custodian_id, corpus_id, b"not a PDF")
        assert response.status_code == 400
        listing = client.get(
            "/v1/sources",
            params={"custodian_id": custodian_id, "corpus_id": corpus_id},
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 0
