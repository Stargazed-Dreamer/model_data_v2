#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""viz/echarts.min.js 一键复原脚本。

.gitignore 刻意不入库该文件（约 1MB），因此新 clone / 新机器上 viz 页面会因
`echarts is not defined` 整页初始化失败（图表与表格都不渲染）。克隆后跑一次本脚本即可：

    python scripts/fetch_viz_assets.py

按 npmmirror → jsdelivr → unpkg 顺序尝试，任一成功即写盘并校验文件头。
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "viz" / "echarts.min.js"
URLS = [
    "https://registry.npmmirror.com/echarts/5.5.1/files/dist/echarts.min.js",
    "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js",
    "https://unpkg.com/echarts@5.5.1/dist/echarts.min.js",
]
MAGIC = b"Licensed to the Apache Software Foundation"


def main() -> int:
    if DEST.exists() and DEST.stat().st_size > 500_000:
        print(f"already present: {DEST} ({DEST.stat().st_size} bytes)")
        return 0
    DEST.parent.mkdir(parents=True, exist_ok=True)
    for url in URLS:
        try:
            print(f"trying {url} ...")
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            if MAGIC not in data[:400]:
                print(f"  content check failed, skip")
                continue
            DEST.write_bytes(data)
            print(f"OK -> {DEST} ({len(data)} bytes)")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"  failed: {exc}")
    print("all mirrors failed; download echarts 5.x manually into viz/echarts.min.js")
    return 1


if __name__ == "__main__":
    sys.exit(main())
