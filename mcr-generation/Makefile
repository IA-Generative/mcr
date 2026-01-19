SOURCE_DIR = ./mcr_generation

.PHONY: clean help

help:
	clear;
	@echo "================= Usage =================";
	@echo "type-check             : Run mypy as a static type-checker.";
	@echo "lint                   : Run ruff as a static linter.";
	@echo "format                 : Run ruff to format the code.";
	@echo "pre-commit             : Run type-check, lint and format commands.";
	@echo "test-coverage          : Run pytest coverage commands";
	@echo "test-coverage-integration : Run pytest coverage for integration (API) tests only.";

type-check:
	uv sync --all-extras
	uv run mypy -p mcr_generation

lint: 
	uv sync --all-extras
	uv run ruff check

format:
	uv sync --all-extras
	uv run ruff format
	uv run ruff check --select I . --fix

pre-commit: type-check lint format

SERVICE_NAME = mcr-generation
TEST_TYPE = integration
COVERAGE_PATH_INTEGRATION = mcr_generation/app/api

test-coverage:
	@make test-coverage-integration

test-coverage-integration:
	@uv sync --all-extras --quiet
	@uv run pytest --cov=$(COVERAGE_PATH_INTEGRATION) --cov-report=term 2>&1 | \
		grep -v "CoverageWarning" | grep TOTAL | awk '{print "$(SERVICE_NAME) $(TEST_TYPE) " $$4}'