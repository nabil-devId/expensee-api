.PHONY: setup dev clean db migrations migrate install venv

# Default Python interpreter
PYTHON := python3
VENV_NAME := venv
VENV_BIN := $(VENV_NAME)/bin
VENV_ACTIVATE := . $(VENV_BIN)/activate

# Check if we're in a virtual environment
ifeq ("$(VIRTUAL_ENV)","")
  INVENV = $(VENV_ACTIVATE) &&
else
  INVENV =
endif

venv: ## Create virtual environment if it doesn't exist
	test -d $(VENV_NAME) || $(PYTHON) -m venv $(VENV_NAME)
	$(VENV_ACTIVATE)
	@echo "Virtual environment is ready and activated"

setup: venv ## Create virtual environment and install dependencies
	$(INVENV) pip install -r requirements.txt

install: venv ## Install dependencies only
	$(INVENV) pip install -r requirements.txt

db: ## Start PostgreSQL database
	docker-compose up -d db

migrations: venv ## Generate new migration
	$(INVENV) PYTHONPATH=. alembic revision --autogenerate -m "$(message)"

migrate: venv ## Apply migrations
	$(INVENV) PYTHONPATH=. alembic upgrade head

dev: venv db migrate ## Start development server with hot reload
	$(INVENV) uvicorn app.main:app --reload --host 0.0.0.0 --port 5001

clean: ## Remove virtual environment and cached files
	rm -rf $(VENV_NAME)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  %-20s %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help 