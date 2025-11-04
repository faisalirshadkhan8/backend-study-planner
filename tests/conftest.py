import os
import io
import sys
import pytest

# Ensure test mode
os.environ.setdefault("DEBUG", "false")

# Guarantee the backend directory (parent of tests) is on sys.path so `import app` works
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app  # noqa: E402

@pytest.fixture(scope="session")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

@pytest.fixture
def sample_text_file():
    return (io.BytesIO(b"Sample content about backend testing and retrieval."), "test_doc.txt")
