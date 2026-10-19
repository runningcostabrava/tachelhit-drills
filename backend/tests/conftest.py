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
