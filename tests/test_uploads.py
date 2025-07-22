import io
import os
import pytest
from flask_sqlalchemy import query as fsq

import app

class DummyPage:
    def extract_text(self):
        return "text"

class DummyPDF:
    def __init__(self, f):
        pass
    @property
    def pages(self):
        return [DummyPage()]

@pytest.fixture(autouse=True)
def patch_pdf(monkeypatch):
    monkeypatch.setattr(app, "PdfReader", DummyPDF)

@pytest.fixture
def client(tmp_path, monkeypatch):
    app.app.config["TESTING"] = True
    app.app.config["UPLOAD_FOLDER"] = tmp_path
    monkeypatch.setattr(app, "MATCHES_FILE", str(tmp_path / "matches.json"))
    monkeypatch.setattr(app, "JOBS_FILE", str(tmp_path / "jobs.json"))
    with app.app.test_client() as client:
        yield client

def login(client, role="user"):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = role

class DummyUser:
    full_name = "User"
    email = "user@example.com"

@pytest.fixture(autouse=True)
def patch_user(monkeypatch):
    monkeypatch.setattr(fsq.Query, "get", lambda self, ident: DummyUser())


def test_upload_job_pdf(client):
    login(client, role="employer")
    data = {"job_description": (io.BytesIO(b"%PDF-1.4\n"), "job.pdf")}
    resp = client.post("/upload-job", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert b"uploaded successfully" in resp.data.lower()
    assert os.path.exists(os.path.join(app.app.config["UPLOAD_FOLDER"], "job.pdf"))


def test_upload_job_non_pdf(client):
    login(client, role="employer")
    data = {"job_description": (io.BytesIO(b"data"), "job.txt")}
    resp = client.post("/upload-job", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert b"only pdf files are allowed" in resp.data.lower()


def test_upload_resume_pdf(client):
    login(client, role="user")
    data = {
        "resume": (io.BytesIO(b"%PDF-1.4\n"), "resume.pdf"),
        "job_description": (io.BytesIO(b"%PDF-1.4\n"), "desc.pdf"),
    }
    resp = client.post("/upload-resume", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert b"resume matched" in resp.data.lower()


def test_upload_resume_non_pdf(client):
    login(client, role="user")
    data = {
        "resume": (io.BytesIO(b"data"), "resume.txt"),
        "job_description": (io.BytesIO(b"%PDF-1.4\n"), "desc.pdf"),
    }
    resp = client.post("/upload-resume", data=data, content_type="multipart/form-data", follow_redirects=True)
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert (b"only pdf files are allowed" in resp.data.lower()) or any("Only PDF files are allowed" in msg for _cat, msg in flashes)

