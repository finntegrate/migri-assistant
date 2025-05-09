from collections.abc import Mapping
from typing import Any, Protocol, TextIO

class Post(Protocol):
    metadata: dict[str, Any]
    content: str

def load(file_or_path: str | TextIO) -> Post:
    """
    Load a file with frontmatter and content.

    Args:
        file_or_path: File path or file object

    Returns:
        A Post object with metadata and content
    """
    ...

def loads(text: str) -> Post:
    """
    Load a string with frontmatter and content.

    Args:
        text: String containing frontmatter and content

    Returns:
        A Post object with metadata and content
    """
    ...

def dump(post: Post | Mapping[str, Any], filename: str) -> None:
    """
    Write a post dict to the specified filename.

    Args:
        post: A Post object or dictionary with metadata and content
        filename: The destination filename
    """
    ...

def dumps(post: Post | Mapping[str, Any]) -> str:
    """
    Return a string representation of a post.

    Args:
        post: A Post object or dictionary with metadata and content

    Returns:
        String representation with frontmatter and content
    """
    ...
