.PHONY: help validate test lint verify-discovery install-hooks

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

validate: ## Validate every skills/<name>/SKILL.md frontmatter contract
	uv run pytest -q

test: validate ## Alias for `validate`

lint: ## Run all pre-commit hooks across the repo
	uv run pre-commit run --all-files

verify-discovery: ## List skills via the skills CLI from this local path
	npx -y skills add ./. --list

install-hooks: ## Install pre-commit git hooks
	uv run pre-commit install
