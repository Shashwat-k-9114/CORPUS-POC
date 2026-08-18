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


def valid_pdf_with_text() -> bytes:
    return build_minimal_pdf(text="Hello World", page_width=200, page_height=200)


def blank_page_pdf() -> bytes:
    return build_minimal_pdf(text="", page_width=200, page_height=200)


def malformed_pdf_bytes() -> bytes:
    return b"%PDF-1.4\nthis is not a well-formed PDF body, just garbage bytes\n%%EOF"


def non_pdf_bytes() -> bytes:
    return b"This is a plain text file pretending to be a PDF."
