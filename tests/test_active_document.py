"""
Test active document functionality.
"""
import os
import sys
import pytest
from io import BytesIO

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app as flask_app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_active_document_workflow(client):
    """
    Test the complete active document workflow:
    1. Upload two documents
    2. Set one as active
    3. Ask question without document_id (should use active)
    4. Get active document (should return the set document)
    5. Clear active document
    6. Get active document (should return null)
    """
    # 1. Upload first document
    doc1_content = b"This is the first document about quantum physics."
    doc1_data = {
        "file": (BytesIO(doc1_content), "doc1.txt")
    }
    response1 = client.post(
        "/upload",
        data=doc1_data,
        content_type="multipart/form-data"
    )
    assert response1.status_code == 200
    doc1_id = response1.get_json().get("document_id")
    assert doc1_id is not None

    # 2. Upload second document
    doc2_content = b"This is the second document about machine learning."
    doc2_data = {
        "file": (BytesIO(doc2_content), "doc2.txt")
    }
    response2 = client.post(
        "/upload",
        data=doc2_data,
        content_type="multipart/form-data"
    )
    assert response2.status_code == 200
    doc2_id = response2.get_json().get("document_id")
    assert doc2_id is not None

    # 3. Set doc1 as active
    set_active_response = client.post(
        "/active-document",
        json={"document_id": doc1_id}
    )
    assert set_active_response.status_code == 200
    set_active_json = set_active_response.get_json()
    assert set_active_json["message"] == "Active document set"
    assert set_active_json["document_id"] == doc1_id

    # 4. Get active document (should be doc1)
    get_active_response = client.get("/active-document")
    assert get_active_response.status_code == 200
    active_doc = get_active_response.get_json().get("document_id")
    assert active_doc == doc1_id

    # 5. Ask question without document_id (should auto-use doc1)
    ask_response = client.post(
        "/ask",
        json={"question": "What is this document about?"}
    )
    assert ask_response.status_code == 200
    ask_json = ask_response.get_json()
    assert "answer" in ask_json
    # Verify sources only reference doc1 (if sources exist)
    sources = ask_json.get("sources", [])
    if sources:
        for source in sources:
            if "document_id" in source:
                assert source["document_id"] == doc1_id, \
                    f"Expected doc1 ({doc1_id}), got {source['document_id']}"

    # 6. Clear active document
    clear_response = client.post(
        "/active-document",
        json={"document_id": None}
    )
    assert clear_response.status_code == 200
    clear_json = clear_response.get_json()
    assert clear_json["message"] == "Active document cleared"

    # 7. Get active document (should be null)
    get_cleared_response = client.get("/active-document")
    assert get_cleared_response.status_code == 200
    cleared_active = get_cleared_response.get_json().get("document_id")
    assert cleared_active is None


def test_set_active_document_without_json(client):
    """Test that setting active document requires JSON content type."""
    response = client.post(
        "/active-document",
        data="not json"
    )
    assert response.status_code == 415
    assert "application/json" in response.get_json().get("error", "")


def test_active_document_override(client):
    """
    Test that explicit document_id in /ask overrides active document.
    """
    # 1. Upload two documents
    doc1_content = b"Document one content."
    doc1_data = {"file": (BytesIO(doc1_content), "doc1.txt")}
    response1 = client.post("/upload", data=doc1_data, content_type="multipart/form-data")
    doc1_id = response1.get_json().get("document_id")

    doc2_content = b"Document two content."
    doc2_data = {"file": (BytesIO(doc2_content), "doc2.txt")}
    response2 = client.post("/upload", data=doc2_data, content_type="multipart/form-data")
    doc2_id = response2.get_json().get("document_id")

    # 2. Set doc1 as active
    client.post("/active-document", json={"document_id": doc1_id})

    # 3. Ask with explicit doc2_id (should override active doc1)
    ask_response = client.post(
        "/ask",
        json={"question": "What is this about?", "document_id": doc2_id}
    )
    assert ask_response.status_code == 200
    ask_json = ask_response.get_json()
    
    # Verify sources reference doc2 (if sources exist)
    sources = ask_json.get("sources", [])
    if sources:
        for source in sources:
            if "document_id" in source:
                assert source["document_id"] == doc2_id, \
                    f"Expected doc2 ({doc2_id}), got {source['document_id']}"


def test_get_active_document_when_none_set(client):
    """Test that getting active document returns null when none is set."""
    response = client.get("/active-document")
    assert response.status_code == 200
    active_doc = response.get_json().get("document_id")
    assert active_doc is None
