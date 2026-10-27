"""Canned content for the scripted (offline) demo backend.

This is the reference project that ``--mock`` builds: a tiny temperature
conversion module. Two versions are provided on purpose - the first one has a
real bug (Kelvin offset 273 instead of 273.15) so the demo shows the agent
running tests, seeing a genuine failure, patching the code, and re-running until
green. Nothing here is faked: the test runner really executes and really fails.
"""

from __future__ import annotations

SPEC_MD = """# tempconv

Goal: a Python CLI that converts temperatures between Celsius, Fahrenheit and
Kelvin.

## Scope
- `convert(value, src, dst)` -> rounded float
- `to_celsius` / `from_celsius` helpers
- `main(argv)` CLI: `python tempconv.py 100 C F` -> `100C = 212F`
- stdlib only, no dependencies
- test file `test_tempconv.py` covering C<->F, C<->K, round trips and bad units
"""

TEMPconv_V1 = '''# tempconv.py -- temperature conversion helpers (Python stdlib only)

KELVIN_OFFSET = 273  # BUG: should be 273.15


def to_celsius(value, unit):
    """Convert `value` expressed in `unit` to Celsius."""
    unit = unit.upper()
    if unit == "C":
        return float(value)
    if unit == "F":
        return (float(value) - 32.0) * 5.0 / 9.0
    if unit == "K":
        return float(value) - KELVIN_OFFSET
    raise ValueError("unknown unit: %r" % (unit,))


def from_celsius(value, unit):
    """Convert a Celsius `value` to `unit`."""
    unit = unit.upper()
    if unit == "C":
        return float(value)
    if unit == "F":
        return float(value) * 9.0 / 5.0 + 32.0
    if unit == "K":
        return float(value) + KELVIN_OFFSET
    raise ValueError("unknown unit: %r" % (unit,))


def convert(value, src, dst):
    """Convert `value` from unit `src` to unit `dst`, rounded to 4 places."""
    return round(from_celsius(to_celsius(value, src), dst), 4)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        prog="tempconv", description="Convert temperatures between C, F and K."
    )
    parser.add_argument("value", type=float)
    parser.add_argument("src", choices=["C", "F", "K"])
    parser.add_argument("dst", choices=["C", "F", "K"])
    args = parser.parse_args(argv)
    result = convert(args.value, args.src, args.dst)
    print("%g%s = %g%s" % (args.value, args.src.upper(), result, args.dst.upper()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# The fixed version differs only in the Kelvin offset (and a comment).
TEMPconv_V2 = TEMPconv_V1.replace(
    "KELVIN_OFFSET = 273  # BUG: should be 273.15",
    "KELVIN_OFFSET = 273.15  # absolute zero is -273.15 C",
)

TEST_FILE = '''# test_tempconv.py -- unit tests for tempconv (stdlib unittest)
import unittest

import tempconv


class TestCelsiusFahrenheit(unittest.TestCase):
    def test_celsius_to_fahrenheit(self):
        self.assertAlmostEqual(tempconv.convert(0, "C", "F"), 32.0, places=4)
        self.assertAlmostEqual(tempconv.convert(100, "C", "F"), 212.0, places=4)

    def test_fahrenheit_to_celsius(self):
        self.assertAlmostEqual(tempconv.convert(32, "F", "C"), 0.0, places=4)
        self.assertAlmostEqual(tempconv.convert(212, "F", "C"), 100.0, places=4)

    def test_round_trip_celsius_fahrenheit(self):
        for value in (-40.0, 0.0, 21.5, 37.0, 100.0):
            f = tempconv.convert(value, "C", "F")
            self.assertAlmostEqual(tempconv.convert(f, "F", "C"), value, places=3)


class TestKelvin(unittest.TestCase):
    def test_celsius_to_kelvin(self):
        self.assertAlmostEqual(tempconv.convert(0, "C", "K"), 273.15, places=4)
        self.assertAlmostEqual(tempconv.convert(-273.15, "C", "K"), 0.0, places=4)

    def test_kelvin_to_celsius(self):
        self.assertAlmostEqual(tempconv.convert(273.15, "K", "C"), 0.0, places=4)
        self.assertAlmostEqual(tempconv.convert(0, "K", "C"), -273.15, places=4)


class TestValidation(unittest.TestCase):
    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            tempconv.to_celsius(1, "X")

    def test_cli_output(self):
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tempconv.main(["100", "C", "F"])
        self.assertEqual(buf.getvalue().strip(), "100C = 212F")


if __name__ == "__main__":
    unittest.main()
'''

README_MD = """# tempconv

A tiny, dependency-free temperature conversion CLI built by the Forge agent.

## Usage

```bash
python tempconv.py 100 C F     # 100C = 212F
python tempconv.py 32 F C      # 32F = 0C
python tempconv.py 0 C K       # 0C = 273.15K
```

## API

```python
import tempconv
tempconv.convert(0, "C", "K")   # 273.15
```

## Tests

```bash
python -m unittest discover -s . -p 'test_*.py' -v
```
"""
