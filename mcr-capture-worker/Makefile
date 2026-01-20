SOURCE_DIR = ./mcr_capture_worker

.PHONY: clean help coverage

help:
	clear;
	@echo "================= Usage =================";
	@echo "reload                 : Regenerate the docker image and run the docker-compose in detached mode.";
	@echo "type-check             : Run mypy as a static type-checker.";
	@echo "lint                   : Run ruff as a static linter.";
	@echo "format                 : Run ruff to format the code.";
	@echo "pre-commit             : Run type-check, lint and format commands.";
	@echo "test-coverage          : Run pytest coverage commands";
	@echo "test-coverage-integration : Run pytest coverage for integration (API) tests only.";


# Clean the folder from build/test related folders
reload: 
	docker build -t mcr-capture_worker .
	docker-compose up -d

type-check:
	uv sync --group dev  --inexact
	uv run mypy -p mcr_capture_worker

lint: 
	uv sync --group dev --inexact
	uv run ruff check

format:
	uv sync --group dev --inexact
	uv run ruff format
	uv run ruff check --select I . --fix

pre-commit: type-check lint format

show-trace:
	uv run playwright show-trace $(trace)

test:
	uv sync --group test --inexact
	uv run pytest .

test-coverage:
	@make test-coverage-integration

SERVICE_NAME = mcr-capture-worker
TEST_TYPE = integration
COVERAGE_PATH_INTEGRATION = mcr_capture_worker/app/api

test-coverage-integration:
	@uv sync --group test --inexact --quiet
	@uv run pytest --cov=$(COVERAGE_PATH_INTEGRATION) --cov-report=term 2>&1 | \
		grep -v "CoverageWarning" | grep TOTAL | awk '{print "$(SERVICE_NAME) $(TEST_TYPE) " $$4}'