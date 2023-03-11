prepare:
	pipenv install --dev
	pipenv run pre-commit install

shell:
	pipenv shell

lint:
	pipenv run pre-commit run --all-files

test:
	pipenv run mypy

serve-docs:
	@cd docs;\
	make html;\
	cd _build/html;\
	python -m http.server;\
