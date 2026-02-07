SOURCE_DIR = ./mcr_meeting
EVALUATION_DATA_DIR ?=$(SOURCE_DIR)/evaluation/data
EVALUATION_OUTPUT_DIR  ?= $(EVALUATION_DATA_DIR)/outputs
MODEL    ?= tiny

ENV_FILE := ../.env

ifneq ("$(wildcard $(ENV_FILE))","")
  include $(ENV_FILE)
  export
endif

.PHONY: clean help

help:
	clear;
	@echo "================= Usage =================";
	@echo "type-check             : Run mypy as a static type-checker.";
	@echo "lint                   : Run ruff as a static linter.";
	@echo "format                 : Run ruff to format the code.";
	@echo "test            		  : Run all the tests in the package.";
	@echo "pre-commit             : Run type-check, lint, format and test commands.";
	@echo "db                     : Utility command set to generate and apply migrations.";
	@echo "test-coverage          : Run pytest coverage commands";
	@echo "test-coverage-integration : Run pytest coverage for integration (API) tests only.";
	@echo "evaluation 					: Run evaluation on the ASR pipeline"

type-check:
	uv sync --group typing --inexact
	uv run mypy -p mcr_meeting

lint: 
	uv sync --group dev --inexact
	uv run ruff check

format:
	uv sync --group dev --inexact
	uv run ruff format
	uv run ruff check --select I . --fix

test:
	uv sync --group test --all-extras --inexact
	uv run pytest .

deps-check:
	uv sync --group tools --inexact
	uv run deptry -v .

pre-commit: format type-check lint test

# Main db command help
db:
	@echo "=============== DB - Usage ==============";
	@echo "  make db-migration m='message'   Create a new migration with a message"
	@echo "  make db-upgrade                  Apply latest migrations"
	@echo "  make db-downgrade                Revert the last migration"

# Create a migration with a message
db-migration:
ifndef m
	$(error Please provide a message using m='message')
endif
	uv sync --inexact
	uv run alembic revision --autogenerate -m "$(m)"

# Run migrations
db-upgrade:
	uv sync --inexact
	uv run alembic upgrade head

# Downgrade one revision
db-downgrade:
	uv sync --inexact
	uv run alembic downgrade -1

# Coverage configuration
COVERAGE_MODULE ?= mcr_meeting
COVERAGE_PATH_INTEGRATION ?= mcr_meeting/app/api
COVERAGE_XML ?= coverage.xml
COVERAGE_HTML_DIR ?= htmlcov

# All tests + coverage (local/dev friendly)
test-coverage:
	@uv sync --group test --all-extras --inexact
	@uv run pytest . \
		--cov=$(COVERAGE_MODULE) \
		--cov-report=term-missing \
		--cov-report=xml:$(COVERAGE_XML) \
		--cov-report=html:$(COVERAGE_HTML_DIR)

# Integration (API) tests only + coverage
test-coverage-integration:
	@uv sync --group test --all-extras --inexact
	@uv run pytest tests/api \
		--cov=$(COVERAGE_PATH_INTEGRATION) \
		--cov-report=term-missing \
		--cov-report=xml:$(COVERAGE_XML)

# CI-friendly: no html report, just term + xml artifact
test-coverage-ci:
	@uv sync --group test --all-extras --inexact
	@uv run pytest . \
		--cov=$(COVERAGE_MODULE) \
		--cov-report=term-missing \
		--cov-report=xml:$(COVERAGE_XML)

eval:
	DATA_DIR=$(EVALUATION_DATA_DIR) OUT_DIR=$(EVALUATION_OUTPUT_DIR) MODEL=$(MODEL)
	uv sync --all-extras && \
	uv run python -m mcr_meeting.evaluation.cli.cli

metrics:
	DATA_DIR=$(EVALUATION_DATA_DIR) OUT_DIR=$(EVALUATION_OUTPUT_DIR)
	uv sync --all-extras && \
	uv run python -m mcr_meeting.evaluation.cli.cli_generate_metrics

# Before running this, make sure you have graphviz installed in your system.
# On MacOS, you can install it using: brew install graphviz
generate-graphs:
	@echo "Generating state machine graphs..."
	@uv sync --inexact --group dev >/dev/null 2>&1 || true
	@uv run python scripts/generate_state_machine_graph.py
	@echo "Graphs generated successfully in mcr_meeting/app/state_machine/graph/"