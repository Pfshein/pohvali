"""Pure PNG validation for admin-uploaded mascot images (PH-405).

Parses only what the format guarantees: the signature, the IHDR chunk
(dimensions and colour type) and the chunk list. No external dependencies and
no full decode — the file bytes are stored as-is.
"""

MAX_IMAGE_BYTES = 1024 * 1024
MIN_DIMENSION = 256
MAX_DIMENSION = 1024

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_IHDR_LENGTH = 13
_IHDR_OFFSET = 8
_BYTES_PER_LENGTH = 4
_BYTES_PER_TYPE = 4
_BYTES_PER_CRC = 4

_TOO_BIG = "Файл больше 1 MiB — сожми PNG и попробуй ещё раз."
_NOT_PNG = "Это не PNG-файл — пришли PNG-документ."
_DAMAGED = "PNG выглядит повреждённым — попробуй пересохранить файл."
_DIMENSIONS = "Разрешение должно быть от 256 до 1024 px по обеим сторонам."
_NO_ALPHA = "В PNG нет alpha-канала — сохрани файл с прозрачностью (RGBA)."


def validate_png(data: bytes) -> str | None:
    """Return a calm operator-facing error, or None when the PNG is acceptable."""
    if len(data) == 0:
        return _NOT_PNG
    if len(data) > MAX_IMAGE_BYTES:
        return _TOO_BIG
    if not data.startswith(PNG_SIGNATURE):
        return _NOT_PNG

    header_end = _IHDR_OFFSET + _BYTES_PER_LENGTH + _BYTES_PER_TYPE + _IHDR_LENGTH + _BYTES_PER_CRC
    if len(data) < header_end:
        return _DAMAGED
    declared_length = int.from_bytes(
        data[_IHDR_OFFSET : _IHDR_OFFSET + _BYTES_PER_LENGTH], "big"
    )
    chunk_type = data[
        _IHDR_OFFSET + _BYTES_PER_LENGTH : _IHDR_OFFSET + _BYTES_PER_LENGTH + _BYTES_PER_TYPE
    ]
    if declared_length != _IHDR_LENGTH or chunk_type != b"IHDR":
        return _DAMAGED

    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    color_type = data[25]

    if not (MIN_DIMENSION <= width <= MAX_DIMENSION) or not (
        MIN_DIMENSION <= height <= MAX_DIMENSION
    ):
        return _DIMENSIONS

    has_alpha = color_type in (4, 6) or (color_type == 3 and _has_trns_chunk(data))
    if not has_alpha:
        return _NO_ALPHA
    return None


def _has_trns_chunk(data: bytes) -> bool:
    offset = _IHDR_OFFSET
    while offset + _BYTES_PER_LENGTH + _BYTES_PER_TYPE <= len(data):
        length = int.from_bytes(data[offset : offset + _BYTES_PER_LENGTH], "big")
        chunk_type = data[
            offset + _BYTES_PER_LENGTH : offset + _BYTES_PER_LENGTH + _BYTES_PER_TYPE
        ]
        if chunk_type == b"tRNS":
            return True
        if chunk_type == b"IEND":
            return False
        offset += _BYTES_PER_LENGTH + _BYTES_PER_TYPE + length + _BYTES_PER_CRC
    return False
