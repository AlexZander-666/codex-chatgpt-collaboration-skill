#!/usr/bin/env python3
"""Canonicalize task text and supported ProseMirror editor HTML snapshots."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser


SUPPORTED_TOP_LEVEL_BLOCKS = {"p", "div", "pre"}
BLOCK_ELEMENTS = SUPPORTED_TOP_LEVEL_BLOCKS | {
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ol",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
INLINE_ELEMENTS = {"a", "b", "code", "em", "i", "mark", "s", "span", "strong", "sub", "sup", "u"}
VOID_ELEMENTS = {"br", "hr", "img", "input", "meta", "link"}


class ComposerTopologyError(ValueError):
    """Raised when editor HTML cannot be converted without guessing."""


def canonicalize_transport(text: str) -> str:
    """Normalize transport line endings without changing other code points."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def utf8_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_task_marker(user_request: str, envelope: str, length: int = 16) -> str:
    """Hash a stable marker basis with any existing marker line omitted."""

    if not 8 <= length <= 64:
        raise ValueError("marker length must be between 8 and 64 hex characters")
    request = canonicalize_transport(user_request)
    normalized_envelope = canonicalize_transport(envelope)
    lines = normalized_envelope.splitlines(keepends=True)
    marker_lines = [line for line in lines if line.startswith("CODEX_TASK_ID:")]
    if len(marker_lines) > 1:
        raise ValueError("task envelope contains more than one marker line")
    envelope_without_marker = "".join(
        line for line in lines if not line.startswith("CODEX_TASK_ID:")
    )
    basis = request + "\n\0CODEX_TASK_ENVELOPE\0\n" + envelope_without_marker
    return utf8_sha256(basis)[:length]


class _ComposerParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.mode: str | None = None
        self.current: list[str] = []
        self.blocks: list[str] = []
        self.inline: list[str] = []
        self.top_tag: str | None = None

    @staticmethod
    def _is_trailing_break(attrs: list[tuple[str, str | None]]) -> bool:
        classes = next((value or "" for name, value in attrs if name == "class"), "")
        return "ProseMirror-trailingBreak" in classes.split()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.depth == 0 and tag in SUPPORTED_TOP_LEVEL_BLOCKS:
            if self.mode == "inline":
                raise ComposerTopologyError("mixed top-level inline and block content")
            self.mode = "blocks"
            self.current = []
            self.top_tag = tag
        elif self.depth == 0 and (tag in INLINE_ELEMENTS or tag == "br"):
            if self.mode == "blocks":
                raise ComposerTopologyError(f"unsupported top-level element after blocks: {tag}")
            self.mode = "inline"
        elif self.depth == 0:
            raise ComposerTopologyError(f"unsupported top-level element: {tag}")
        elif tag in BLOCK_ELEMENTS:
            raise ComposerTopologyError(f"unsupported nested block element: {tag}")
        elif tag not in INLINE_ELEMENTS and tag != "br":
            raise ComposerTopologyError(f"unsupported nested element: {tag}")

        target = self.current if self.mode == "blocks" else self.inline
        if tag == "br" and not self._is_trailing_break(attrs):
            target.append("\n")
        elif tag in {"script", "style", "textarea"}:
            raise ComposerTopologyError(f"unsupported editable element: {tag}")

        if tag not in VOID_ELEMENTS:
            self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_ELEMENTS:
            return
        if self.depth < 1:
            raise ComposerTopologyError(f"unbalanced closing element: {tag}")
        self.depth -= 1
        if self.depth == 0 and self.mode == "blocks":
            if tag != self.top_tag:
                raise ComposerTopologyError(f"mismatched top-level element: {tag}")
            self.blocks.append("".join(self.current))
            self.current = []
            self.top_tag = None

    def handle_data(self, data: str) -> None:
        if self.depth == 0:
            if not data.strip():
                return
            if self.mode == "blocks":
                raise ComposerTopologyError("mixed top-level text and block content")
            self.mode = "inline"
            self.inline.append(data)
            return
        target = self.current if self.mode == "blocks" else self.inline
        target.append(data)

    def result(self) -> str:
        if self.depth != 0 or self.current:
            raise ComposerTopologyError("unclosed editor element")
        if self.mode == "blocks":
            return "\n".join(self.blocks)
        return "".join(self.inline)


def canonicalize_composer_html(inner_html: str) -> str:
    """Reconstruct plaintext from a supported editable-root innerHTML snapshot."""

    parser = _ComposerParser()
    parser.feed(inner_html)
    parser.close()
    return parser.result()
