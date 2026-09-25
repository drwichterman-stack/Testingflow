import pytest

from clinassess.keystore import KeyStore
from clinassess.service import AppService

PASSWORD = "Correct-Horse-42"


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINASSESS_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def svc(home):
    # Low scrypt cost for test speed only; production uses config.SCRYPT_N.
    ks = KeyStore(home / "keystore.json", scrypt_n=2 ** 12)
    s = AppService(ks, home / "db.enc", home / "audit.log.enc")
    s.setup("drsmith", PASSWORD)
    return s


@pytest.fixture
def client_a(svc):
    return svc.create_client({"last_name": "Doe", "first_name": "Jane", "dob": "2015-03-10",
                              "grade": "5", "flow": "A", "asrs_enabled": False})
