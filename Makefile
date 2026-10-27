# Forge - agentic engineering copilot (Nebius Token Factory + NVIDIA Nemotron)
# Everything here runs with the Python 3.9+ standard library. No pip install.

PY ?= python3
OUT ?= build
GOAL ?= Build a CLI that converts temperatures between Celsius, Fahrenheit and Kelvin, with unit tests.

.PHONY: help smoke test demo real models clean distclean

help:
	@echo "make smoke    # full offline end-to-end check, no API key needed"
	@echo "make test     # unit tests only"
	@echo "make demo     # run the agent in mock mode, writing to ./$(OUT)"
	@echo "make real     # run the agent against Nebius Token Factory (needs NEBIUS_API_KEY)"
	@echo "make models   # list Nemotron models available to your key"
	@echo "make clean    # remove generated build output and caches"

smoke:
	$(PY) smoke.py

test:
	$(PY) -m unittest discover -s tests -p 'test_*.py'

demo:
	NO_COLOR=1 $(PY) -m forge --demo --mock --out $(OUT)

real:
	$(PY) -m forge "$(GOAL)" --real --out $(OUT)-real

models:
	$(PY) -m forge --models $(if $(NEBIUS_API_KEY),--real,--mock)

clean:
	rm -rf $(OUT) $(OUT)-real .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

distclean: clean
	rm -rf build-real
