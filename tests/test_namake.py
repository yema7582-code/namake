from pathlib import Path

from namake.core import digest, puff, shrink
from namake.guard import check, facts
from namake.llm import FakeLLM
from namake import cli

GOOD = "山田様\n\nいつもお世話になっております。中崎です。\n\n火曜14時で承知いたしました。資料は明日お送りいたします。\n\nよろしくお願いいたします。\n\n中崎"


def test_facts_reads_numbers_and_weekdays():
    f = facts("火曜14時OK、金NG。150個")
    assert f["numbers"] == {"14", "150"}
    assert f["weekdays"] == {"火", "金"}


def test_facts_ignores_month_words():
    assert facts("来月は10月に")["weekdays"] == set()


def test_full_width_and_clock_forms_match():
    assert check("火曜14時OK", "火曜日の１４:００で承知いたしました") == []


def test_guard_passes_faithful_mail():
    assert check("火曜14時OK。資料は明日送る。", GOOD, "中崎", "山田様") == []


def test_guard_flags_invented_and_missing_facts():
    bad = "山田様\n水曜15時でお願いいたします。"
    w = check("火曜14時OK", bad)
    assert any("14" in x for x in w)
    assert any("15" in x for x in w)
    assert any("水曜" in x for x in w)
    assert any("火曜" in x for x in w)


def test_puff_builds_fewshot_prompt_and_returns_warnings():
    llm = FakeLLM([GOOD])
    d = puff(llm, "火曜14時OK。資料は明日送る。", "山田様", "中崎")
    assert d.text == GOOD and d.warnings == []
    msgs = llm.calls[0]
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["content"].endswith("メモ: 火曜14時OK。資料は明日送る。")
    assert sum(m["role"] == "assistant" for m in msgs) >= 2


def test_shrink_keeps_only_two_labelled_lines():
    llm = FakeLLM(["はい、要約します。\n用件: 請求書の再送\nやること: 金曜までに送る\n以上です"])
    assert shrink(llm, "長いメール") == "用件: 請求書の再送\nやること: 金曜までに送る"


def test_digest_puts_action_items_first(tmp_path: Path):
    (tmp_path / "a.txt").write_text("お知らせです", encoding="utf-8")
    (tmp_path / "b.eml").write_bytes(
        "From: kimura@example.com\nSubject: =?utf-8?b?6KuL5rGC5pu4?=\nContent-Type: text/plain; charset=utf-8\n\n請求書を送ってください\n".encode()
    )
    (tmp_path / "skip.pdf").write_bytes(b"%PDF")
    llm = FakeLLM(["用件: お知らせ\nやること: なし", "用件: 請求書\nやること: 請求書を送る"])
    out = digest(llm, tmp_path)
    assert out.startswith("# 朝のメールまとめ (2通、対応が要るのは1通)")
    assert out.index("請求書を送る") < out.index("お知らせ\n")
    assert "kimura@example.com" in out
    assert len(llm.calls) == 2


def test_cli_exit_code_signals_warnings(monkeypatch, capsys):
    monkeypatch.setenv("NAMAKE_FAKE", "山田様\n水曜にお伺いします。")
    assert cli.main(["puff", "火曜OK", "--to", "山田様", "--from", "中崎"]) == 1
    assert "水曜" in capsys.readouterr().err
    monkeypatch.setenv("NAMAKE_FAKE", "山田様\n火曜で承知いたしました。")
    assert cli.main(["puff", "火曜OK", "--to", "山田様", "--from", "中崎"]) == 0


def test_puff_retries_until_guard_is_happy():
    llm = FakeLLM(["山田様\n水曜15時で。", GOOD])
    d = puff(llm, "火曜14時OK。資料は明日送る。", "山田様", "中崎")
    assert d.text == GOOD and d.warnings == [] and len(llm.calls) == 2


def test_puff_keeps_least_bad_draft_after_all_tries():
    llm = FakeLLM(["水曜15時", "火曜15時", "水曜16時"])
    d = puff(llm, "火曜14時OK", "山田様", "中崎", tries=3)
    assert d.text == "火曜15時" and len(llm.calls) == 3


def test_digest_overrules_model_when_mail_asks_by_a_date(tmp_path: Path):
    (tmp_path / "x.txt").write_text("請求書を28日までにお送りいただけますと幸いです。", encoding="utf-8")
    (tmp_path / "y.txt").write_text("セールを31日まで開催中です。", encoding="utf-8")
    llm = FakeLLM(["用件: 請求書\nやること: なし", "用件: セール\nやること: なし"])
    out = digest(llm, tmp_path)
    assert "対応が要るのは1通" in out
    assert "本文を確認" in out and out.index("## x") < out.index("## y")
