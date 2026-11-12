"""Dump schema + row count + sample of each Analytics Parquet table (dev helper)."""
import glob
import os

import pyarrow.parquet as pq

ROOT = r"D:\Analytics-main\data\analytics"
for d in sorted(os.listdir(ROOT)):
    files = glob.glob(os.path.join(ROOT, d, "*.parquet"))
    t = pq.read_table(files[0]) if len(files) == 1 else pq.ParquetDataset(os.path.join(ROOT, d)).read()
    size = sum(os.path.getsize(f) for f in files)
    print(f"### {d}  rows={t.num_rows} files={len(files)} bytes={size}")
    for f in t.schema:
        print(f"  {f.name}: {f.type}")
    print("  sample:", t.slice(0, 1).to_pylist())
