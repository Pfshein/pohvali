import struct

from app.modules.mascots.png import MAX_IMAGE_BYTES, validate_png


def build_png(
    *,
    width: int = 512,
    height: int = 512,
    color_type: int = 6,
    with_trns: bool = False,
    trailing: bytes = b"",
) -> bytes:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + chunk_type
            + payload
            + b"\x00\x00\x00\x00"
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
    if with_trns:
        data += chunk(b"tRNS", b"\x00")
    data += chunk(b"IEND", b"")
    return data + trailing


def test_valid_rgba_png_within_bounds_passes() -> None:
    assert validate_png(build_png()) is None
    assert validate_png(build_png(width=256, height=256)) is None
    assert validate_png(build_png(width=1024, height=1024)) is None


def test_grayscale_alpha_png_passes() -> None:
    assert validate_png(build_png(color_type=4)) is None


def test_palette_png_with_trns_chunk_passes() -> None:
    assert validate_png(build_png(color_type=3, with_trns=True)) is None


def test_png_without_alpha_is_rejected() -> None:
    for color_type in (0, 2):
        error = validate_png(build_png(color_type=color_type))
        assert error is not None
        assert "alpha" in error.casefold()


def test_palette_png_without_trns_is_rejected() -> None:
    error = validate_png(build_png(color_type=3))

    assert error is not None
    assert "alpha" in error.casefold()


def test_non_png_bytes_are_rejected() -> None:
    error = validate_png(b"JPEG-not-a-png" * 4)

    assert error is not None
    assert "png" in error.casefold()


def test_empty_input_is_rejected() -> None:
    assert validate_png(b"") is not None


def test_oversized_bytes_are_rejected() -> None:
    payload = build_png() + b"\x00" * (MAX_IMAGE_BYTES + 1)

    error = validate_png(payload)

    assert error is not None
    assert "1 MiB" in error


def test_dimensions_outside_256_1024_are_rejected() -> None:
    for width, height in ((255, 512), (512, 1025), (128, 128)):
        error = validate_png(build_png(width=width, height=height))

        assert error is not None, (width, height)
        assert "256" in error and "1024" in error


def test_damaged_header_is_rejected() -> None:
    data = bytearray(build_png())
    data[12] = ord("X")

    assert validate_png(bytes(data)) is not None
    assert validate_png(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10) is not None
