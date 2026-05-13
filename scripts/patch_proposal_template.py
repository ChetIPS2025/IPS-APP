"""One-off patch for bundled proposal template: title dash + responsibilities placeholder."""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path


def main() -> None:
    p = Path(__file__).resolve().parents[1] / "assets" / "estimate_template_autofill_logo_updated.docx"
    data = p.read_bytes()
    z = zipfile.ZipFile(io.BytesIO(data))
    name = "word/document.xml"
    xml = z.read(name).decode("utf-8")

    # Fix mojibake / replacement char between JOB_NAME and "Quote" (template had U+FFFD)
    xml2 = xml
    bad = "{{JOB_NAME}}\uFFFD Quote"
    if bad in xml2:
        xml2 = xml2.replace(bad, "{{JOB_NAME}}\u2013 Quote")
    elif "{{JOB_NAME}} \u2013 Quote" not in xml2:
        # Any single odd char between `}}` and ` Quote`
        xml2 = re.sub(
            r"\{\{JOB_NAME\}\}.\s*Quote",
            "{{JOB_NAME}}\u2013 Quote",
            xml2,
            count=1,
        )

    needle = "{{CUSTOMER_NAME}} Responsibilities</w:t></w:r></w:p>"
    insert = (
        "{{CUSTOMER_NAME}} Responsibilities</w:t></w:r></w:p>"
        '<w:p><w:r><w:t xml:space="preserve">{{CUSTOMER_RESPONSIBILITIES}}</w:t></w:r></w:p>'
    )
    if "{{CUSTOMER_RESPONSIBILITIES}}" not in xml2 and needle in xml2:
        xml2 = xml2.replace(needle, insert, 1)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zw:
        for item in z.infolist():
            d = z.read(item.filename)
            if item.filename == name:
                d = xml2.encode("utf-8")
            zw.writestr(item, d)

    p.write_bytes(buf.getvalue())
    m = re.search(r"\{\{JOB_NAME\}\}[^<]+", xml2)
    print("JOB run:", repr(m.group(0)) if m else "missing")
    print("Has CUSTOMER_RESPONSIBILITIES:", "{{CUSTOMER_RESPONSIBILITIES}}" in xml2)


if __name__ == "__main__":
    main()
