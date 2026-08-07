#!/usr/bin/env python3
"""Canonicalize task text and supported ProseMirror editor HTML snapshots."""

from __future__ import annotations

import hashlib
import hmac
import re
from html.parser import HTMLParser


PLAIN_TOP_LEVEL_BLOCKS = {"p", "div", "pre"}
RICH_TOP_LEVEL_BLOCKS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ol",
    "ul",
}
SUPPORTED_TOP_LEVEL_BLOCKS = PLAIN_TOP_LEVEL_BLOCKS | RICH_TOP_LEVEL_BLOCKS
INLINE_ELEMENTS = {"a", "span"}
VOID_ELEMENTS = {"br", "hr", "img", "input", "meta", "link"}
CONNECTION_PAYLOAD = "This is a Codex-ChatGPT connection test. Reply exactly: CONNECTION_OK"
TASK_PREAMBLE = "You are an external research and design adviser. Do not perform local actions."
TASK_HEADINGS = (
    "## Objective",
    "## Verified context",
    "## Boundaries",
    "## Evidence already available",
    "## Questions",
    "## Deliverables",
    "## Acceptance criteria",
)
LEGACY_REQUIRED_HEADINGS = tuple(
    heading for heading in TASK_HEADINGS if heading != "## Evidence already available"
)
MARKER_PATTERN = re.compile(r"CODEX_TASK_ID:([0-9a-f]{16,64})")
FINGERPRINT_PATTERN = re.compile(r"CODEX_DRAFT_SHA256:([0-9a-f]{64})")


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
    fingerprint_lines = [line for line in lines if line.startswith("CODEX_DRAFT_SHA256:")]
    if len(marker_lines) > 1:
        raise ValueError("task envelope contains more than one marker line")
    if len(fingerprint_lines) > 1:
        raise ValueError("task envelope contains more than one fingerprint line")
    envelope_without_marker = "".join(
        line
        for line in lines
        if not line.startswith(("CODEX_TASK_ID:", "CODEX_DRAFT_SHA256:"))
    )
    basis = request + "\n\0CODEX_TASK_ENVELOPE\0\n" + envelope_without_marker
    return utf8_sha256(basis)[:length]


def compute_draft_fingerprint(envelope: str) -> str:
    """Hash the LF transport envelope with its fingerprint line omitted."""

    normalized = canonicalize_transport(envelope)
    lines = normalized.splitlines(keepends=True)
    fingerprint_lines = [line for line in lines if line.startswith("CODEX_DRAFT_SHA256:")]
    if len(fingerprint_lines) > 1:
        raise ValueError("task envelope contains more than one fingerprint line")
    basis = "".join(line for line in lines if not line.startswith("CODEX_DRAFT_SHA256:"))
    return utf8_sha256(basis)


def classify_stale_codex_draft(text: str) -> str | None:
    """Recognize exact Codex connection or structured task drafts for safe reset."""

    canonical = canonicalize_transport(text)
    if canonical == CONNECTION_PAYLOAD:
        return "connection"

    lines = canonical.splitlines()
    if not lines:
        return None

    marker_lines = [line for line in lines if line.startswith("CODEX_TASK_ID:")]
    if len(marker_lines) != 1 or MARKER_PATTERN.fullmatch(marker_lines[0]) is None:
        return None
    known_protocol_lines = tuple(marker_lines) + tuple(
        line for line in lines if line.startswith("CODEX_DRAFT_SHA256:")
    )
    if any(line.startswith("CODEX_") and line not in known_protocol_lines for line in lines):
        return None

    marker_position = lines.index(marker_lines[0])

    fingerprint_lines = [line for line in lines if line.startswith("CODEX_DRAFT_SHA256:")]
    if not fingerprint_lines:
        heading_positions: list[int] = []
        for heading in LEGACY_REQUIRED_HEADINGS:
            if lines.count(heading) != 1:
                return None
            heading_positions.append(lines.index(heading))
        if heading_positions != sorted(heading_positions) or marker_position >= heading_positions[0]:
            return None
        prefix_lines = [line for line in lines[: heading_positions[0]] if line]
        legacy_preambles = [
            line
            for line in prefix_lines
            if line.startswith("You are an external ") and "Do not perform local actions." in line
        ]
        if len(prefix_lines) != 2 or len(legacy_preambles) != 1 or marker_lines[0] not in prefix_lines:
            return None
        return "legacy-task"
    if len(fingerprint_lines) != 1:
        return None
    heading_positions = []
    for heading in TASK_HEADINGS:
        if lines.count(heading) != 1:
            return None
        heading_positions.append(lines.index(heading))
    if heading_positions != sorted(heading_positions) or marker_position >= heading_positions[0]:
        return None
    if not lines or lines[0] != TASK_PREAMBLE:
        return None
    if lines.index(fingerprint_lines[0]) != marker_position + 1:
        return None
    match = FINGERPRINT_PATTERN.fullmatch(fingerprint_lines[0])
    if match is None:
        return None
    expected = compute_draft_fingerprint(canonical)
    return "fingerprinted-task" if hmac.compare_digest(match.group(1), expected) else None


class _ComposerNode:
    def __init__(self, tag: str, attrs: dict[str, str | None]) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list[str | _ComposerNode] = []


class _ComposerParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.roots: list[str | _ComposerNode] = []
        self.stack: list[_ComposerNode] = []

    @staticmethod
    def _is_trailing_break(attrs: list[tuple[str, str | None]]) -> bool:
        classes = next((value or "" for name, value in attrs if name == "class"), "")
        return "ProseMirror-trailingBreak" in classes.split()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "textarea"}:
            raise ComposerTopologyError(f"unsupported editable element: {tag}")
        node = _ComposerNode(tag, dict(attrs))
        target = self.stack[-1].children if self.stack else self.roots
        target.append(node)
        if tag not in VOID_ELEMENTS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_ELEMENTS:
            return
        if not self.stack:
            raise ComposerTopologyError(f"unbalanced closing element: {tag}")
        node = self.stack.pop()
        if node.tag != tag:
            raise ComposerTopologyError(f"mismatched closing element: {tag}")

    def handle_data(self, data: str) -> None:
        target = self.stack[-1].children if self.stack else self.roots
        target.append(data)

    @classmethod
    def _inline_text(cls, children: list[str | _ComposerNode]) -> str:
        parts: list[str] = []
        for child in children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag == "br":
                classes = (child.attrs.get("class") or "").split()
                if "ProseMirror-trailingBreak" not in classes:
                    parts.append("\n")
            elif child.tag == "span":
                parts.append(cls._inline_text(child.children))
            elif child.tag == "a":
                link_text = cls._inline_text(child.children)
                if child.attrs.get("href") != link_text:
                    raise ComposerTopologyError(
                        "only a raw URL whose link text equals href is reversible"
                    )
                parts.append(link_text)
            else:
                raise ComposerTopologyError(f"unsupported nested element: {child.tag}")
        return "".join(parts)

    @classmethod
    def _list_item_text(cls, node: _ComposerNode) -> str:
        meaningful = [
            child
            for child in node.children
            if not (isinstance(child, str) and not child.strip())
        ]
        if len(meaningful) == 1 and isinstance(meaningful[0], _ComposerNode):
            paragraph = meaningful[0]
            if paragraph.tag != "p":
                raise ComposerTopologyError(
                    f"unsupported list-item child element: {paragraph.tag}"
                )
            return cls._inline_text(paragraph.children)
        return cls._inline_text(node.children)

    @classmethod
    def _serialize_rich_block(cls, node: _ComposerNode) -> str:
        if node.tag in PLAIN_TOP_LEVEL_BLOCKS:
            return cls._inline_text(node.children)
        if re.fullmatch(r"h[1-6]", node.tag):
            level = int(node.tag[1])
            return f"{'#' * level} {cls._inline_text(node.children)}"
        if node.tag in {"ul", "ol"}:
            meaningful = [
                child
                for child in node.children
                if not (isinstance(child, str) and not child.strip())
            ]
            if not meaningful or any(
                not isinstance(child, _ComposerNode) or child.tag != "li"
                for child in meaningful
            ):
                raise ComposerTopologyError("list must contain only list items")
            if node.tag == "ul":
                prefixes = ["- "] * len(meaningful)
            else:
                raw_start = node.attrs.get("start") or "1"
                if not raw_start.isdigit() or int(raw_start) < 1:
                    raise ComposerTopologyError("ordered-list start must be a positive integer")
                start = int(raw_start)
                prefixes = [f"{start + index}. " for index in range(len(meaningful))]
            return "\n".join(
                prefix + cls._list_item_text(child)
                for prefix, child in zip(prefixes, meaningful, strict=True)
            )
        raise ComposerTopologyError(f"unsupported top-level element: {node.tag}")

    def result(self) -> str:
        if self.stack:
            raise ComposerTopologyError("unclosed editor element")
        meaningful = [
            root
            for root in self.roots
            if not (isinstance(root, str) and not root.strip())
        ]
        if not meaningful:
            return ""
        has_blocks = any(isinstance(root, _ComposerNode) for root in meaningful)
        has_inline = any(isinstance(root, str) for root in meaningful)
        if has_blocks and has_inline:
            raise ComposerTopologyError("mixed top-level inline and block content")
        if has_inline:
            return "".join(root for root in meaningful if isinstance(root, str))

        blocks = [root for root in meaningful if isinstance(root, _ComposerNode)]
        if any(block.tag not in SUPPORTED_TOP_LEVEL_BLOCKS for block in blocks):
            unsupported = next(
                block.tag for block in blocks if block.tag not in SUPPORTED_TOP_LEVEL_BLOCKS
            )
            raise ComposerTopologyError(f"unsupported top-level element: {unsupported}")
        rich_markdown = any(block.tag in RICH_TOP_LEVEL_BLOCKS for block in blocks)
        if not rich_markdown:
            return "\n".join(self._inline_text(block.children) for block in blocks)

        rendered = [self._serialize_rich_block(block) for block in blocks]
        if any(not block.strip() for block in rendered):
            raise ComposerTopologyError("empty rich-text block is ambiguous")
        result = rendered[0]
        for previous, current in zip(blocks[:-1], rendered[1:], strict=True):
            separator = "\n" if re.fullmatch(r"h[1-6]", previous.tag) else "\n\n"
            result += separator + current
        return result


def canonicalize_composer_html(inner_html: str) -> str:
    """Reconstruct plaintext from a supported editable-root innerHTML snapshot."""

    parser = _ComposerParser()
    parser.feed(inner_html)
    parser.close()
    return parser.result()
