"""
Upload rules: what each purpose may contain, and how a finished upload is
verified before anything can reference it.

R2 presigned PUTs cannot enforce a maximum size, so limits are enforced after
the upload: the object's real size and type are read back, its first bytes are
checked against the declared format, and audio/video durations are read from
the MP4 header. Anything that fails is deleted.
"""

from dataclasses import dataclass

MB = 1024 * 1024

IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heif",
}
VIDEO_TYPES = {
    "video/mp4": "mp4",
    "video/quicktime": "mov",
}
# Voice notes recorded by the app are AAC in an MP4 (.m4a) container
AUDIO_TYPES = {
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
}

IMAGE_MAX_BYTES = 10 * MB
VIDEO_MAX_BYTES = 50 * MB
VIDEO_MAX_SECONDS = 60
VOICE_MAX_BYTES = 10 * MB
VOICE_MAX_SECONDS = 120


@dataclass(frozen=True)
class UploadRule:
    folder: str
    kind: str  # "image" | "video" | "audio"
    max_bytes: int
    max_seconds: int = 0
    requires_chat: bool = False

    @property
    def content_types(self):
        return {"image": IMAGE_TYPES, "video": VIDEO_TYPES, "audio": AUDIO_TYPES}[self.kind]


PURPOSES = {
    "profile_picture": UploadRule("profile", "image", IMAGE_MAX_BYTES),
    "profile_gallery": UploadRule("profile", "image", IMAGE_MAX_BYTES),
    "bondmaker_profile_picture": UploadRule("bondmaker", "image", IMAGE_MAX_BYTES),
    "bondmaker_cover_picture": UploadRule("bondmaker", "image", IMAGE_MAX_BYTES),
    "id_document": UploadRule("verification", "image", IMAGE_MAX_BYTES),
    "selfie": UploadRule("verification", "image", IMAGE_MAX_BYTES),
    "post_image": UploadRule("posts", "image", IMAGE_MAX_BYTES),
    "post_video": UploadRule("posts", "video", VIDEO_MAX_BYTES, VIDEO_MAX_SECONDS),
    "chat_image": UploadRule("chat", "image", IMAGE_MAX_BYTES, requires_chat=True),
    "chat_video": UploadRule(
        "chat", "video", VIDEO_MAX_BYTES, VIDEO_MAX_SECONDS, requires_chat=True
    ),
    "chat_voice_note": UploadRule(
        "chat", "audio", VOICE_MAX_BYTES, VOICE_MAX_SECONDS, requires_chat=True
    ),
}


class UploadRejected(Exception):
    """The file broke a rule. The message is safe to show to the client."""


def normalize_content_type(value):
    return (value or "").split(";")[0].strip().lower()


def check_declared(purpose, content_type, size_bytes):
    """Validate what the client says it will upload. Returns the UploadRule."""
    rule = PURPOSES.get(purpose)
    if rule is None:
        raise UploadRejected("Unknown upload purpose.")
    if content_type not in rule.content_types:
        allowed = ", ".join(sorted(rule.content_types))
        raise UploadRejected(f"{content_type or 'This file type'} is not allowed here. Use {allowed}.")
    if size_bytes <= 0:
        raise UploadRejected("The file is empty.")
    if size_bytes > rule.max_bytes:
        raise UploadRejected(f"The file is larger than {rule.max_bytes // MB} MB.")
    return rule


# ---------------------------------------------------------------------------
# Content sniffing
# ---------------------------------------------------------------------------

HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}


def matches_signature(content_type, head_bytes):
    """True when the file's first bytes are consistent with its declared type."""
    if content_type == "image/jpeg":
        return head_bytes.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return head_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return head_bytes[0:4] == b"RIFF" and head_bytes[8:12] == b"WEBP"
    if content_type in ("image/heic", "image/heif"):
        return head_bytes[4:8] == b"ftyp" and head_bytes[8:12] in HEIF_BRANDS
    if content_type in VIDEO_TYPES or content_type in AUDIO_TYPES:
        # ISO base media (MP4/MOV/M4A) files open with an ftyp box
        return head_bytes[4:8] == b"ftyp" and head_bytes[8:12] not in HEIF_BRANDS
    return False


# ---------------------------------------------------------------------------
# MP4 duration
# ---------------------------------------------------------------------------

_MAX_TOP_LEVEL_BOXES = 64
_MAX_MOOV_BYTES = 8 * MB


def _boxes(data):
    """Yield (type, payload_start, payload_end) for boxes laid out in data."""
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], "big")
        box_type = data[offset + 4:offset + 8]
        header = 8
        if size == 1:
            if offset + 16 > len(data):
                return
            size = int.from_bytes(data[offset + 8:offset + 16], "big")
            header = 16
        elif size == 0:
            size = len(data) - offset
        if size < header:
            return
        yield box_type, offset + header, min(offset + size, len(data))
        offset += size


def _duration_from_mvhd(payload):
    version = payload[0] if payload else None
    if version == 0 and len(payload) >= 20:
        timescale = int.from_bytes(payload[12:16], "big")
        duration = int.from_bytes(payload[16:20], "big")
    elif version == 1 and len(payload) >= 32:
        timescale = int.from_bytes(payload[20:24], "big")
        duration = int.from_bytes(payload[24:32], "big")
    else:
        return None
    if timescale <= 0:
        return None
    return duration / timescale


def mp4_duration_seconds(read_range, total_size):
    """
    Duration from the movie header, reading only box headers plus the moov box.
    read_range(start, end) returns bytes [start, end). Returns None if the file
    has no readable movie header.
    """
    offset = 0
    for _ in range(_MAX_TOP_LEVEL_BOXES):
        if offset + 8 > total_size:
            return None
        header = read_range(offset, min(offset + 16, total_size))
        if len(header) < 8:
            return None
        size = int.from_bytes(header[0:4], "big")
        box_type = header[4:8]
        header_len = 8
        if size == 1:
            if len(header) < 16:
                return None
            size = int.from_bytes(header[8:16], "big")
            header_len = 16
        elif size == 0:
            size = total_size - offset
        if size < header_len:
            return None

        if box_type == b"moov":
            end = min(offset + size, offset + header_len + _MAX_MOOV_BYTES, total_size)
            moov = read_range(offset + header_len, end)
            for child_type, start, child_end in _boxes(moov):
                if child_type == b"mvhd":
                    return _duration_from_mvhd(moov[start:child_end])
            return None
        offset += size
    return None
