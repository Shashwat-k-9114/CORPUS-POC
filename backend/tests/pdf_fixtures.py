"""Minimal, deterministic, hand-built PDF byte fixtures for tests.

Generated at runtime instead of committed as binary files so the test suite has
no dependency on a PDF-writing library and no binary assets in git.
"""


def build_minimal_pdf(text: str = "", page_width: int = 200, page_height: int = 200) -> bytes:
    content_stream = f"BT /F1 24 Tf 20 100 Td ({text}) Tj ET" if text else ""
    stream_bytes = content_stream.encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream_bytes)} >>\nstream\n".encode() + stream_bytes + b"\nendstream",
    ]

    buf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj_body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{i} 0 obj\n".encode() + obj_body + b"\nendobj\n"

    xref_offset = len(buf)
    n = len(objects) + 1
    buf += f"xref\n0 {n}\n".encode()
    buf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        buf += f"{off:010d} 00000 n \n".encode()
    buf += f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(buf)


def build_multi_page_pdf(page_count: int = 3, text_prefix: str = "Page") -> bytes:
    """Build a small valid PDF with independent, text-bearing pages."""
    if page_count < 1:
        raise ValueError("page_count must be positive")
    page_ids = list(range(3, 3 + page_count))
    font_id = 3 + page_count
    content_ids = list(range(font_id + 1, font_id + 1 + page_count))
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Kids [{ ' '.join(f'{item} 0 R' for item in page_ids) }] "
            f"/Count {page_count} >>"
        ).encode(),
    ]
    for page_id, content_id in zip(page_ids, content_ids):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for page_number in range(1, page_count + 1):
        stream = f"BT /F1 24 Tf 20 100 Td ({text_prefix} {page_number}) Tj ET".encode("latin-1")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    buf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj_body in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf += f"{index} 0 obj\n".encode() + obj_body + b"\nendobj\n"
    xref_offset = len(buf)
    object_count = len(objects) + 1
    buf += f"xref\n0 {object_count}\n".encode()
    buf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        buf += f"{offset:010d} 00000 n \n".encode()
    buf += f"trailer\n<< /Size {object_count} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    return bytes(buf)


def valid_pdf_with_text() -> bytes:
    return build_minimal_pdf(text="Hello World", page_width=200, page_height=200)


def blank_page_pdf() -> bytes:
    return build_minimal_pdf(text="", page_width=200, page_height=200)


def malformed_pdf_bytes() -> bytes:
    return b"%PDF-1.4\nthis is not a well-formed PDF body, just garbage bytes\n%%EOF"


def non_pdf_bytes() -> bytes:
    return b"This is a plain text file pretending to be a PDF."
