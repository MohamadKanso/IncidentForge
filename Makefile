.PHONY: install test lint demo clean

install:
	python3 -m pip install -e ".[dev]"

test:
	python3 -m pytest

lint:
	python3 -m ruff check incidentforge tests

demo:
	python3 -m incidentforge demo --out examples/demo

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info outputs tmp examples/demo

