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

# Les proves no han de desar res a cap dipòsit de debò (#577).
#
# No n'hi ha prou de treure-les: el **MoviePy** fa `load_dotenv()` quan s'importa
# (`moviepy/config.py:14`) i es carrega el `.env` que troba pujant pel disc — que a la màquina
# d'en Pablo és el del repositori principal, amb les claus de R2 de producció. Com que el
# MoviePy només s'importa quan alguna prova toca vídeo, a partir d'aquell punt la resta de la
# bateria corria amb el dipòsit de debò configurat, i les proves que pugen mitjans fallaven
# segons l'ordre. Costa de veure: per mòduls separats no passa mai.
#
# Posant-les a buit en comptes de treure-les, el `load_dotenv` del MoviePy ja no les toca
# (no sobreescriu el que ja hi ha), i `magatzem` les veu buides i se'n va a Cloudinary.
for _clau in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
    os.environ[_clau] = ""
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


@pytest.fixture(autouse=True)
def _fresh_signup_budget():
    """Signing up and logging in are limited per IP, and every test shares the same one.

    So a test that makes two accounts quietly spends the next test's allowance, and that test
    fails with `KeyError: 'token'` — somewhere else, for something it did not do. It bit
    test_veus the day the practice tests started registering two people, and it depends on the
    order the tests happen to run in, which is random here (pytest-randomly).

    Clearing the counters before each test makes every test start from the same place. The tests
    that are ABOUT the limit fill it up themselves, so they still prove what they prove.
    """
    import main
    main._register_attempts.clear()
    main._login_attempts.clear()
    yield
