"""Every test module must see the SAME isolated database. test_api.py sets DATABASE_URL before
importing main, but pytest imports modules alphabetically at collection, and a module that does
`import main` before test_api (test_align_known, test_chorus_dedupe, …) would bind main to the
developer's real drills.db. Set the environment here, once, before any collection."""
import os
import sys

TEST_DB = "test_drills.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB}"
os.environ.pop("CHECK_SCHEMA", None)
os.environ.pop("API_KEY", None)
os.environ.setdefault("LEXICON_WARMUP", "0")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _client_identity():
    """Every real client carries an identity: the app registers a token on first use, even for
    somebody who never signs up, and adding to the library now asks for one. The shared test
    client carries one too — made HERE, after collection, because opening the database while the
    modules are still being imported leaves the file locked on Windows. The tests that check what
    a stranger may do clear the header on purpose."""
    from test_api import client
    r = client.post("/users/register", json={"username": "test_contributor"})
    if r.status_code == 200:
        client.headers.update({"X-User-Token": r.json()["token"]})
    yield
