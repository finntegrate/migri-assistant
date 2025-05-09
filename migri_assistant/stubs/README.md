# Type Stubs in Migri Assistant

This directory contains type stubs (`.pyi` files) for third-party libraries that don't provide their own type hints.

## Structure

The stubs should be organized to mirror the package structure they're typing:

```
migri_assistant/
└── stubs/
    ├── __init__.py
    ├── package_name.pyi            # For simple packages
    └── complex_package/            # For packages with submodules
        ├── __init__.pyi
        ├── module1.pyi
        └── module2.pyi
```

## Adding New Stubs

When adding new stubs:

1. Place them in the appropriate location within `migri_assistant/stubs/`
2. Ensure the stub files use the `.pyi` extension
3. Make sure all types are properly imported
4. Test with `mypy` to ensure your stubs are recognized

## Guidelines

- Keep stubs minimal - include only what's needed for type checking
- Include docstrings for important functions and classes
- For packages with minimal usage, a single `.pyi` file is often sufficient
- For complex packages with many modules, mirror the package's directory structure

## Example Stub

A simple stub file might look like this:

```python
# package_name.pyi
from typing import Any, Dict, List, Optional

def some_function(arg1: str, arg2: Optional[int] = None) -> Dict[str, Any]: ...

class SomeClass:
    attr1: str
    attr2: List[int]

    def __init__(self, param: str) -> None: ...
    def method1(self) -> None: ...
    def method2(self, value: Any) -> str: ...
```
