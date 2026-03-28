from __future__ import annotations

from pathlib import Path


EXTENSION_MAP = {
    ".txt": "text",
    ".md": "report",
    ".pdf": "report",
    ".docx": "docx_report",
    ".py": "source_code",
    ".ipynb": "notebook",
    ".csv": "spreadsheet",
    ".tsv": "dataset",
    ".xlsx": "dataset",
    ".json": "dataset",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".svg": "design_diagram",
    ".pptx": "slide_deck",
    ".wav": "audio",
    ".mp3": "audio",
    ".mp4": "video",
    ".mov": "video",
}

MIME_BY_SUFFIX = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".py": "text/x-python",
    ".ipynb": "application/json",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}


def classify_artifact(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    artifact_type = EXTENSION_MAP.get(suffix, "unsupported")
    mime_type = MIME_BY_SUFFIX.get(suffix, "application/octet-stream")
    return artifact_type, mime_type
