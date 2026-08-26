#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""model_data 可视化服务（端口 8620）。

启动：
    python viz_server.py            # 默认 8620
    python viz_server.py --port 8621

页面：http://127.0.0.1:8620/
"""
from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

import viz_transform as vt

BASE_DIR = Path(__file__).resolve().parent
VIZ_DIR = BASE_DIR.parent / "viz"  # viz_index.html / echarts.min.js 位于 model_data/viz/
app = FastAPI(title="model_data viz", docs_url=None, redoc_url=None)

_lock = threading.Lock()
_cache: dict | None = None


def _data() -> dict:
    """现读现转 + 短缓存；抓取进程更新 JSONL 后刷新页面即生效。"""
    global _cache
    jsonl = vt.DEFAULT_JSONL
    with _lock:
        try:
            mtime = jsonl.stat().st_mtime_ns
        except OSError:
            mtime = 0
        if _cache is None or _cache.get("_mtime") != mtime:
            rows = vt.load_rows(jsonl)
            _cache = {
                "_mtime": mtime,
                "rows": rows,
                "schema": vt.build_schema_info(rows),
                "aggregates": vt.build_aggregates(rows),
            }
        return _cache


@app.get("/api/models")
def api_models():
    return JSONResponse({"rows": _data()["rows"]})


@app.get("/api/aggregates")
def api_aggregates():
    return JSONResponse(_data()["aggregates"])


@app.get("/api/schema")
def api_schema():
    return JSONResponse(_data()["schema"])


@app.get("/", response_class=HTMLResponse)
def index():
    html_path = VIZ_DIR / "viz_index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/static/echarts.min.js")
def echarts_static():
    js = (VIZ_DIR / "echarts.min.js").read_text(encoding="utf-8")
    from fastapi.responses import Response
    return Response(js, media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8620)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
