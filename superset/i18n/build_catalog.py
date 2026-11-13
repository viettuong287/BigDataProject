"""Biên dịch bản dịch tiếng Việt cho Superset: messages.po -> messages.mo (Flask/Jinja, backend)
và messages.json (định dạng Jed mà frontend React đọc qua bootstrap data `language_pack`).

Chạy trong Dockerfile của image Superset (đã có thư viện babel):
    python build_catalog.py <messages.po> <superset/translations/vi/LC_MESSAGES>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po


def main(po_path: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(po_path, "rb") as f:
        catalog = read_po(f, locale="vi", domain="messages")

    with open(out / "messages.mo", "wb") as f:
        write_mo(f, catalog)

    pack: dict = {"": {"domain": "superset", "plural_forms": "nplurals=1; plural=0;", "lang": "vi"}}
    for msg in catalog:
        if not msg.id or not msg.string or msg.fuzzy:
            continue
        key = msg.id[0] if isinstance(msg.id, tuple) else msg.id
        value = list(msg.string) if isinstance(msg.string, tuple) else [msg.string]
        pack[key] = value
    (out / "messages.json").write_text(
        json.dumps({"domain": "superset", "locale_data": {"superset": pack}}, ensure_ascii=False),
        encoding="utf-8",
    )

    # Đối chiếu với danh mục chuỗi gốc của Superset (chuỗi Flask-AppBuilder nằm ngoài danh mục này).
    en = out.parent.parent / "en" / "LC_MESSAGES" / "messages.json"
    if en.exists():
        known = json.loads(en.read_text(encoding="utf-8"))["locale_data"]["superset"]
        ours = [k for k in pack if k]
        missing = [k for k in ours if k not in known]
        print(f"vi: {len(ours)} chuỗi đã dịch / {len(known) - 1} chuỗi của Superset; "
              f"{len(missing)} chuỗi ngoài danh mục Superset: {missing}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
