.PHONY: all sdist wheel docs install upload upload_docs clean

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
    
clean:
	@echo "Removing tox dirs, logfiles, Pyro URI dumps, .pyo/.pyc files..."
	rm -rf .tox
	find . -name __pycache__  | xargs  rm -r
	find . -name \*_log  | xargs  rm 
	find . -name \*.log  | xargs  rm
	find . -name \*_URI  | xargs  rm
	find . -name \*.pyo  | xargs  rm
	find . -name \*.pyc  | xargs  rm
	find . -name \*.class  | xargs  rm
	find . -name \*.DS_Store  | xargs  rm
	rm -f MANIFEST 
	rm -rf build
	find . -name  '.#*'  | xargs  rm 
	find . -name  '#*#'  | xargs  rm 
	@echo "clean!"
