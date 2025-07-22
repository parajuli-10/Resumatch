import json
from pathlib import Path

from PyPDF2 import PdfWriter


def create_pdf(path: Path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as f:
        writer.write(f)


def test_user_registration(app_client):
    client, app = app_client
    data = {
        "email": "user@example.com",
        "full_name": "User Example",
        "password": "pass",
        "role": "user",
    }
    response = client.post("/register", data=data, follow_redirects=True)
    assert response.status_code == 200
    with app.app.app_context():
        user = app.User.query.filter_by(email="user@example.com").first()
        assert user is not None


def test_employer_upload_flow(app_client, tmp_path):
    client, app = app_client
    reg = {
        "email": "emp@example.com",
        "full_name": "Employer",
        "password": "pass",
        "role": "employer",
    }
    client.post("/register", data=reg, follow_redirects=True)
    client.post("/login", data={"email": reg["email"], "password": reg["password"]}, follow_redirects=True)

    pdf_path = tmp_path / "job.pdf"
    create_pdf(pdf_path)

    with open(pdf_path, "rb") as f:
        resp = client.post(
            "/upload-job",
            data={"job_description": (f, "job.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200

    uploaded = Path(app.UPLOAD_FOLDER) / "job.pdf"
    assert uploaded.exists()

    with open(app.JOBS_FILE) as jf:
        jobs = json.load(jf)
    assert any(j["job_description"] == "job.pdf" for j in jobs)


def test_resume_matching(app_client, tmp_path):
    client, app = app_client
    reg = {
        "email": "cand@example.com",
        "full_name": "Candidate",
        "password": "pass",
        "role": "user",
    }
    client.post("/register", data=reg, follow_redirects=True)
    client.post("/login", data={"email": reg["email"], "password": reg["password"]}, follow_redirects=True)

    resume_path = tmp_path / "resume.pdf"
    job_path = tmp_path / "job.pdf"
    create_pdf(resume_path)
    create_pdf(job_path)

    class DummyPage:
        def extract_text(self):
            return "dummy"

    class DummyReader:
        def __init__(self, *_args, **_kwargs):
            pass

        @property
        def pages(self):
            return [DummyPage()]

    app.PdfReader = DummyReader

    with open(resume_path, "rb") as rf, open(job_path, "rb") as jf:
        resp = client.post(
            "/upload-resume",
            data={"resume": (rf, "resume.pdf"), "job_description": (jf, "job.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200

    with open(app.MATCHES_FILE) as mf:
        matches = json.load(mf)
    assert any(m["candidate_email"] == reg["email"] for m in matches)


def test_file_download(app_client, tmp_path):
    client, app = app_client
    reg = {
        "email": "emp2@example.com",
        "full_name": "Employer2",
        "password": "pass",
        "role": "employer",
    }
    client.post("/register", data=reg, follow_redirects=True)
    client.post("/login", data={"email": reg["email"], "password": reg["password"]}, follow_redirects=True)

    pdf_path = tmp_path / "job2.pdf"
    create_pdf(pdf_path)
    with open(pdf_path, "rb") as f:
        client.post(
            "/upload-job",
            data={"job_description": (f, "job2.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    resp = client.get("/download-job/job2.pdf")
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type", "").startswith("application/pdf")

    resp2 = client.get("/download-job/missing.pdf")
    assert resp2.status_code == 404
