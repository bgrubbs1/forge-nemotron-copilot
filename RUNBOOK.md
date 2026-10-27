# RUNBOOK — exact commands

Everything runs from the repository root:

```bash
cd contest-entries/nebius-nvidia
```

Python 3.9+ only. No `pip install`, no virtualenv, no Node, no network for mock mode.
Confirmed working on macOS 14 with Python 3.9.6 and Node 22 available (Node unused).

---

## 0. Preflight (10 seconds)

```bash
python3 --version                  # expect 3.9.x or newer
ls                                 # expect Makefile smoke.py forge/ tests/ examples/
```

Expected repo root contents:

```text
LICENSE  Makefile  README.md  RULES-NOTES.md  RUNBOOK.md  SUBMISSION.md
forge/  tests/  examples/  smoke.py
```

---

## 1. The full offline proof (recommended first command)

```bash
make smoke
```

Expected output (9/9):

```text
======================================================================
 FORGE SMOKE TEST  -  offline, no API key, no network
======================================================================
  PASS  python >= 3.9                                  3.9.6
  PASS  all modules byte-compile                        16 files
  PASS  unit test suite                                Ran 47 tests ...
  PASS  mock-mode agent run (end to end)               8 steps, 4 files, 2 test runs
  PASS  generated project passes its own tests         Ran 7 tests ...
  PASS  generated CLI output is correct                100C = 212F
  PASS  JSONL transcript well formed, no secrets       25 events
  PASS  real-mode HTTP path (local fake endpoint)      8 OpenAI-compatible HTTP calls, green
  PASS  real mode needs a key (fails safely)           exit 2 + guidance
----------------------------------------------------------------------
 SMOKE PASS: 9/9 checks green
```

If any check fails, stop and read the FAIL line — each check prints the assertion or
captured output that broke it. `FORGE_SMOKE_VERBOSE=1 make smoke` adds tracebacks.

```bash
make test     # 47 unit tests only (about 5 s)
```

---

## 2. Mock-mode demo (for screen recording / offline judges)

```bash
rm -rf build                 # start clean so the file writes are visible
make demo                    # == NO_COLOR=1 python3 -m forge --demo --mock --out build
```

Then show what was actually produced:

```bash
find build -type f | sort
cd build && python3 -m unittest discover -s . -p 'test_*.py' -v
python3 tempconv.py 100 C F        # -> 100C = 212F
cd ..
```

Notes:
- `NO_COLOR=1` in `make demo` keeps the terminal output plain (better for recording).
  Omit it (run `python3 -m forge --demo` directly) to get the colored trace.
- Want a non-demo goal in mock mode? The scripted backend always builds the reference
  project; the goal text is echoed but the trajectory is fixed. This is documented in
  the README as mock mode's one limitation. Use `--real` for arbitrary goals.

---

## 3. Real mode — NVIDIA Nemotron on Nebius Token Factory

### 3.1 Get a key (user-only step)

1. Create a Nebius account / sign in: <https://nebius.com> (UNVERIFIED whether a card is
   required — do this early).
2. Open **Token Factory** in the console and create an **API key**.
3. Copy it once — most consoles show it only once.

### 3.2 Export the key (never commit it)

```bash
export NEBIUS_API_KEY='paste-the-key-here'
# optional overrides:
# export NEBIUS_BASE_URL='https://api.tokenfactory.us-central1.nebius.com/v1'
# export NEBIUS_MODEL='nvidia/nemotron-3-super-120b-a12b'
```

Sanity-check the key and see the real model ids your account can use:

```bash
python3 -m forge --models --real
```

Expected: `GET https://api.tokenfactory.us-central1.nebius.com/v1/models` followed by a
list of model ids, with `<-- configured NEBIUS_MODEL` next to the default. If you see
`WARNING: your NEBIUS_MODEL ... is not in the list`, copy an exact id from the list:

```bash
export NEBIUS_MODEL='nvidia/<exact-id-from-the-list>'
```

### 3.3 Run it

```bash
rm -rf build-real
python3 -m forge "Build a CLI that converts temperatures between Celsius, Fahrenheit and Kelvin, with unit tests" \
  --real --out build-real --json build-real.jsonl
```

Expected: the header shows `backend : Nebius Token Factory`, `model : ...`, `base_url : ...`,
then 4–8 steps ending in `PASS ... tests green`. Exit code 0.

Verify the output independently:

```bash
cd build-real && python3 -m unittest discover -s . -p 'test_*.py' -v && python3 tempconv.py 0 C K
# -> 0C = 273.15K
```

### 3.4 What "real mode" sends

- `POST {NEBIUS_BASE_URL}/chat/completions`
- Headers: `Authorization: Bearer $NEBIUS_API_KEY`, `Content-Type: application/json`
- Body: `{model, messages, tools: [...5 tools...], tool_choice: "auto", temperature: 0.2, max_tokens: 2048}`
- Assistant `tool_calls` are echoed back, followed by `{"role": "tool", "tool_call_id": ...}`
  observations — the standard OpenAI-compatible tool loop.

### 3.5 Proof without a key (what the tests do)

`tests/fake_nebius_server.py` is a local OpenAI-compatible server. The suite points
`NEBIUS_BASE_URL` at it and runs the **entire** real-mode path over HTTP:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
# includes: test_real_mode.RealModeHttpTest (7 tests)
```

To watch it manually:

```bash
python3 tests/fake_nebius_server.py     # prints a listening URL + fake key
# in another shell:
NEBIUS_API_KEY=test-key-not-real NEBIUS_BASE_URL=<printed-url> NO_COLOR=1 \
  python3 -m forge --demo --real --out /tmp/forge-fake
```

A captured run of that is `examples/sample-real-mode-run.txt`.

---

## 4. Publish the repository (user-only step)

```bash
cd contest-entries/nebius-nvidia
git init -b main
git add -A
git commit -m "Forge: agentic engineering copilot on Nebius Token Factory + NVIDIA Nemotron"
git remote add origin git@github.com:<your-user>/forge-nebius-nemotron.git
git push -u origin main
```

Then, on GitHub:

1. Repo **Settings → General → Danger Zone → Change visibility → Public**.
2. **Add license**: repo page → "Add file" is not needed (LICENSE is committed), but the
   About sidebar must show it. If it does not: **Settings → General → Features → License**
   or add via the repo's "Add license" flow and commit — then confirm **"MIT license"**
   appears in the right-hand **About** panel.
3. About panel: add the description and topics, e.g.
   `agentic-coding, nvidia-nemotron, nebius-token-factory, python, llm-agent`.
4. Confirm a fresh browser (logged out) can read the repo — that is what judges see.

Never commit `build/`, `build-real/`, `*.jsonl` (already in `.gitignore`) and never commit
the key.

---

## 5. Record and upload the demo (user-only step)

Setup:

- Terminal: dark theme, font 16–18 pt, window ~1280×720, no other tabs visible.
- Clear the screen and `rm -rf build build-real` before recording so the writes are visible.
- Close mail/chat windows; no personal data, no third-party logos or copyrighted music.
- Preferred: QuickTime Player → **File → New Screen Recording** (macOS), then record only
  the terminal region. 1080p or better, 30 fps.

Run order (see `SUBMISSION.md` for the scene-by-scene script with narration):

```bash
export NEBIUS_API_KEY='...'
python3 -m forge --models --real          # scene 1: prove Nemotron on Token Factory
python3 -m forge --demo --real --out build   # scene 2: the live loop, ends PASS
cd build && python3 -m unittest discover -s . -p 'test_*.py' && python3 tempconv.py 100 C F
```

If a live model call is slow or flaky on the day, record mock mode as a labelled backup
clip and say so on camera — never present a scripted run as a live model run.

Upload: YouTube → **Visibility: Public** (not Unlisted — the rules require "publicly
visible"), **not** "made for kids", no music. Copy the watch URL into the Devpost form.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ERROR: real mode needs an API key` (exit 2) | `NEBIUS_API_KEY` unset in this shell | `export NEBIUS_API_KEY=...` or use `--mock` |
| `authentication failed (HTTP 401)` | bad/expired key, or key from a different platform | regenerate the Token Factory key; re-export; check the base URL matches the key's platform |
| `HTTP 404 ... the base URL or model id may be wrong` | wrong `NEBIUS_BASE_URL` path or model id not enabled | `python3 -m forge --models --real`, copy an exact id into `NEBIUS_MODEL`; ensure base URL ends in `/v1` |
| `HTTP 429` repeatedly | rate limit | lower `FORGE_MAX_STEPS`, wait, retry; the client already retries 429/5xx twice |
| Request hangs then `network error ... timed out` | slow endpoint / no egress | increase `FORGE_TIMEOUT=240`; check VPN/proxy |
| `INCOMPLETE — stopped after 12 steps without finish()` | goal too big for the budget | raise `FORGE_MAX_STEPS=20` or give a smaller goal ("one module + tests") |
| `ERROR: not finishing - the test suite has not passed yet` | model tried to shortcut | expected behaviour: Forge refuses to fake success; it keeps looping, and after two refusals reports `INCOMPLETE` |
| `path escapes the sandbox` / `'..' is not allowed` | model tried to write outside | expected; the tool returns the error to the model, which retries inside the sandbox |
| `no test files were discovered` counted as failure | empty sandbox / tests not written yet | expected: a green run requires at least one real test |
| Colors missing | `NO_COLOR` set or output piped | run without `NO_COLOR=1` in an interactive terminal |
| `make smoke` fails on the port check | local firewall blocking 127.0.0.1 loopback | allow Python to bind loopback; that check needs it |
| `ModuleNotFoundError: forge` | running from the wrong directory | `cd contest-entries/nebius-nvidia` first (all commands assume repo root) |
| Recording shows scrollback noise | terminal not cleared | `clear` (or `Cmd-K`) immediately before the run |

Reset everything:

```bash
make clean          # removes build/, build-real/, __pycache__
git status          # should be clean before you commit
```

---

## 7. Time budget for the entrant

| Step | Minutes |
| --- | --- |
| Nebius account + Token Factory key | 10–15 |
| `python3 -m forge --models --real` + first real run | 5 |
| Public GitHub repo + license in About | 10–15 |
| Record video (2 takes) | 20–30 |
| Upload to YouTube (public) | 10 |
| Join hackathon on Devpost + submit form | 20–25 |
| Feedback section | 10 |
| **Total** | **~85–110 min** |

Deadline: **Fri 2026-10-30, 13:00 ET**. Aim to submit by **Thu 2026-10-29 evening ET**.

---

## 8. Evidence log (what was actually run, 2026-10-27)

| Command | Result |
| --- | --- |
| `make test` | `Ran 47 tests ... OK` |
| `make smoke` | `SMOKE PASS: 9/9 checks green` |
| `make demo` | `PASS 8 steps, 4 file(s), 2 test run(s), tests green`, exit 0 |
| generated project | `Ran 7 tests ... OK`; `python3 tempconv.py 100 C F` → `100C = 212F` |
| real-mode HTTP path | 8 OpenAI-compatible calls to a local fake endpoint, green (`examples/sample-real-mode-run.txt`) |
| live Nebius call | **not run** — no Nebius credentials available; see `RULES-NOTES.md` §8 |
