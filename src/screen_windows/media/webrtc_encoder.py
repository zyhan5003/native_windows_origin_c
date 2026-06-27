from __future__ import annotations

from dataclasses import asdict, dataclass
import fractions
from typing import Any

import av
import aiortc.codecs as aiortc_codecs
import aiortc.rtcrtpsender as aiortc_sender
from aiortc.codecs import G722Encoder, OpusEncoder, PcmaEncoder, PcmuEncoder, Vp8Encoder
from aiortc.codecs.h264 import H264Encoder, MAX_FRAME_RATE
from aiortc.rtcrtpparameters import RTCRtpCodecParameters

from .encoder import EncoderSelection


_ACTIVE_RUNTIME: "WebRtcEncoderRuntime | None" = None


@dataclass(slots=True)
class WebRtcEncoderStatus:
    requested_encoder: str
    requested_backend: str
    active_encoder: str
    active_backend: str
    hardware_requested: bool
    hardware_active: bool
    fallback_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WebRtcEncoderRuntime:
    def __init__(self, selection: EncoderSelection) -> None:
        self.requested_backend = selection.backend if selection.available else "libx264"
        self.requested_encoder = (
            selection.ffmpeg_encoder if selection.available else "libx264"
        )
        self._active_backend = "pending"
        self._active_encoder = "pending"
        self._fallback_reason = ""

    @property
    def status(self) -> WebRtcEncoderStatus:
        return WebRtcEncoderStatus(
            requested_encoder=self.requested_encoder,
            requested_backend=self.requested_backend,
            active_encoder=self._active_encoder,
            active_backend=self._active_backend,
            hardware_requested=self.requested_encoder != "libx264",
            hardware_active=self._active_encoder not in {"libx264", "pending"},
            fallback_reason=self._fallback_reason,
        )

    def mark_active(self, encoder_name: str, backend: str) -> None:
        self._active_encoder = encoder_name
        self._active_backend = backend
        if encoder_name == self.requested_encoder:
            self._fallback_reason = ""

    def mark_fallback(self, reason: str) -> None:
        self._active_encoder = "libx264"
        self._active_backend = "libx264"
        self._fallback_reason = reason


def install_webrtc_encoder_runtime(selection: EncoderSelection) -> WebRtcEncoderRuntime:
    """让 aiortc H264 实时编码优先使用项目探测出的可用后端。"""

    global _ACTIVE_RUNTIME
    _ACTIVE_RUNTIME = WebRtcEncoderRuntime(selection)
    aiortc_codecs.get_encoder = _get_encoder  # type: ignore[assignment]
    aiortc_sender.get_encoder = _get_encoder  # type: ignore[assignment]
    return _ACTIVE_RUNTIME


def current_webrtc_encoder_status() -> WebRtcEncoderStatus:
    if _ACTIVE_RUNTIME is None:
        return WebRtcEncoderStatus(
            requested_encoder="libx264",
            requested_backend="libx264",
            active_encoder="libx264",
            active_backend="libx264",
            hardware_requested=False,
            hardware_active=False,
            fallback_reason="runtime not installed",
        )
    return _ACTIVE_RUNTIME.status


def _get_encoder(codec: RTCRtpCodecParameters):
    mime_type = codec.mimeType.lower()
    if mime_type == "audio/g722":
        return G722Encoder()
    if mime_type == "audio/opus":
        return OpusEncoder()
    if mime_type == "audio/pcma":
        return PcmaEncoder()
    if mime_type == "audio/pcmu":
        return PcmuEncoder()
    if mime_type == "video/h264":
        return RuntimeH264Encoder(_ACTIVE_RUNTIME)
    if mime_type == "video/vp8":
        return Vp8Encoder()
    raise ValueError(f"No encoder found for MIME type `{mime_type}`")


class RuntimeH264Encoder(H264Encoder):
    def __init__(self, runtime: WebRtcEncoderRuntime | None) -> None:
        super().__init__()
        self._runtime = runtime
        self._encoder_name = (
            runtime.requested_encoder
            if runtime is not None and runtime.requested_encoder
            else "libx264"
        )
        self._backend = (
            runtime.requested_backend
            if runtime is not None and runtime.requested_backend
            else "libx264"
        )
        self._using_fallback = self._encoder_name == "libx264"

    def _encode_frame(self, frame: av.VideoFrame, force_keyframe: bool):
        try:
            yield from self._encode_with_current_encoder(frame, force_keyframe)
        except Exception as exc:
            if self._using_fallback:
                raise
            reason = f"{self._encoder_name} failed: {exc}"
            if self._runtime is not None:
                self._runtime.mark_fallback(reason)
            self.buffer_data = b""
            self.buffer_pts = None
            self.codec = None
            self._encoder_name = "libx264"
            self._backend = "libx264"
            self._using_fallback = True
            yield from self._encode_with_current_encoder(frame, force_keyframe)

    def _encode_with_current_encoder(
        self,
        frame: av.VideoFrame,
        force_keyframe: bool,
    ):
        if self.codec and (
            frame.width != self.codec.width
            or frame.height != self.codec.height
            or abs(self.target_bitrate - self.codec.bit_rate) / self.codec.bit_rate > 0.1
        ):
            self.buffer_data = b""
            self.buffer_pts = None
            self.codec = None

        if force_keyframe:
            frame.pict_type = av.video.frame.PictureType.I
        else:
            frame.pict_type = av.video.frame.PictureType.NONE

        if self.codec is None:
            self.codec = _create_h264_codec(
                self._encoder_name,
                frame=frame,
                target_bitrate=self.target_bitrate,
            )
            if self._runtime is not None:
                self._runtime.mark_active(self._encoder_name, self._backend)

        data_to_send = b""
        for package in self.codec.encode(frame):
            data_to_send += bytes(package)

        if data_to_send:
            yield from _split_h264_bitstream(data_to_send)


def _create_h264_codec(
    encoder_name: str,
    *,
    frame: av.VideoFrame,
    target_bitrate: int,
) -> av.CodecContext:
    codec = av.CodecContext.create(encoder_name, "w")
    codec.width = frame.width
    codec.height = frame.height
    codec.bit_rate = target_bitrate
    codec.framerate = fractions.Fraction(MAX_FRAME_RATE, 1)
    codec.time_base = fractions.Fraction(1, MAX_FRAME_RATE)

    if encoder_name == "h264_qsv":
        codec.pix_fmt = "nv12"
        codec.options = {
            "preset": "veryfast",
            "scenario": "displayremoting",
            "low_power": "1",
            "async_depth": "1",
        }
        return codec

    if encoder_name == "h264_nvenc":
        codec.pix_fmt = "yuv420p"
        codec.options = {
            "preset": "p1",
            "tune": "ll",
            "rc": "cbr",
            "delay": "0",
            "refs": "1",
        }
        return codec

    if encoder_name == "h264_amf":
        codec.pix_fmt = "nv12"
        codec.options = {
            "usage": "ultralowlatency",
            "quality": "speed",
            "rc": "cbr",
        }
        return codec

    codec.pix_fmt = "yuv420p"
    codec.options = {
        "level": "31",
        "tune": "zerolatency",
    }
    codec.profile = "Baseline"
    return codec


def _split_h264_bitstream(buf: bytes):
    annex_b_packages = list(H264Encoder._split_bitstream(buf))
    if annex_b_packages:
        yield from annex_b_packages
        return

    offset = 0
    while offset + 4 <= len(buf):
        nal_size = int.from_bytes(buf[offset : offset + 4], byteorder="big")
        offset += 4
        if nal_size <= 0 or offset + nal_size > len(buf):
            return
        yield buf[offset : offset + nal_size]
        offset += nal_size
