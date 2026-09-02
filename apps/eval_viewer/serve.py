#!/usr/bin/env python3
"""Serve a generated evidence dossier on localhost."""

from __future__ import annotations

import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("apps/eval_viewer/dist"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("COMPANY_OS_EVAL_VIEWER_PORT", "4179")))
    args = parser.parse_args()
    root = args.root.resolve()
    handler = lambda *values, **kwargs: SimpleHTTPRequestHandler(*values, directory=str(root), **kwargs)
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Evidence viewer: http://127.0.0.1:{args.port}/")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
