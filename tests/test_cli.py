import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("FORGE_")}
    env.pop("NEBIUS_API_KEY", None)
    env["NO_COLOR"] = "1"
    env.update(extra)
    return env


def run_cli(args, cwd=REPO, env=None, timeout=120):
    return subprocess.run(
        [sys.executable, "-m", "forge"] + args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env or clean_env(),
        timeout=timeout,
    )


class CliTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp(prefix="forge-cli-")

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def test_demo_mock_run_exit_zero(self):
        proc = run_cli(["--demo", "--mock", "--out", self.out])
        stdout = proc.stdout.decode()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode() + stdout[-2000:])
        self.assertIn("PASS", stdout)
        self.assertIn("tests green", stdout)
        for name in ("tempconv.py", "test_tempconv.py", "README.md", "SPEC.md"):
            self.assertTrue(os.path.isfile(os.path.join(self.out, name)), name)

    def test_generated_project_really_passes_its_own_tests(self):
        run_cli(["--demo", "--mock", "--out", self.out])
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"],
            cwd=self.out,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())
        cli = subprocess.run(
            [sys.executable, "tempconv.py", "100", "C", "F"],
            cwd=self.out,
            stdout=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(cli.stdout.decode().strip(), "100C = 212F")

    def test_default_without_key_is_mock(self):
        proc = run_cli(["--demo", "--out", os.path.join(self.out, "d")])
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("mock mode", proc.stdout.decode())

    def test_real_without_key_exits_2_with_guidance(self):
        proc = run_cli(["--demo", "--real", "--out", self.out])
        self.assertEqual(proc.returncode, 2)
        err = proc.stderr.decode()
        self.assertIn("NEBIUS_API_KEY", err)
        self.assertIn("--mock", err)

    def test_mock_and_real_conflict(self):
        proc = run_cli(["--demo", "--mock", "--real"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("pick one", proc.stderr.decode())

    def test_models_offline_shows_documented_endpoint(self):
        proc = run_cli(["--models", "--mock"])
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        self.assertIn("api.tokenfactory", out)
        self.assertIn("nemotron", out.lower())

    def test_version(self):
        proc = run_cli(["--version"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("forge", proc.stdout.decode())

    def test_json_trace_written(self):
        path = os.path.join(self.out, "trace.jsonl")
        proc = run_cli(["--demo", "--mock", "--out", os.path.join(self.out, "j"), "--json", path])
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue(os.path.isfile(path))
        with open(path) as fh:
            content = fh.read()
        self.assertIn('"run_complete"', content)

    def test_jsonl_contains_no_secret(self):
        path = os.path.join(self.out, "trace.jsonl")
        run_cli(
            ["--demo", "--mock", "--out", os.path.join(self.out, "s"), "--json", path],
            env=clean_env(NEBIUS_API_KEY="super-secret-value"),
        )
        # In this run the key forces real mode... unless overridden by --mock, which
        # wins: --mock must keep working with a key present and must not leak it.
        with open(path) as fh:
            content = fh.read()
        self.assertNotIn("super-secret-value", content)


if __name__ == "__main__":
    unittest.main()
