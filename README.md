# namake 🦥

*namake* comes from ナマケモノ, the Japanese word for sloth. It does the two most tiring parts of Japanese work email for you, on your own laptop, with no internet:

- **puff**: you type `火曜14時OK、資料は明日送る` and get back a polite email you can actually send.
- **shrink**: a five-paragraph keigo email becomes two lines: what they want, and what you have to do.
- **digest**: point it at a folder of exported mail before bed and read one short note in the morning, with the mails that need action on top.

It runs **Gemma 3 1B** (open weights, about 800 MB) through llama.cpp on the CPU. Nothing is sent anywhere.

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e . --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
curl -L -o models/gemma-3-1b-it-Q4_K_M.gguf \
  https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf
```

## Use

```bash
export NAMAKE_NAME=中崎
namake puff "木曜NG、来週の水曜なら午前中いける" --to 佐藤様
namake shrink examples/inbox/03-mitsumori.txt
namake digest examples/inbox > morning.md
```

`puff` exits with code 1 and prints warnings to stderr when the draft's dates, weekdays or numbers don't match your memo, so you can wire it into a script and stop when something looks off.

## How it keeps a 1B model honest

A model this small is fast and private, but it slips. Three cheap tricks do most of the work:

1. **Few-shot over instructions.** Two worked examples taught it that `OK` means "I accept" better than any sentence of instructions did.
2. **A fact guard** (`namake/guard.py`). Every number and weekday in your memo must appear in the email, and nothing new may appear. If the check fails, namake asks again at a slightly higher temperature, up to three times, and keeps the draft with the fewest problems.
3. **A regex seatbelt for the digest.** If a mail asks for something by a date and the model still says "nothing to do", the digest says so and moves it up.

It still makes mistakes the guard can't see (see `examples/sample_run.txt`). Read before you send. Being lazy is fine; being reckless isn't.

## Tests

```bash
pip install pytest && python -m pytest -q
```

The tests use a fake model, so they run in well under a second without downloading anything.

## License

MIT. Gemma is provided under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
