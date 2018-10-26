.PHONY: clean-pyc clean-build clean

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint:
	flake8 ticktick  tests

test:
	py.test

test-all:
	tox

coverage:
	coverage run --source ticktick  setup.py test
	coverage report -m
	coverage html
	open htmlcov/index.html

release: clean
	python setup.py sdist bdist_wheel
	twine upload dist/*

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist
