.PHONY: all sdist wheel docs install upload clean test lint
PYTHON=python3

all:
	@echo "targets include sdist, wheel, docs, upload, install, clean, lint"

lint:
	pycodestyle

sdist:
	$(PYTHON) setup.py sdist
	@echo "Look in the dist/ directory"

wheel:
	$(PYTHON) setup.py bdist_wheel
	@echo "Look in the dist/ directory"

docs:
	$(PYTHON) setup.py build_sphinx

upload:
	$(PYTHON) setup.py sdist bdist_wheel upload
	@echo "Don't forget to check the doc builds on RTD!"

install:
	$(PYTHON) setup.py install

test:
	PYTHONPATH=./src $(PYTHON) tests/run_testsuite.py

clean:
	@echo "Removing tox dirs, logfiles, Pyro URI dumps, .pyo/.pyc files..."
	rm -rf .tox
	find . -name __pycache__ -print0 | xargs -0 rm -rf
	find . -name \*_log -print0 | xargs -0  rm -f
	find . -name \*.log -print0 | xargs -0  rm -f
	find . -name \*_URI -print0 | xargs -0  rm -f
	find . -name \*.pyo -print0 | xargs -0  rm -f
	find . -name \*.pyc -print0 | xargs -0  rm -f
	find . -name \*.class -print0 | xargs -0  rm -f
	find . -name \*.DS_Store -print0 | xargs -0  rm -f
	find . -name \.coverage -print0 | xargs -0  rm -f
	find . -name \coverage.xml -print0 | xargs -0  rm -f
	rm -f MANIFEST
	rm -rf build
	rm -rf tests/test-reports
	find . -name  '.#*' -print0 | xargs -0  rm -f
	find . -name  '#*#' -print0 | xargs -0  rm -f
	@echo "clean!"
