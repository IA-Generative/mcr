SOURCE_DIR = ./mcr_gateway

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
	uv sync --group typing --inexact
	uv run mypy -p mcr_gateway

lint: 
	uv sync --group dev --inexact
	uv run ruff check

format:
	uv sync --group dev --inexact
	uv run ruff format
	uv run ruff check --select I . --fix

deps-check:
	uv sync --group tools --inexact
	uv run deptry -v .

test:
	uv sync --group test --quiet --inexact
	uv run pytest .

pre-commit: type-check lint format

test-coverage:
	@make test-coverage-integration

SERVICE_NAME = mcr-gateway
TEST_TYPE = integration
COVERAGE_PATH_INTEGRATION = mcr_gateway/app/api

test-coverage-integration:
	@uv sync --group test --quiet --inexact
	@uv run pytest --cov=$(COVERAGE_PATH_INTEGRATION) --cov-report=term 2>&1 | \
		grep -v "CoverageWarning" | grep TOTAL | awk '{print "$(SERVICE_NAME) $(TEST_TYPE) " $$4}'