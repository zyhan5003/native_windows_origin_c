from __future__ import annotations

import base64

import pytest

from screen_windows.filetransfer import (
    FileTransferError,
    FileTransferService,
    sanitize_filename,
)


def encode_chunk(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def test_file_transfer_writes_chunks_and_completes(tmp_path) -> None:
    service = FileTransferService(receive_dir=tmp_path, chunk_size=8)

    transfer = service.start_upload(transfer_id="abc-1", name="../report.txt", size=11)
    assert transfer.safe_name == "report.txt"

    first = service.write_chunk(
        transfer_id="abc-1",
        offset=0,
        data_base64=encode_chunk(b"hello "),
    )
    assert first.bytes_received == 6

    second = service.write_chunk(
        transfer_id="abc-1",
        offset=6,
        data_base64=encode_chunk(b"world"),
    )
    assert second.bytes_received == 11

    completed = service.complete_upload(transfer_id="abc-1")

    assert completed.target_path.read_bytes() == b"hello world"
    assert not completed.part_path.exists()
    assert service.completed_files == 1
    assert service.completed_bytes == 11
    assert service.active_count == 0


def test_file_transfer_completes_zero_byte_file(tmp_path) -> None:
    service = FileTransferService(receive_dir=tmp_path)

    transfer = service.start_upload(transfer_id="empty", name="empty.txt", size=0)
    completed = service.complete_upload(transfer_id="empty")

    assert completed is transfer
    assert completed.target_path.read_bytes() == b""
    assert not completed.part_path.exists()
    assert service.completed_files == 1
    assert service.completed_bytes == 0


def test_file_transfer_generates_unique_name_when_target_and_fallback_exist(tmp_path) -> None:
    service = FileTransferService(receive_dir=tmp_path)
    (tmp_path / "note.txt").write_text("old", encoding="utf-8")
    (tmp_path / "note-abc-1.txt").write_text("older", encoding="utf-8")

    transfer = service.start_upload(transfer_id="abc", name="note.txt", size=1)

    assert transfer.safe_name == "note.txt"
    assert transfer.target_path.name == "note-abc-2.txt"
    assert transfer.part_path.name == "note-abc-2.txt.part"


def test_file_transfer_rejects_unexpected_offset(tmp_path) -> None:
    service = FileTransferService(receive_dir=tmp_path)
    service.start_upload(transfer_id="abc", name="a.txt", size=3)

    with pytest.raises(FileTransferError, match="unexpected chunk offset"):
        service.write_chunk(
            transfer_id="abc",
            offset=1,
            data_base64=encode_chunk(b"a"),
        )


def test_file_transfer_rejects_oversized_file(tmp_path) -> None:
    service = FileTransferService(receive_dir=tmp_path, max_file_size=2)

    with pytest.raises(FileTransferError, match="exceeds max_file_size"):
        service.start_upload(transfer_id="abc", name="a.txt", size=3)


def test_file_transfer_cancel_removes_partial_file(tmp_path) -> None:
    service = FileTransferService(receive_dir=tmp_path, chunk_size=8)
    transfer = service.start_upload(transfer_id="abc", name="a.txt", size=4)
    service.write_chunk(transfer_id="abc", offset=0, data_base64=encode_chunk(b"ab"))

    canceled = service.cancel_upload(transfer_id="abc")

    assert canceled is transfer
    assert not transfer.part_path.exists()
    assert service.active_count == 0
    assert service.canceled_files == 1
    assert service.canceled_bytes == 2


def test_file_transfer_lists_and_resolves_completed_files(tmp_path) -> None:
    service = FileTransferService(receive_dir=tmp_path)
    (tmp_path / "done.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "skip.txt.part").write_text("partial", encoding="utf-8")

    files = service.list_files()
    path = service.resolve_download_path("done.txt")

    assert [file.name for file in files] == ["done.txt"]
    assert files[0].size == 2
    assert path == (tmp_path / "done.txt").resolve()
    with pytest.raises(FileTransferError, match="partial"):
        service.resolve_download_path("skip.txt.part")


def test_sanitize_filename_removes_path_and_forbidden_chars() -> None:
    assert sanitize_filename("..\\bad:name?.txt") == "bad_name_.txt"


def test_sanitize_filename_avoids_windows_reserved_names() -> None:
    assert sanitize_filename("CON.txt") == "_CON.txt"
    assert sanitize_filename("lpt1") == "_lpt1"
