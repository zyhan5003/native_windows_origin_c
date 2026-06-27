from __future__ import annotations

from datetime import UTC, datetime

from screen_windows.security.auth import TokenManager, TokenStore


def test_issue_and_verify_token_success() -> None:
    manager = TokenManager("123456", ttl_seconds=3600)
    session = manager.issue_token("123456")
    timestamp = int(datetime.now(UTC).timestamp())
    signature = manager.build_hmac(session.token, timestamp)

    assert manager.verify_token(session.token, timestamp, signature) is True


def test_issue_token_rejects_wrong_pin() -> None:
    manager = TokenManager("123456")

    try:
        manager.issue_token("000000")
    except ValueError as error:
        assert "invalid pin" in str(error)
    else:
        raise AssertionError("expected invalid pin")


def test_verify_token_rejects_expired_timestamp() -> None:
    manager = TokenManager("123456", ttl_seconds=3600)
    session = manager.issue_token("123456")
    timestamp = int(datetime.now(UTC).timestamp()) - 301
    signature = manager.build_hmac(session.token, timestamp)

    assert manager.verify_token(session.token, timestamp, signature) is False


def test_token_store_persists_hash_for_restart(tmp_path) -> None:
    store_path = tmp_path / "tokens.json"
    manager = TokenManager(
        "123456",
        ttl_seconds=3600,
        token_store=TokenStore(store_path),
    )
    session = manager.issue_token("123456")
    timestamp = int(datetime.now(UTC).timestamp())
    signature = manager.build_hmac(session.token, timestamp)

    restarted = TokenManager(
        "123456",
        ttl_seconds=3600,
        token_store=TokenStore(store_path),
    )

    assert session.token not in store_path.read_text(encoding="utf-8")
    assert restarted.verify_token(session.token, timestamp, signature) is True
