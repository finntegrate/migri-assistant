# Copilot Instructions

## Packages

Please use the `uv` package manager.

```
uv add <package-name>
```

Do not use `pip`, `uv pip install`, or `uv pip install -e .` to install packages or this project.

## Ruff

We use Ruff for linting and formatting. Please ensure your code passes all checks before submitting a pull request.
You can run the linter with the following command:

```
uv run ruff .
```

You can also run the linter with the `--fix` option to automatically fix some issues:

```
uv run ruff . --fix
```

You can also run the linter with the `--check` option to check for issues without fixing them:

```
uv run ruff . --check
```

## Testing

When adding features, always include appropriate tests. Run the entire test suite with:

```
uv run pytest
```

## Code Coverage

We aim for >= 80% test coverage before merging any pull requests.

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

## Ollama

We use Ollama for local LLM inference.

The following Ollama models are used in the project:

- `llama3.2`: The base model for text generation.

To query the Ollama models that are installed, use the command:

```
ollama list
```

To list all Ollama commands, use the command:

```
ollama help
```

To get help for a specific command, use the command:

```
ollama <command> --help
```

## Code Style

### Type Hints

- Use type hints for all function parameters and return types.
- Use `Optional` for optional parameters and return types.
- Use `list`, `dict`, `set`, and `tuple` for built-in types.

### Mypy

We use Mypy for type checking. Please ensure your code passes all checks.
You can run Mypy with the following command:

```
uv run mypy .
```

You can also run Mypy with the `--strict` option to enable strict type checking:

```
uv run mypy . --strict
```
