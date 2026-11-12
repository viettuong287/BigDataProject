"""Xuất các sơ đồ Mermaid trong docs/architecture.md thành PNG (Chromium headless + mermaid.js từ CDN).

Chạy: docker compose run --rm screenshots python scripts/render_diagrams.py
Kết quả: docs/architecture.png (sơ đồ luồng chi tiết), docs/architecture_pipeline_position.png,
         evidence/architecture_pipeline.png, evidence/neon_tables_inventory.png (nếu có neon_inventory.html)
"""
import html
import re
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
blocks = re.findall(r"```mermaid\n(.*?)```", (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8"), re.S)
outputs = [ROOT / "docs" / "architecture_pipeline_position.png", ROOT / "docs" / "architecture.png"]

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<style>body{margin:0;padding:16px;background:#fff;font-family:Arial} #d{display:inline-block}</style></head>
<body><div id="d" class="mermaid">%s</div>
<script>mermaid.initialize({startOnLoad:true, theme:'default', flowchart:{htmlLabels:true, curve:'basis'}});</script>
</body></html>"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2400, "height": 1400}, device_scale_factor=2)
    for code, out in zip(blocks, outputs):
        page.set_content(TEMPLATE % html.escape(code))
        page.wait_for_selector("#d svg", timeout=60000)
        page.wait_for_timeout(500)
        page.locator("#d").screenshot(path=str(out))
        print("->", out.relative_to(ROOT))
    shutil.copy(outputs[1], ROOT / "evidence" / "architecture_pipeline.png")

    inv = ROOT / "evidence" / "neon_inventory.html"
    if inv.exists():
        page = browser.new_page(viewport={"width": 1240, "height": 900}, device_scale_factor=1)
        page.goto(inv.as_uri())
        page.screenshot(path=str(ROOT / "evidence" / "neon_tables_inventory.png"), full_page=True)
        print("-> evidence/neon_tables_inventory.png")
    browser.close()
