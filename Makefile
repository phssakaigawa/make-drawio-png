.PHONY: test install-dev build clean

install-dev:
	pip install -e ".[dev]"

test:
	pytest

build:
	pip install hatchling
	python -m hatchling build

clean:
	Remove-Item -Recurse -Force dist, build, src\make_drawio_png.egg-info -ErrorAction SilentlyContinue
