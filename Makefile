.PHONY: dev clean migrations migrate migrate-rollback install venv help

# --- Configuration ---
PYTHON := python3
VENV_DIR := .venv
REQUIREMENTS_FILE := requirements.txt

# --- Virtual Environment Tools ---
# These variables point to executables *inside* the virtual environment
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
VENV_ALEMBIC := $(VENV_DIR)/bin/alembic
VENV_UVICORN := $(VENV_DIR)/bin/uvicorn

# Marker file to indicate venv is set up
VENV_MARKER := $(VENV_DIR)/.venv_created


# Marker file to indicate dependencies are installed
INSTALL_MARKER := $(VENV_DIR)/.requirements_installed

# --- Targets ---

# Default target when `make` is run without arguments
.DEFAULT_GOAL := help

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

$(VENV_MARKER):
	@echo ">>> Creating virtual environment in $(VENV_DIR)..."
	test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)
	@echo ">>> Upgrading pip and installing wheel in virtual environment..."
	$(VENV_PIP) install --upgrade pip wheel
	@touch $@ # Create the marker file

venv: $(VENV_MARKER) ## Create/ensure virtual environment exists and core tools are up-to-date
	@echo ">>> Virtual environment is ready at $(VENV_DIR)"

$(INSTALL_MARKER): $(VENV_MARKER) $(REQUIREMENTS_FILE)
	@echo ">>> Installing dependencies from $(REQUIREMENTS_FILE)..."
	$(VENV_PIP) install -r $(REQUIREMENTS_FILE)
	@touch $@ # Create the marker file

install: $(INSTALL_MARKER) ## Install/update dependencies from requirements.txt
	@echo ">>> Dependencies are up to date."

migrations: install ## Generate new migration (usage: make migrations message="your message")
	@if [ -z "$(message)" ]; then \
		echo "ERROR: 'message' variable is not set. Usage: make migrations message=\"your descriptive message\""; \
		exit 1; \
	fi
	@echo ">>> Generating migration: $(message)"
	PYTHONPATH=. $(VENV_ALEMBIC) revision --autogenerate -m "$(message)"

migrate: install ## Apply migrations
	@echo ">>> Applying database migrations..."
	PYTHONPATH=. $(VENV_ALEMBIC) upgrade head

migrate-rollback: install ## Downgrade migrations by one step
	@echo ">>> Rolling back last database migration..."
	PYTHONPATH=. $(VENV_ALEMBIC) downgrade -1

dev: migrate ## Start development server with hot reload (depends on migrations being applied)
	@echo ">>> Starting development server on http://0.0.0.0:8000..."
	PYTHONPATH=. $(VENV_UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

clean: ## Remove virtual environment and cached files
	@echo ">>> Cleaning project..."
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo ">>> Clean complete."