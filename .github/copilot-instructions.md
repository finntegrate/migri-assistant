# Copilot Instructions

## Packages

Please use the `uv` package manager.

```
uv add <package-name>
```

Do not use `pip` or `uv pip install` to install packages.

## Ruff

We use Ruff for linting and formatting. Please ensure your code passes all checks before submitting a pull request.
You can run the linter with the following command:

```
uv ruff .
```

You can also run the linter with the `--fix` option to automatically fix some issues:

```
uv ruff . --fix
```

You can also run the linter with the `--check` option to check for issues without fixing them:

```
uv ruff . --check
```

## Testing

When adding features, always include appropriate tests. Run the entire test suite with:

```
uv run pytest
```

## Code Coverage

We aim for high test coverage. When submitting code:

1. Check your coverage with:

```
uv run pytest --cov=migri_assistant
```

2. Generate HTML coverage reports for visual inspection:

```
uv run pytest --cov=migri_assistant --cov-report=html
```

3. For specific module coverage:

```
uv run pytest --cov=migri_assistant.utils tests/utils/
```

Aim for at least 80% coverage for new code. The HTML coverage report can be found in the `htmlcov` directory.
