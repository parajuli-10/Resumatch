import os
import importlib
import pytest

from PyPDF2 import PdfWriter


def create_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as f:
        writer.write(f)


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path/'uploads'))
    monkeypatch.setenv("MATCHES_FILE", str(tmp_path/'matches.json'))
    monkeypatch.setenv("JOBS_FILE", str(tmp_path/'jobs.json'))

    import app
    importlib.reload(app)

    with app.app.app_context():
        app.db.drop_all()
        app.db.create_all()

    client = app.app.test_client()
    return client, app
