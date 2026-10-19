"""A cheap fact check. Small models sometimes invent a date or a number; catch that before you hit send."""
from __future__ import annotations

import re
import unicodedata

_WEEKDAYS = "月火水木金土日"
_NUM = re.compile(r"\d+")
_WEEKDAY = re.compile(rf"([{_WEEKDAYS}])曜")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def facts(text: str) -> dict[str, set[str]]:
    t = _norm(text)
    nums = {str(int(n)) for n in _NUM.findall(t) if int(n) != 0}  # "14:00" and "14時" both give 14
    days = set(_WEEKDAY.findall(t))
    # 「金曜」 written as 「金曜日」 or 「金」 alone in short memos
    days |= {c for c in re.findall(rf"(?<![^\s、。,])([{_WEEKDAYS}])(?=NG|OK|なら|は|で|に|、|$)", t)}
    return {"numbers": nums, "weekdays": days}


def check(memo: str, mail: str, sender: str = "", recipient: str = "") -> list[str]:
    """Return human-readable warnings. Empty list means nothing looked off."""
    src, out = facts(memo), facts(mail)
    allowed_nums = src["numbers"] | facts(sender + recipient)["numbers"]
    warnings = []
    for n in sorted(src["numbers"] - out["numbers"]):
        warnings.append(f"メモの「{n}」がメールに見当たりません")
    for n in sorted(out["numbers"] - allowed_nums):
        warnings.append(f"メモにない数字「{n}」がメールに入っています")
    for d in sorted(src["weekdays"] - out["weekdays"]):
        warnings.append(f"メモの「{d}曜」がメールに見当たりません")
    for d in sorted(out["weekdays"] - src["weekdays"]):
        warnings.append(f"メモにない「{d}曜」がメールに入っています")
    return warnings
