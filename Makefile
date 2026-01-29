.PHONY: clean help type-check lint format pre-commit start stop restart rebuild coverage

PACKAGES := mcr-gateway mcr-generation mcr-core mcr-capture-worker

help:
	clear
	@echo "================= Usage ================="
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

define CALL_TARGET_CMD_ON_ALL_PKGS
	for pkg in $(PACKAGES); do \
		make -C $$pkg $(1); \
	done
endef

# example: make start service=mcr-frontend
start:
	touch .env
	docker compose --env-file .env.local.docker --env-file .env up $(service) --watch

stop:
	docker compose down $(service)

restart:
	docker compose down $(service)
	docker compose --env-file .env.local.docker --env-file .env up --watch $(service)

rebuild:
	docker compose down $(service)
	@if [ "$(service)" = "frontend" ]; then \
		docker volume rm mcr_frontend_node_modules; \
	fi
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
	@set -a; \
	. ./.env.local.host; \
	set +a; \
	cd mcr-capture-worker && \
	uv run playwright install && \
	uv run -m mcr_capture_worker.worker

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
