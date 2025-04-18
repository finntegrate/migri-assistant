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
