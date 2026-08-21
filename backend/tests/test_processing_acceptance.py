import os
import time
from uuid import uuid4

import httpx
import pytest

from tests.pdf_fixtures import build_multi_page_pdf

API_URL = os.environ.get("CORPUS_PROCESSING_ACCEPTANCE_API_URL")
pytestmark = pytest.mark.acceptance


def test_running_worker_completes_page_checkpoints_and_exposes_lineage() -> None:
    if not API_URL:
        pytest.skip("CORPUS_PROCESSING_ACCEPTANCE_API_URL is not configured")
    with httpx.Client(base_url=API_URL, timeout=30) as client:
        created = client.post(
            "/v1/custodians",
            json={"slug": f"processing-{uuid4().hex[:12]}", "name": "Processing acceptance"},
        )
        assert created.status_code == 201
        custodian = created.json()["custodian"]
        corpus = created.json()["default_corpus"]
        admission = client.post(
            "/v1/admissions",
            files={"file": ("processing.pdf", build_multi_page_pdf(2), "application/pdf")},
            data={
                "custodian_id": custodian["id"],
                "corpus_id": corpus["id"],
                "arrival_channel": "acceptance",
            },
        )
        assert admission.status_code == 201
        receipt = admission.json()
        job_id = receipt["processing_job"]["id"]
        for _ in range(60):
            job = client.get(f"/v1/processing-jobs/{job_id}", params={"custodian_id": custodian["id"]}).json()
            if job["state"] in {"completed", "partial", "failed"}:
                break
            time.sleep(0.5)
        assert job["state"] == "completed"
        pages = client.get(f"/v1/processing-jobs/{job_id}/pages", params={"custodian_id": custodian["id"]}).json()
        assert len(pages) == 2 and all(page["state"] == "completed" for page in pages)
        representations = client.get(
            f"/v1/sources/{receipt['source']['id']}/representations",
            params={"custodian_id": custodian["id"]},
        ).json()
        assert len(representations) == 4
        assert {item["canonical_object_id"] for item in representations} == {receipt["canonical_object"]["id"]}

        corrupt = client.post(
            "/v1/admissions",
            files={"file": ("corrupt.pdf", b"%PDF-1.4\ncorrupt\n%%EOF", "application/pdf")},
            data={
                "custodian_id": custodian["id"],
                "corpus_id": corpus["id"],
                "arrival_channel": "acceptance",
            },
        )
        assert corrupt.status_code == 201
        corrupt_body = corrupt.json()
        corrupt_job_id = corrupt_body["processing_job"]["id"]
        for _ in range(60):
            corrupt_job = client.get(
                f"/v1/processing-jobs/{corrupt_job_id}", params={"custodian_id": custodian["id"]}
            ).json()
            if corrupt_job["state"] in {"completed", "partial", "failed"}:
                break
            time.sleep(0.5)
        assert corrupt_job["state"] == "failed"
        assert client.get(
            f"/v1/sources/{corrupt_body['source']['id']}", params={"custodian_id": custodian["id"]}
        ).status_code == 200
