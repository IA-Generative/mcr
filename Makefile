.PHONY: clean help install install-hooks type-check lint format pre-commit check-env start stop restart rebuild coverage eval-participants init-drive start-drive stop-drive


PACKAGES := mcr-gateway mcr-generation mcr-core mcr-capture-worker

help:
	clear
	@echo "================= Usage ================="
	@echo "install                   : Install dependencies of all python packages (uv sync), the frontend (pnpm install) and the git pre-commit hooks."
	@echo "install-hooks             : Install the git pre-commit hooks (uvx pre-commit install)."
	@echo "start                     : Start the app with docker compose"
	@echo "stop                      : Stop the app."
	@echo "restart                   : Restart the app or a single service using service=..."
	@echo "rebuild                   : Rebuild the app or a single service using service=..."
	@echo "type-check                : Run the type-check command in all python packages."
	@echo "lint                      : Run the lint command in all python packages."
	@echo "format                    : Run the format command in all python packages."
	@echo "pre-commit                : Run the all 3 previous command in all python packages."
	@echo "coverage                  : Run test coverage in all python packages."
	@echo "start-playwright-with-gui : Stop playwright docker service and run the bot locally with a browser gui."
	@echo "eval-participants         : Run the participants identification evaluation pipeline in the transcription_worker container."
	@echo "init-drive                : One-time Drive setup (build images, copy config)"
	@echo "start-drive               : Start MCR + Drive, configure Keycloak"
	@echo "stop-drive                : Stop both stacks"

define CALL_TARGET_CMD_ON_ALL_PKGS
	for pkg in $(PACKAGES); do \
		make -C $$pkg $(1); \
	done
endef

install: install-hooks
	$(call CALL_TARGET_CMD_ON_ALL_PKGS, install)
	cd mcr-frontend && pnpm install

install-hooks:
	uvx pre-commit install

# docker compose resolves ${VAR} with "shell > --env-file" precedence: a variable
# exported by the terminal silently overrides .env edits. Warn before every `up`.
check-env:
	@./scripts/check_env.py

# example: make start service=mcr-frontend
start: check-env
	touch .env
	docker compose --env-file .env.local.docker --env-file .env up $(service) --watch

stop:
	docker compose down $(service)

restart: check-env
	docker compose down $(service)
	docker compose --env-file .env.local.docker --env-file .env up --watch $(service)

rebuild: check-env
	docker compose down $(service)
	docker compose build $(service)
	docker compose --env-file .env.local.docker --env-file .env up --watch $(service)

type-check:
	$(call CALL_TARGET_CMD_ON_ALL_PKGS, type-check)

lint:
	$(call CALL_TARGET_CMD_ON_ALL_PKGS, lint)

format:
	$(call CALL_TARGET_CMD_ON_ALL_PKGS, format)

pre-commit:
	$(call CALL_TARGET_CMD_ON_ALL_PKGS, pre-commit)

start-playwright-with-gui:
	@docker compose down capture_worker
	cd mcr-capture-worker && \
	uv run playwright install && \
	uv run -m mcr_capture_worker.worker

eval-participants:
	docker compose --env-file .env.local.docker --env-file .env exec transcription_worker python -m mcr_meeting.evaluation.participant_naming

init-drive:  ## One-time: copy config, build images
	./docker/drive/setup-drive.sh

start-drive: check-env  ## Start MCR + Drive
	@if [ ! -f ../drive/compose.override.yml ]; then \
		echo "Drive is not set up. Run 'make init-drive' first."; \
		exit 1; \
	fi
	docker network create shared-network 2>/dev/null || true
	docker compose --env-file .env.local.docker --env-file .env up -d --wait keycloak
	@echo "Keycloak ready — starting Drive..."
	cd ../drive && docker compose up -d
	cd ../drive && make migrate
	cd ../drive && make configure-wopi
	@echo "Drive ready at http://localhost:3000"

stop-drive:  ## Stop both stacks
	cd ../drive && docker compose down
	docker compose down

coverage:
	@sh -c '\
		( \
			$(call CALL_TARGET_CMD_ON_ALL_PKGS, test-coverage >> .coverage_tmp) \
		) & \
		pid=$$!; \
		spinstr="|/-\\"; \
		while kill -0 $$pid 2>/dev/null; do \
			for c in $${spinstr}; do \
				printf " Running coverage... %c\r"; \
				sleep 0.1; \
			done; \
		done; \
		wait $$pid; \
		printf "\r"; \
	'
	@echo "+-------------------------------+-------------------------+----------+"
	@echo "| Package                       | Test Type               | Coverage |"
	@echo "+-------------------------------+-------------------------+----------+"
	@cat .coverage_tmp | while read line; do \
		pkg_name=$$(echo $$line | awk '{print $$1}'); \
		test_type=$$(echo $$line | awk '{print $$2}'); \
		cov=$$(echo $$line | awk '{print $$NF}'); \
		printf "| %-29s | %-23s | %-8s |\n" "$$pkg_name" "$$test_type" "$$cov"; \
	done
	@echo "+-------------------------------+-------------------------+----------+"
	@rm -f .coverage_tmp
