from __future__ import annotations

from dataclasses import dataclass, field
import base64
from pathlib import Path
import re
from typing import Any


DEFAULT_CHUNK_SIZE = 64 * 1024
DEFAULT_MAX_FILE_SIZE = 512 * 1024 * 1024


class FileTransferError(ValueError):
    pass


@dataclass(slots=True)
class ActiveFileTransfer:
    transfer_id: str
    original_name: str
    safe_name: str
    expected_size: int
    target_path: Path
    part_path: Path
    bytes_received: int = 0


@dataclass(frozen=True, slots=True)
class CompletedFileInfo:
    name: str
    size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size": self.size,
        }


@dataclass(slots=True)
class FileTransferService:
    receive_dir: Path
    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    chunk_size: int = DEFAULT_CHUNK_SIZE
    completed_files: int = 0
    completed_bytes: int = 0
    canceled_files: int = 0
    canceled_bytes: int = 0
    _active: dict[str, ActiveFileTransfer] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.receive_dir = self.receive_dir.resolve()
        self.receive_dir.mkdir(parents=True, exist_ok=True)

    @property
    def active_count(self) -> int:
        return len(self._active)

    def start_upload(self, *, transfer_id: str, name: str, size: int) -> ActiveFileTransfer:
        transfer_id = validate_transfer_id(transfer_id)
        if transfer_id in self._active:
            raise FileTransferError("transfer already exists")
        if size < 0:
            raise FileTransferError("file size must be non-negative")
        if size > self.max_file_size:
            raise FileTransferError("file exceeds max_file_size")

        safe_name = sanitize_filename(name)
        target_path = self._build_unique_target_path(transfer_id, safe_name)
        part_path = target_path.with_name(f"{target_path.name}.part")
        transfer = ActiveFileTransfer(
            transfer_id=transfer_id,
            original_name=name,
            safe_name=safe_name,
            expected_size=size,
            target_path=target_path,
            part_path=part_path,
        )
        if part_path.exists():
            part_path.unlink()
        self._active[transfer_id] = transfer
        return transfer

    def write_chunk(self, *, transfer_id: str, offset: int, data_base64: str) -> ActiveFileTransfer:
        transfer = self._get_transfer(transfer_id)
        if offset != transfer.bytes_received:
            raise FileTransferError("unexpected chunk offset")

        try:
            chunk = base64.b64decode(data_base64, validate=True)
        except ValueError as exc:
            raise FileTransferError("invalid base64 chunk") from exc

        if not chunk:
            raise FileTransferError("empty chunk")
        if len(chunk) > self.chunk_size:
            raise FileTransferError("chunk exceeds chunk_size")
        if transfer.bytes_received + len(chunk) > transfer.expected_size:
            raise FileTransferError("chunk exceeds declared file size")

        with transfer.part_path.open("ab") as output:
            output.write(chunk)
        transfer.bytes_received += len(chunk)
        return transfer

    def complete_upload(self, *, transfer_id: str) -> ActiveFileTransfer:
        transfer = self._get_transfer(transfer_id)
        if transfer.bytes_received != transfer.expected_size:
            raise FileTransferError("file upload is incomplete")
        transfer.part_path.replace(transfer.target_path)
        self.completed_files += 1
        self.completed_bytes += transfer.expected_size
        del self._active[transfer_id]
        return transfer

    def cancel_upload(self, *, transfer_id: str) -> ActiveFileTransfer | None:
        transfer = self._active.pop(validate_transfer_id(transfer_id), None)
        if transfer is None:
            return None
        if transfer.part_path.exists():
            transfer.part_path.unlink()
        self.canceled_files += 1
        self.canceled_bytes += transfer.bytes_received
        return transfer

    def cancel_many(self, transfer_ids: set[str]) -> int:
        canceled = 0
        for transfer_id in list(transfer_ids):
            if self.cancel_upload(transfer_id=transfer_id) is not None:
                canceled += 1
        return canceled

    def list_files(self) -> list[CompletedFileInfo]:
        files: list[CompletedFileInfo] = []
        for item in sorted(self.receive_dir.iterdir(), key=lambda path: path.name.lower()):
            if not item.is_file() or item.name.endswith(".part"):
                continue
            files.append(CompletedFileInfo(name=item.name, size=item.stat().st_size))
        return files

    def resolve_download_path(self, name: str) -> Path:
        safe_name = sanitize_filename(name)
        if safe_name.endswith(".part"):
            raise FileTransferError("partial files are not downloadable")
        target = ensure_within_directory(self.receive_dir, self.receive_dir / safe_name)
        if not target.is_file():
            raise FileTransferError("file not found")
        return target

    def _get_transfer(self, transfer_id: str) -> ActiveFileTransfer:
        transfer = self._active.get(transfer_id)
        if transfer is None:
            raise FileTransferError("unknown transfer id")
        return transfer

    def _build_unique_target_path(self, transfer_id: str, safe_name: str) -> Path:
        candidate = self.receive_dir / safe_name
        if not candidate.exists() and not candidate.with_name(f"{candidate.name}.part").exists():
            return ensure_within_directory(self.receive_dir, candidate)

        stem = candidate.stem
        suffix = candidate.suffix
        fallback = self.receive_dir / f"{stem}-{transfer_id}{suffix}"
        return ensure_within_directory(self.receive_dir, fallback)


def sanitize_filename(name: str) -> str:
    cleaned = Path(str(name)).name.strip()
    if not cleaned or cleaned in {".", ".."}:
        raise FileTransferError("invalid file name")
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", cleaned)
    cleaned = cleaned.rstrip(" .")
    if not cleaned:
        raise FileTransferError("invalid file name")
    return cleaned[:160]


def validate_transfer_id(transfer_id: str) -> str:
    normalized = str(transfer_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", normalized):
        raise FileTransferError("invalid transfer id")
    return normalized


def ensure_within_directory(base_dir: Path, target_path: Path) -> Path:
    resolved = target_path.resolve()
    if base_dir != resolved and base_dir not in resolved.parents:
        raise FileTransferError("target path escapes receive_dir")
    return resolved
