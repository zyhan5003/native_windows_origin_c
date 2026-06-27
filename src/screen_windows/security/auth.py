from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
from pathlib import Path
import secrets
from typing import Any


@dataclass(frozen=True, slots=True)
class AuthSession:
    token: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class StoredAuthSession:
    token_hash: str
    issued_at: datetime
    expires_at: datetime


class TokenStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> dict[str, StoredAuthSession]:
        if not self._path.exists():
            return {}
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        sessions: dict[str, StoredAuthSession] = {}
        for item in raw.get("sessions", []):
            session = StoredAuthSession(
                token_hash=str(item["token_hash"]),
                issued_at=datetime.fromisoformat(str(item["issued_at"])),
                expires_at=datetime.fromisoformat(str(item["expires_at"])),
            )
            sessions[session.token_hash] = session
        return sessions

    def save(self, sessions: dict[str, StoredAuthSession]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "sessions": [
                {
                    "token_hash": session.token_hash,
                    "issued_at": session.issued_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                }
                for session in sessions.values()
            ]
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class TokenManager:
    """管理首次 PIN 配对和后续 token 校验。"""

    def __init__(
        self,
        pin: str,
        *,
        ttl_seconds: int = 3600,
        token_store: TokenStore | None = None,
    ) -> None:
        self._pin = pin or self.generate_pin()
        self._ttl = ttl_seconds
        self._sessions: dict[str, AuthSession] = {}
        self._stored_sessions: dict[str, StoredAuthSession] = {}
        self._token_store = token_store
        if self._token_store is not None:
            self._stored_sessions = self._token_store.load()

    @staticmethod
    def generate_pin() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @property
    def pin(self) -> str:
        return self._pin

    def issue_token(self, pin: str) -> AuthSession:
        if pin != self._pin:
            raise ValueError("invalid pin")

        issued_at = datetime.now(UTC)
        token = secrets.token_urlsafe(24)
        session = AuthSession(
            token=token,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=self._ttl),
        )
        self._sessions[token] = session
        if self._token_store is not None:
            # 落盘只保存 hash，避免配置目录泄漏时暴露可直接复用的 token。
            token_hash = self.hash_token(token)
            self._stored_sessions[token_hash] = StoredAuthSession(
                token_hash=token_hash,
                issued_at=session.issued_at,
                expires_at=session.expires_at,
            )
            self._token_store.save(self._active_stored_sessions(datetime.now(UTC)))
        return session

    def build_hmac(self, token: str, timestamp: int) -> str:
        message = str(timestamp).encode("utf-8")
        digest = hmac.new(token.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return digest

    def verify_token(self, token: str, timestamp: int, signature: str) -> bool:
        now = datetime.now(UTC)
        session = self._sessions.get(token)
        stored_session = None
        if session is None:
            stored_session = self._stored_sessions.get(self.hash_token(token))
            if stored_session is None:
                return False
            session_expires_at = stored_session.expires_at
        else:
            session_expires_at = session.expires_at

        if session_expires_at < now:
            self._prune_expired(now)
            return False

        delta = abs(int(now.timestamp()) - timestamp)
        if delta > 300:
            return False

        expected = self.build_hmac(token, timestamp)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _active_stored_sessions(self, now: datetime) -> dict[str, StoredAuthSession]:
        return {
            token_hash: session
            for token_hash, session in self._stored_sessions.items()
            if session.expires_at >= now
        }

    def _prune_expired(self, now: datetime) -> None:
        if self._token_store is None:
            return
        active = self._active_stored_sessions(now)
        if len(active) != len(self._stored_sessions):
            self._stored_sessions = active
            self._token_store.save(self._stored_sessions)
