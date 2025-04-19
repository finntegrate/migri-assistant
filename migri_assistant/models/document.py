class Document:
    def __init__(self, url: str, content: str, metadata: dict):
        self.url = url
        self.content = content
        self.metadata = metadata

    def to_dict(self):
        return {
            "url": self.url,
            "content": self.content,
            "metadata": self.metadata,
        }
