# SUBMISSION — complete Devpost package

**Read this first.** Everything below is written to be pasted into the Devpost form.
Items marked **⚠ VERIFY** depend on a live Nebius run or a link that only the entrant can
produce — confirm them before pressing Submit. No claim in this document says the app was
run against Nebius by the person who wrote the copy; real-mode verification is the
entrant's step 1.

- Deadline: **Fri 2026-10-30, 13:00 ET** (10:00 PT). Submit by **Thu evening** if possible.
- Track: **Coding and Agentic Engineering**
- Rules quotes and eligibility: see [`RULES-NOTES.md`](RULES-NOTES.md).

---

## PART A — Devpost form fields (copy/paste)

### Project name

```text
Forge — Goal In, Tested Repo Out
```

### Elevator pitch (≤ 200 characters)

```text
One sentence in, a runnable tested repo out. Forge runs a visible write → test → repair loop on NVIDIA Nemotron via Nebius Token Factory, so code is proven, not promised.
```

### Track selection

```text
Coding and Agentic Engineering
```

### "Try it out" / demo links

| Field | Value |
| --- | --- |
| Public code repository | `⚠ VERIFY — https://github.com/<your-user>/forge-nebius-nemotron` |
| Working demo / test build URL | `⚠ VERIFY — same repo URL` (it is a test build: one command runs the whole app offline — see "Testing instructions for judges" below) |
| Video demo URL | `⚠ VERIFY — https://youtu.be/<id>` (YouTube, **Public**, under 3:00) |

### About the project

Paste the sections below into the matching Devpost fields.

#### Inspiration

Every developer now has an AI that can write code. Almost none of them can *prove* the
code works. The last mile of engineering — run it, watch it fail, read the failure, fix it,
run it again — is where AI coding tools still quietly hand the work back to a human.

I wanted to see how small and honest an agent could be if it had to earn the word "done".
Not a chat window that says the tests should pass. A loop that actually runs
`python -m unittest`, reads the traceback, patches the file, and runs it again — with every
step visible on screen. Nemotron 3 on Nebius Token Factory was a natural fit: a strong
open model behind a plain OpenAI-compatible endpoint, so the agent stays small and the
intelligence lives in the model rather than in a framework.

#### What it does

Forge turns one sentence of intent into a small, real, *passing* Python project.

You give it a goal — "build a CLI that converts temperatures between Celsius, Fahrenheit
and Kelvin, with unit tests". Forge runs a visible tool-call loop:

1. **Plans** and writes a short spec.
2. **Writes** the module and a unittest test file through `write_file`.
3. **Runs** the suite with `run_tests` — a real subprocess in a sandbox directory.
4. **Reads the failure.** In the shipped demo the first run genuinely fails: three Kelvin
   assertions catch a hardcoded offset of `273` that should be `273.15`.
5. **Repairs** the code and re-runs until the suite is green.
6. **Refuses to fake it:** `finish` is rejected while tests are failing, and a run that
   never gets green ends as `INCOMPLETE`, not "success".
7. **Reports** the transcript and a JSONL trace of every call and observation.

The output is not a snippet in a chat bubble. It is a directory with `SPEC.md`, working
code, tests that pass on their own, and a README — verified afterwards by an independent
`unittest` run and by executing the generated CLI.

It also ships an **offline mode** with a deterministic scripted backend, so judges,
reviewers or anyone without a Nebius key can run the entire app — loop, sandbox, tests and
all — in about five seconds (`make smoke`). Only the model is scripted offline; the loop
and the test execution are the real code paths.

#### How we built it

- **Python 3.9+, standard library only.** No framework, no SDK, no dependencies. The
  Nebius call is `urllib` against the OpenAI-compatible
  `POST {NEBIUS_BASE_URL}/chat/completions`, with `tools` / `tool_choice: "auto"` and the
  standard `tool_calls` → `role: tool` message protocol.
- **Five tools, deliberately.** `write_file`, `read_file`, `list_files`, `run_tests`,
  `finish`. A small tool surface keeps the model on rails and the transcript readable.
- **A real sandbox.** Every path is resolved with `realpath` and must stay inside the
  run directory (`../`, absolute paths and symlink escapes are rejected). The only process
  ever spawned is `python -m unittest` with a timeout, captured output and an environment
  scrubbed of `NEBIUS_API_KEY` and every other secret.
- **A finish gate.** The agent cannot declare success while the suite is red: `finish`
  returns an error up to twice, and if the budget runs out the result is `INCOMPLETE`.
  `unittest discover` exiting 0 with zero tests is treated as a failure, so "green" always
  means real assertions ran.
- **Two backends, one loop.** `NebiusBackend` (live Token Factory) and `MockBackend`
  (deterministic scripted trajectory) return the same OpenAI-shaped assistant messages, so
  there is no "demo path" and "production path" — the same `run_agent` code is exercised
  by both.
- **Tested, not asserted.** 47 unit/integration tests plus a 9-check smoke test. The suite
  includes a local fake OpenAI-compatible server, so the complete real-mode HTTP path —
  Bearer auth, request shape, tool-call plumbing, 401/404 handling, the full 8-step loop —
  is verified without a Nebius key.
- Built during the hackathon submission period with an AI coding agent (DeepSeek Harness)
  as the primary pair-programmer. The problem choice, architecture, requirement reading,
  review and every acceptance decision were human; the code, tests and docs were drafted
  with the agent and reviewed line by line.

#### Challenges we ran into

- **Tool-calling robustness.** Even on OpenAI-compatible endpoints, models occasionally
  narrate a JSON call instead of emitting a structured `tool_calls` array. Forge parses
  native calls first, then falls back to a fenced/bare JSON extraction, and strips that
  JSON out of the narration so the trace stays readable. Two paths, one normalised message.
- **"Green" lies.** Two ways a test loop can lie to you: no tests discovered (exit 0,
  nothing ran) and the model calling `finish` early. Both are now explicit failures —
  the second one required a finish gate with a retry budget rather than a hard block, so a
  confused model can still recover instead of deadlocking.
- **Sandboxing without a container.** No Docker, no dependencies. Path resolution plus
  environment scrubbing plus a single allowed subprocess covers the realistic failure
  modes for a coding agent that writes files and runs tests, and each one is unit-tested.
- **Verifying a provider call you can't call.** No Nebius credentials were available while
  building, so real mode was validated against a local OpenAI-compatible server speaking
  the same wire protocol. That turned a "trust me" into seven tests — and made the
  error paths (bad key, wrong model, dead host) demonstrable.
- **The demo must show failure.** A repair loop is only convincing if the failure is real.
  The reference project ships a genuine bug (`273` vs `273.15`) so the first test run
  actually fails and the fix is a real change, not theatre.

#### Accomplishments that we're proud of

- A complete agent loop and sandbox in **~1,300 lines of dependency-free Python**
  (~2,200 with the tests and smoke check) — small enough to read in one sitting, real
  enough to build and test code.
- **47 tests and a 9-check smoke test**, all passing, including the full real-mode HTTP
  path against a fake endpoint — judges can reproduce every claim on this page with
  `make smoke` and no API key.
- A **finish gate and a zero-test guard**, so the agent's "PASS" means something. That one
  design choice is the difference between a demo and a tool.
- **Every step is legible.** The terminal trace names the model, shows each tool call and
  observation, and prints the failing assertion verbatim. Nothing is hidden behind a
  spinner.
- **It actually works end to end:** the demo run produces a directory whose tests pass
  independently and whose CLI prints `100C = 212F`.

#### What we learned

- The model is the easy part. **Verification is the product.** Once the agent could run
  tests, the interesting engineering moved to what counts as proof: which exit codes,
  which "green" is a lie, when to refuse a `finish`.
- **Small tool surfaces beat clever frameworks.** Five tools and a strict protocol got
  more reliable behaviour than a larger API ever would, and the whole loop fits in one
  readable file.
- **Failure paths deserve as much design as the happy path.** The most valuable 40 lines
  in the project are the ones that stop the agent from claiming success.
- **An OpenAI-compatible endpoint is a superpower for small agents.** With Nemotron on
  Token Factory, a 1,000-line agent gets frontier-model tool use without a client library —
  which is exactly what makes the base URL + model id the only two things that can break.
- Honest offline modes make AI projects *reviewable*: a deterministic backend turns "watch
  my video" into "run this in five seconds".

#### What's next for Forge

- **Multi-language targets** (Node, Go) with the same sandbox contract — the tool loop is
  language-agnostic; only the test-runner command changes.
- **A web UI** streaming the same JSONL trace live, so a team can watch and interrupt a run.
- **Nebius Serverless Endpoints deployment** for the agent service itself, and Serverless
  Jobs for offline batch runs — the natural next step given the Token Factory footprint.
- **Repo-aware mode:** point Forge at an existing repository instead of an empty sandbox,
  with a diff-based tool (`edit_file`) and a real git branch per run.
- **Nemotron model routing:** Nano for fast file writes, Super for repair reasoning, with a
  cost/latency readout per run — a concrete, measurable use of the model family.

### Testing instructions for judges (paste into the submission's testing notes)

```text
No API key needed to verify this project.

  git clone <repo-url> && cd forge-nebius-nemotron
  make smoke
  make demo

`make smoke` runs 9 end-to-end checks (47 unit tests, a full agent run, the generated
project's own test suite, its CLI, the JSONL transcript, and the real-mode HTTP path
against a local OpenAI-compatible server). Expected: "SMOKE PASS: 9/9 checks green".

`make demo` runs the agent and writes a tested project into ./build. Then:
  cd build && python3 -m unittest discover -s . -p 'test_*.py' && python3 tempconv.py 100 C F

Real mode (only with a Nebius Token Factory key):
  export NEBIUS_API_KEY=...
  python3 -m forge --models --real          # confirm the Nemotron model id
  python3 -m forge "Build a CLI that converts temperatures between C, F and K, with unit tests" --real

Demo video: <youtube-url>
```

### "Built with" tags

```text
python, Nebius Token Factory, NVIDIA Nemotron, NVIDIA Nemotron 3 Super, LLM agents,
agentic coding, tool calling, OpenAI-compatible API, unittest, urllib, JSONL, MIT License
```

### Bonus: feedback submission draft (Most Valuable Feedback — $100 + swag)

> Only submit this if it matches what you actually experienced while building — edit
> anything that is not true for you. Specific, constructive beats flattering.

```text
What worked well
- Token Factory's OpenAI-compatible surface is the right call: an agent with zero SDK
  dependencies worked on the first try (base_url + model id + /chat/completions + tools).
- The Nemotron 3 page shows a runnable code sample with the exact base_url and model id,
  which removed all guesswork.
- Nemotron 3 Super handled multi-step tool calling (write file → run tests → repair) with
  good instruction-following; the failing-test output was used correctly as feedback.

What would help builders
- The docs sample shows chat completions but no tool-calling example. A canonical
  tools/tool_choice/tool_calls example (request + response JSON) would save the first hour
  of every agent project.
- Please document the full model id list (Nano / Super / Ultra) on the same page as the
  sample, and indicate which ids are enabled by default for new accounts.
- A clear statement of the free-credit amount and whether a payment method is required to
  create a key would let builders plan. (I could not find this.)
- Listing context window and per-model rate limits in GET /v1/models (or a linked table)
  would make model routing -- Nano for cheap steps, Super for hard ones -- easy to
  implement from code instead of from docs.
- If there are per-account model allow-lists, returning that list from the API (or a
  descriptive 403) would turn "404 on a model id" into a fixable error.
```

---

## PART B — Demo video script (< 3:00 hard limit)

Target **2:45**. One take with a live real-mode run is ideal; if the endpoint is slow,
record it, then trim waiting with a labelled 2× speed-up ("2× speed") — never fake output.
Movie audio only from your microphone; **no music**, no other companies' logos or UIs.

Screen: terminal only, dark theme, 16–18 pt font, ~1280×720 window. Clear the terminal
immediately before recording. Close mail/chat; no personal data visible. Use a repo path
with no personal name in it if convenient.

Pre-roll checklist before you hit record:

```bash
cd contest-entries/nebius-nvidia
rm -rf build build-real            # so file writes are visible
export NEBIUS_API_KEY='...'
python3 -m forge --models --real   # confirm the model id works BEFORE recording
clear
```

| Time | On screen (what you do) | Say (roughly) |
| --- | --- | --- |
| 0:00–0:12 | Title card or clean terminal with the repo open: `Forge — Goal In, Tested Repo Out`. | "Every AI coding tool can write code. The hard part is proving it works. This is Forge: you give it a goal, and it returns a repository whose tests actually pass." |
| 0:12–0:32 | Show `README` one-pager / the loop diagram, then run `python3 -m forge --models --real`. Highlight the Nemotron id and `Token Factory`. | "Under the hood, NVIDIA Nemotron 3 Super on Nebius Token Factory. Plain OpenAI-compatible endpoint — no SDK, no framework. Here's the live model list from my key, and here's the exact model Forge will use." |
| 0:32–0:50 | Type the real-mode command with the goal, press Enter. Header appears: `backend : Nebius Token Factory`, `model : ...`. | "One sentence of intent. Forge gives the model five tools: write file, read file, list files, run tests — and a finish call. Then it just loops: act, observe, repeat. Every step is on screen." |
| 0:50–1:25 | Let the run play. Point at step 2/3 (`write_file`), then the failing `run_tests` — the `273.0 != 273.15` assertion. | "It writes a spec, the module, and a unittest file. Now it runs the suite — and this is the part I care about: it genuinely fails. Three Kelvin assertions catch an offset of 273 that should be 273.15. Forge reads that traceback as feedback." |
| 1:25–1:50 | Step 5: `write_file` patch, step 6: `run_tests` green, step 8: `finish`, then `PASS ... tests green`. | "It patches the constant, re-runs, and now it's green. Notice it couldn't have claimed success — finish is refused while tests are red. A run that never gets green ends as INCOMPLETE, not done." |
| 1:50–2:10 | `cd build && python3 -m unittest discover -s . -p 'test_*.py' -v`, then `python3 tempconv.py 100 C F` → `100C = 212F`. Show `find build` file list. | "Here's the output, verified independently: the tests pass when I run them myself, and the generated CLI works. Real files, real tests, real exit codes." |
| 2:10–2:30 | Show the sandbox guard briefly: `python3 -m forge --demo --mock` one-liner or `make smoke` run output `SMOKE PASS: 9/9`. | "It's built to be checked: path traversal blocked, the test subprocess gets a scrubbed environment, and `make smoke` proves the whole thing offline — judges don't need a key to run it. Real mode was validated against the same HTTP protocol." |
| 2:30–2:45 | Slides or terminal: who it's for + repo URL. | "Forge is for the moment after the code is written — proof that it runs. Built with Nemotron on Nebius Token Factory, MIT licensed. Repo and instructions are linked below." |

**Hard rules for the video:** under 3:00, uploaded to YouTube and **Public**, English,
shows the project actually running, no third-party trademarks/logos, no copyrighted music.

**Fallback if the live endpoint fails on recording day:** record mock mode
(`python3 -m forge --demo --mock`), and say on camera "this is the offline scripted backend
so the recording isn't blocked on a network call — real mode is the same loop." Then submit
with the live real-mode clip if you can get one; honesty beats a polished fake.

---

## PART C — USER-ONLY checklist (accounts, video, submit)

Nothing here can be done by anyone else — it involves your identity, your accounts and your
voice. Estimated total: **~95 min** (range 85–110).

### Phase 1 — Nebius key (do this first; it is the only real risk)

- [ ] **1. Create/sign in to a Nebius account** — <https://nebius.com> → Sign up. Use your
      own email; verify. *(10 min)*
- [ ] **2. Open Token Factory** in the console and **create an API key**; copy it once.
      *(3 min)*
- [ ] **3. Export it and prove it works:**
      `export NEBIUS_API_KEY='...'` then `python3 -m forge --models --real` → you should
      see a list of model ids. If the default Nemotron id is missing, copy an exact id into
      `export NEBIUS_MODEL='...'`. *(2 min)*
- [ ] **4. Do one live real-mode run** and confirm it ends `PASS ... tests green`. Save the
      terminal output (it is evidence for the write-up). *(5 min)*

> If step 1 or 2 is blocked (card required, region, verification delay), switch to the
> fallback now: record the mock-mode video and label it honestly in the submission. Do not
> let the account step eat the deadline.

### Phase 2 — public repo

- [ ] **5. Create a public GitHub repo** (no README template, no .gitignore — you have both)
      named `forge-nebius-nemotron`, then push (§4 of `RUNBOOK.md` has the exact commands).
      *(8 min)*
- [ ] **6. Confirm on the repo page:** "MIT license" appears in the **About** section,
      repo is **Public**, and `README.md` renders with the quickstart. Open it in a
      logged-out browser to check what a judge sees. *(4 min)*
- [ ] **7. Add topics** in About: `agentic-coding`, `nvidia-nemotron`,
      `nebius-token-factory`, `llm-agents`, `python`. *(1 min)*

### Phase 3 — video

- [ ] **8. Rehearse once** off-camera with the Part B script, then record 2 takes;
      keep the best one under 3:00. *(20–30 min)*
- [ ] **9. Trim/export** to ≤ 3:00 (QuickTime trim or any editor), 1080p. No music.
      *(5 min)*
- [ ] **10. Upload to YouTube**: title `Forge — Goal In, Tested Repo Out (Nebius x NVIDIA
      Hackathon)`, description = 2–3 sentences + repo link, visibility **Public**,
      **not** "made for kids". Copy the watch URL. *(10 min)*

### Phase 4 — Devpost

- [ ] **11. Join the hackathon**: open <https://nebiusglobalaihackathon.devpost.com/> and
      click **Join Hackathon** (creates/logs in a Devpost account). *You must accept the
      rules yourself.* *(4 min)*
- [ ] **12. Start the submission** → "Enter a Submission"; fill Project name, elevator
      pitch, track, pasting from Part A. *(8 min)*
- [ ] **13. Add the links**: public repo URL, the same repo as the "working demo / test
      build" (testing instructions from Part A go in the testing field), YouTube URL.
      *(3 min)*
- [ ] **14. Paste the About sections**, and the "Built with" tags. *(5 min)*
- [ ] **15. Fill the feedback section** with the Part A draft (edit it to be true for you —
      it is worth $100 + swag, and generic feedback loses). *(10 min)*
- [ ] **16. Review the form once** against the requirements list in `RULES-NOTES.md` §3:
      public repo ✓ license visible ✓ README ✓ video < 3:00 and public ✓ track selected ✓
      feedback provided ✓ English ✓ *(3 min)*
- [ ] **17. Submit.** Screenshot the confirmation page / note the submission URL.
      *(1 min)*

### Phase 5 — after submitting

- [ ] **18. Leave the repo public and unchanged** through judging (Dec 1–15, 2026); you may
      not modify the submission after the deadline.
- [ ] **19. If you win anything**, expect an affidavit/W-9 (US) within 10 business days of
      being contacted. Keep an eye on the Devpost account email.

---

## PART D — pre-submit QA (60 seconds, do it on the live pages)

| Check | Where |
| --- | --- |
| Repo loads logged out, shows MIT in About | GitHub repo in a private window |
| `make smoke` → `SMOKE PASS: 9/9` from a fresh clone | `git clone` into `/tmp` and run |
| Video is **Public**, **< 3:00**, plays while logged out | YouTube URL in a private window |
| Devpost form: repo + demo + video URLs have no typos | submission form |
| Track = Coding and Agentic Engineering | submission form |
| Text mentions **NVIDIA Nemotron** + **Nebius Token Factory** explicitly | description |
| Feedback section non-empty | submission form |
| Submitted before **13:00 ET Fri 2026-10-30** | confirmation page timestamp |
