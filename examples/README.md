# Examples

Both files are real captured runs from this repository, not mock-ups.

| File | What it is |
| --- | --- |
| `sample-run.txt` | `python3 -m forge --demo --mock --out build` — the offline scripted backend. Shows the full tool-call loop including a genuine failing test run and the repair. |
| `sample-real-mode-run.txt` | `python3 -m forge --demo --real --out /tmp/forge-real-sample` with `NEBIUS_BASE_URL` pointed at `tests/fake_nebius_server.py` (a local OpenAI-compatible server). Proves the real-mode HTTP path — same loop, same trace — without a Nebius key. The model script is served over HTTP by the fixture. |

To reproduce:

```bash
cd contest-entries/nebius-nvidia
NO_COLOR=1 python3 -m forge --demo --mock --out /tmp/forge-demo-build > examples/sample-run.txt 2>&1
python3 - <<'PY'
import os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "tests")
from fake_nebius_server import FakeNebiusServer
from forge.__main__ import main
with FakeNebiusServer() as srv:
    os.environ.update(NEBIUS_API_KEY=srv.key, NEBIUS_BASE_URL=srv.base_url,
                      NEBIUS_MODEL="nvidia/nemotron-3-super-120b-a12b", NO_COLOR="1")
    raise SystemExit(main(["--demo", "--real", "--out", "/tmp/forge-real-sample"]))
PY
```

With a real `NEBIUS_API_KEY`, the second command produces the same trace driven by
Nemotron on Nebius Token Factory — that is the run to record for the demo video.
