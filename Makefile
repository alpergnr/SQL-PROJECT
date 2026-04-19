PYTHON ?= python3

.PHONY: lint test ci benchmark

lint:
	$(PYTHON) -m py_compile app.py tests/test_app.py

test:
	$(PYTHON) -m unittest discover -s tests -v

ci: lint test

benchmark:
	$(PYTHON) app.py benchmark --limit 20 --output table
