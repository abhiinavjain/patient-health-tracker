from conftest import PASSWORD

from app.config import Settings
from app.throttle import LoginThrottle


def test_hosted_postgres_urls_get_the_psycopg_driver():
    neon = "postgres://u:p@ep-x.neon.tech/db?sslmode=require"
    assert Settings(database_url=neon).database_url == "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require"
    assert Settings(database_url="postgresql://u:p@h/db").database_url == "postgresql+psycopg://u:p@h/db"
    assert Settings(database_url="sqlite://").database_url == "sqlite://"


def test_throttle_window():
    t = LoginThrottle(max_failures=2, window_seconds=60)
    assert t.retry_after("a") == 0
    t.failure("a"); t.failure("a")
    assert t.retry_after("a") > 0 and t.retry_after("b") == 0
    t.success("a")
    assert t.retry_after("a") == 0


def test_login_locks_out_after_repeated_failures(client, patient):
    def attempt(pw):
        return client.post("/api/v1/auth/login", data={"username": patient.email, "password": pw})

    for _ in range(5):
        assert attempt("wrong-password-xx").status_code == 401
    r = attempt(PASSWORD)  # even the right password is refused during the lockout
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0
    # Unknown accounts are throttled the same way, so a lockout reveals nothing about which emails exist.
    for _ in range(5):
        client.post("/api/v1/auth/login", data={"username": "ghost@test.pht", "password": "x" * 12})
    assert client.post("/api/v1/auth/login", data={"username": "ghost@test.pht", "password": "x" * 12}).status_code == 429


def test_successful_login_resets_failures(client, patient):
    for _ in range(4):
        client.post("/api/v1/auth/login", data={"username": patient.email, "password": "wrong-password-xx"})
    assert client.post("/api/v1/auth/login", data={"username": patient.email, "password": PASSWORD}).status_code == 200
    for _ in range(4):
        client.post("/api/v1/auth/login", data={"username": patient.email, "password": "wrong-password-xx"})
    assert client.post("/api/v1/auth/login", data={"username": patient.email, "password": PASSWORD}).status_code == 200


def test_seed_if_empty_is_idempotent(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import sessionmaker

    from app import seed
    from app.models import User

    eng = create_engine(f"sqlite:///{tmp_path}/s.db")
    monkeypatch.setattr(seed, "engine", eng)
    monkeypatch.setattr(seed, "SessionLocal", sessionmaker(bind=eng, expire_on_commit=False))
    seed.run(3, reset=False, if_empty=True)
    with seed.SessionLocal() as db:
        n = db.scalar(select(func.count()).select_from(User))
    seed.run(3, reset=False, if_empty=True)  # second boot: no-op
    with seed.SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == n
