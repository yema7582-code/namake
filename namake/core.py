from __future__ import annotations

import email
import email.policy
from dataclasses import dataclass, field
from pathlib import Path

from . import prompts
from .guard import check

import re

# A seatbelt for the 1B model: if the mail clearly asks for something by a date
# and the model still says "nothing to do", don't trust it.
_ASKS = re.compile(r"(いただけ(ます|れば)(と幸い|でしょうか)|ください|お送り|ご送付|ご返信|ご回答)")
_BY = re.compile(r"(\d+日|[月火水木金土日]曜日?|今週|来週|明日|本日)(まで|中)")


def looks_like_request(body: str) -> bool:
    return bool(_ASKS.search(body) and _BY.search(body))


@dataclass
class Draft:
    text: str
    warnings: list[str] = field(default_factory=list)


def puff(llm, memo: str, to: str, sender: str, tries: int = 3) -> Draft:
    """Short lazy memo in, polite business email out.

    If the fact check complains, ask again a little warmer (up to `tries` times)
    and keep the draft with the fewest warnings. You are napping anyway.
    """
    user = f"宛先: {to}\n差出人: {sender}\nメモ: {memo.strip()}"
    msgs = prompts.build(prompts.PUFF_SYSTEM, prompts.PUFF_SHOTS, user)
    best: Draft | None = None
    for i in range(max(1, tries)):
        text = llm.chat(msgs, temperature=0.2 + 0.25 * i)
        d = Draft(text=text, warnings=check(memo, text, sender, to))
        if best is None or len(d.warnings) < len(best.warnings):
            best = d
        if not d.warnings:
            break
    return best


def shrink(llm, mail: str) -> str:
    """Long polite email in, two lines out."""
    out = llm.chat(prompts.build(prompts.SHRINK_SYSTEM, prompts.SHRINK_SHOTS, mail.strip()), max_tokens=120)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    want = [l for l in lines if l.startswith(("用件", "やること"))]
    return "\n".join((want or lines)[:2])


def read_message(path: Path) -> tuple[str, str, str]:
    """Return (from, subject, body) for a .eml or a plain .txt file."""
    raw = path.read_bytes()
    if path.suffix.lower() == ".eml":
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        body = msg.get_body(preferencelist=("plain",))
        text = body.get_content() if body else ""
        return str(msg.get("From", "")), str(msg.get("Subject", "")), text
    return "", path.stem, raw.decode("utf-8", errors="replace")


def digest(llm, folder: Path) -> str:
    """Shrink every message in a folder into one morning note, sorted so the ones needing action come first."""
    rows = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() not in (".eml", ".txt") or not p.is_file():
            continue
        frm, subj, body = read_message(p)
        gist = shrink(llm, body)
        todo = next((l for l in gist.splitlines() if l.startswith("やること")), "やること: なし")
        if todo.endswith("なし") and looks_like_request(body):
            gist = gist.replace(todo, "やること: (モデルは「なし」と言っていますが、期限つきの依頼に見えます。本文を確認)")
            todo = "やること: 要確認"
        rows.append((todo.endswith("なし"), p.name, frm, subj, gist))
    rows.sort(key=lambda r: r[0])
    need = sum(1 for r in rows if not r[0])
    out = [f"# 朝のメールまとめ ({len(rows)}通、対応が要るのは{need}通)", ""]
    for _, name, frm, subj, gist in rows:
        out.append(f"## {subj or name}" + (f" ({frm})" if frm else ""))
        out.extend(gist.splitlines())
        out.append("")
    return "\n".join(out).rstrip() + "\n"
