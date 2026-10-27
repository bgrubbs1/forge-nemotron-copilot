# Devpost submission setup — Nebius x NVIDIA Global AI Hackathon

**Your submission URL:** https://devpost.com/submit-to/30790-nebius-x-nvidia-global-ai-hackathon/manage/submissions
**Hackathon page:** https://nebiusglobalaihackathon.devpost.com/ · **Deadline: Fri 2026-10-30, 13:00 ET (10:00 PT)** — hard cutoff, submit Thursday evening if possible.
**Track:** Coding and Agentic Engineering · **Prize pool:** $50,000 (Grand $20k, 2nd $10k, 3rd $6k, track/tech prizes) · Free entry, 18+, US eligible.

## GitHub side — DONE ✅
- Public repository: **https://github.com/bgrubbs1/forge-nemotron-copilot** — all source + instructions, MIT `LICENSE` at root (detected by GitHub), README rewritten as a project page (Inspiration / What it does / How we built it / Challenges / Accomplishments / What we learned / What's next / Built with), 1280×720 cover at `docs/cover.png`, repo description + topics set.
- Judges can reproduce every claim with **no API key**: `make smoke` → "SMOKE PASS: 9/9 checks green".
- Rules verified 2026-10-27 (see `RULES-NOTES.md`): "a working software application that runs on either Nebius Token Factory or Nebius AI Cloud and uses at least one NVIDIA open source model"; public repo + open-source license; README with setup instructions; **public YouTube video < 3 min**.

## Only you can do these (they're the submission blockers)
1. **Nebius account + Token Factory API key** (10–15 min): sign up at https://nebius.com/ (Token Factory), create an API key. `export NEBIUS_API_KEY=...`
2. **One live run** (5 min) — required so the submission can honestly claim it runs on Nebius + Nemotron:
   ```bash
   cd contest-entries/nebius-nvidia
   python3 -m forge --models --real          # confirms your key + the Nemotron model id
   python3 -m forge "Build a CLI that converts temperatures between C, F and K, with unit tests" --real
   ```
   If real mode errors, paste the error here and I'll debug before you record.
3. **Record the demo video** (20–30 min): max **3:00**, terminal + browser, showing the live run (goal → write → failing test → repair → passing test), the model name `nvidia/nemotron-3-super-120b-a12b`, and a brief "how it was built" shot. Upload to **YouTube, Public**. Script + shot list: `SUBMISSION.md` Part B.
4. **Devpost** (~20 min): see below.

## Devpost click-through (~20 min, after video + live run)
1. Open the manage URL; log in with **GitHub** if prompted (you already joined the hackathon).
2. **Create project → Import from GitHub** → authorize Devpost's GitHub app (read-only) → select `bgrubbs1/forge-nemotron-copilot`, **or** create manually and paste from `SUBMISSION.md` → "About the project".
3. Fill / verify:
   - **Project name:** `Forge — Goal In, Tested Repo Out`
   - **Elevator pitch (≤200 chars):** `One sentence in, a runnable tested repo out. Forge runs a visible write → test → repair loop on NVIDIA Nemotron via Nebius Token Factory, so code is proven, not promised.`
   - **Track:** `Coding and Agentic Engineering`
   - **Code repository:** `https://github.com/bgrubbs1/forge-nemotron-copilot`
   - **Demo video URL:** the YouTube link (must be Public)
   - **About the project:** paste the Inspiration / What it does / How we built it / Challenges / Accomplishments / What we learned / What's next from `SUBMISSION.md` Part A.
   - **Built with:** `python, Nebius Token Factory, NVIDIA Nemotron, NVIDIA Nemotron 3 Super, LLM agents, agentic coding, tool calling, OpenAI-compatible API, unittest, urllib, JSONL, MIT License`
   - **Testing instructions for judges:** paste the block below.
   - **Thumbnail / gallery image:** upload `docs/cover.png`.
   - Optional bonus: "Most Valuable Feedback" draft in `SUBMISSION.md` (only if it matches your real experience).
4. **Submit** and verify the confirmation; then **submit the feedback bonus** if you have time. Deadline Fri 13:00 ET — do not cut it close.

## Testing instructions for judges (paste into the submission)
```text
No API key needed to verify this project.

  git clone https://github.com/bgrubbs1/forge-nemotron-copilot && cd forge-nemotron-copilot
  make smoke
  make demo

`make smoke` runs 9 end-to-end checks (47 unit tests, a full agent run, the generated
project's own test suite, its CLI, the JSONL transcript, and the real-mode HTTP path
against a local OpenAI-compatible server). Expected: "SMOKE PASS: 9/9 checks green".

`make demo` runs the agent and writes a tested project into ./build. Then:
  cd build && python3 -m unittest discover -s . -p 'test_*.py' && python3 tempconv.py 100 C F

Real mode (only with a Nebius Token Factory key):
  export NEBIUS_API_KEY=...
  python3 -m forge --models --real
  python3 -m forge "Build a CLI that converts temperatures between C, F and K, with unit tests" --real

Demo video: <youtube-url>
```

## Notes
- **Do not overclaim:** real-mode was validated here against an OpenAI-compatible test server, not live Nebius (no key was available at build time). After your live run works, the claim is true; if it fails, tell me before submitting.
- Public repo means no Devpost private-repo sharing exception is needed.
- Eligibility: 18+, US okay; no purchase necessary. Winners provide affidavit/W-9 only at prize time.
- After submitting, optionally set the repo homepage to the Devpost project URL:
  `gh repo edit bgrubbs1/forge-nemotron-copilot --homepage <devpost-project-url>`
