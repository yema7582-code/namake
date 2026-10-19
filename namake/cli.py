"""namake (ナマケモノ = sloth). Do the polite-email chores with a local model.

  namake puff "火曜14時OK、資料は明日送る" --to 山田様 --from 中崎
  namake shrink mail.txt
  namake digest ~/inbox-export > morning.md
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .core import digest, puff, shrink


def _llm():
    if os.environ.get("NAMAKE_FAKE"):
        from .llm import FakeLLM
        return FakeLLM([os.environ["NAMAKE_FAKE"]] * 100)
    from .llm import LocalLLM
    return LocalLLM()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="namake", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("puff", help="lazy memo -> polite email")
    p.add_argument("memo")
    p.add_argument("--to", required=True)
    p.add_argument("--from", dest="sender", default=os.environ.get("NAMAKE_NAME", ""))
    s = sub.add_parser("shrink", help="long email -> two lines")
    s.add_argument("file", nargs="?", help="file to read (default: stdin)")
    d = sub.add_parser("digest", help="folder of .eml/.txt -> morning note")
    d.add_argument("folder")
    a = ap.parse_args(argv)

    llm = _llm()
    if a.cmd == "puff":
        if not a.sender:
            ap.error("--from is required (or set NAMAKE_NAME)")
        dr = puff(llm, a.memo, a.to, a.sender)
        print(dr.text)
        for w in dr.warnings:
            print(f"⚠ {w}", file=sys.stderr)
        return 1 if dr.warnings else 0
    if a.cmd == "shrink":
        text = Path(a.file).read_text(encoding="utf-8") if a.file else sys.stdin.read()
        print(shrink(llm, text))
        return 0
    print(digest(llm, Path(a.folder)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
