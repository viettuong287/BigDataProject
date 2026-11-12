"""In schema + số dòng + vài dòng mẫu của mọi bảng Parquet (dùng khi viết data contract)."""
import sys
from pathlib import Path

import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[1] / "data"

for layer in ("analytics", "gold"):
    for d in sorted((ROOT / layer).iterdir()):
        t = ds.dataset(d, format="parquet", partitioning="hive").to_table()
        print(f"\n## {layer}.{d.name}  rows={t.num_rows}")
        for f in t.schema:
            print(f"  {f.name}: {f.type}")
        if "-v" in sys.argv:
            print(t.slice(0, 3).to_pandas().to_string())
