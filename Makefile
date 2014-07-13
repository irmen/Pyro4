.PHONY: all sdist wheel docs install upload upload_docs clean test

all:
	@echo "targets include sdist, wheel, docs, upload, upload_docs, install, clean"

sdist: 
	python setup.py sdist
	@echo "Look in the dist/ directory"

wheel: 
	python setup.py bdist_wheel
	@echo "Look in the dist/ directory"

docs:
	python setup.py build_sphinx

upload: upload_docs
	python setup.py sdist upload
	python setup.py bdist_wheel upload
	
upload_docs:
	python setup.py build_sphinx upload_sphinx

install:
	python setup.py install

test:
	python tests/run_testsuite.py

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
