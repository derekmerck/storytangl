"""Terminal renderers for StoryTangl CLI output."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Mapping


JsonMapping = Mapping[str, Any]


def create_terminal_renderer(style: str) -> PlainTerminalRenderer:
    if style == "plain":
        return PlainTerminalRenderer()
    if style == "rich":
        return RichTerminalRenderer()
    raise ValueError(f"Unknown terminal renderer: {style}")


class PlainTerminalRenderer:
    """Line-oriented renderer used by the default cmd2 shell."""

    def emit(self, cmd: Any, renderables: list[Any]) -> None:
        for renderable in renderables:
            cmd.poutput(str(renderable))

    def story_update(
        self,
        *,
        fragments: list[Any],
        choices: list[Any],
        metadata: JsonMapping | None = None,
        title: str = "Story Update",
    ) -> list[Any]:
        if not fragments:
            return ["No journal entries available."]

        lines: list[Any] = [f"{title}:", "-------------------------"]
        for fragment in fragments:
            lines.extend(_plain_fragment_lines(fragment))

        lines.extend(self._choice_lines(choices))
        lines.extend(_plain_info_affordance_lines(metadata))
        return lines

    def story_created(
        self,
        *,
        title: str,
        ledger_id: Any,
        fragments: list[Any],
        choices: list[Any],
        metadata: JsonMapping | None = None,
    ) -> list[Any]:
        lines: list[Any] = [f"\nCreated story: {title}"]
        if ledger_id is not None:
            lines.append(f"Ledger ID: {ledger_id}\n")

        if fragments:
            lines.append("--- Story Begins ---")
            for fragment in fragments:
                lines.extend(_plain_fragment_lines(fragment))
            lines.append("")

        if choices:
            lines.extend(self._choice_lines(choices, no_choices_text="(No choices available)"))
        else:
            lines.append("(No choices available)")

        lines.extend(_plain_info_affordance_lines(metadata))
        lines.append("\nUse 'do <number>' to make a choice.")
        return lines

    def projected_state(self, payload: JsonMapping) -> list[Any]:
        sections = payload.get("sections")
        if not isinstance(sections, list):
            return [f"{key}: {value}" for key, value in payload.items()]
        if not sections:
            return ["No status data available."]

        lines: list[Any] = []
        for index, section in enumerate(sections):
            if not isinstance(section, Mapping):
                lines.append(str(section))
                continue

            title = section.get("title") or section.get("section_id") or "Section"
            lines.append(f"{title}:")
            section_lines = _projected_section_lines(section)
            if not section_lines:
                lines.append("  (No details)")
            else:
                lines.extend(f"  {line}" for line in section_lines)
            if index < len(sections) - 1:
                lines.append("")
        return lines

    def _choice_lines(
        self,
        choices: list[Any],
        *,
        no_choices_text: str = "No available choices.",
    ) -> list[Any]:
        if not choices:
            return [no_choices_text]

        lines: list[Any] = ["Choices:"]
        active_index = 1
        for choice in choices:
            label = _choice_label(choice)
            if _choice_active(choice):
                lines.append(f"{active_index}. {label}")
                active_index += 1
                continue

            reason = _read(choice, "unavailable_reason")
            reason_text = f" [locked: {reason}]" if reason else " [locked]"
            lines.append(f"x) {label}{reason_text}")
        return lines


class RichTerminalRenderer(PlainTerminalRenderer):
    """Rich renderer for the optional ``tangl-cli-rich`` entry point."""

    def __init__(self) -> None:
        try:
            __import__("rich")
        except ImportError as exc:
            raise RuntimeError(
                "Install StoryTangl with the cli-rich extra to use Rich output"
            ) from exc

    def emit(self, cmd: Any, renderables: list[Any]) -> None:
        from rich.console import Console

        console = Console(
            file=cmd.stdout,
            width=min(_terminal_width(), 100),
            no_color=("NO_COLOR" in os.environ) or not _isatty(cmd.stdout),
        )
        for renderable in renderables:
            console.print(renderable)

    def story_update(
        self,
        *,
        fragments: list[Any],
        choices: list[Any],
        metadata: JsonMapping | None = None,
        title: str = "Story Update",
    ) -> list[Any]:
        if not fragments:
            return [_rich_text("No journal entries available.", style="dim")]

        renderables: list[Any] = [_rich_rule(title)]
        for fragment in fragments:
            renderables.extend(_rich_fragment_renderables(fragment))

        renderables.append(_rich_choices(choices))
        renderables.extend(_rich_info_affordances(metadata))
        return renderables

    def story_created(
        self,
        *,
        title: str,
        ledger_id: Any,
        fragments: list[Any],
        choices: list[Any],
        metadata: JsonMapping | None = None,
    ) -> list[Any]:
        renderables: list[Any] = [_rich_text(f"Created story: {title}", style="bold")]
        if ledger_id is not None:
            renderables.append(_rich_text(f"Ledger ID: {ledger_id}", style="dim"))
        if fragments:
            renderables.append(_rich_rule("Story Begins"))
            for fragment in fragments:
                renderables.extend(_rich_fragment_renderables(fragment))
        renderables.append(_rich_choices(choices, no_choices_text="(No choices available)"))
        renderables.extend(_rich_info_affordances(metadata))
        renderables.append(_rich_text("Use 'do <number>' to make a choice.", style="dim"))
        return renderables

    def projected_state(self, payload: JsonMapping) -> list[Any]:
        sections = payload.get("sections")
        if not isinstance(sections, list):
            return [self._fallback_table("Info", payload.items())]
        if not sections:
            return [_rich_text("No status data available.", style="dim")]

        renderables: list[Any] = []
        for section in sections:
            if not isinstance(section, Mapping):
                renderables.append(_rich_text(str(section)))
                continue
            title = str(section.get("title") or section.get("section_id") or "Section")
            lines = _projected_section_lines(section)
            if not lines:
                lines = ["(No details)"]
            renderables.append(self._fallback_table(title, _line_pairs(lines)))
        return renderables

    def _fallback_table(self, title: str, pairs: Any) -> Any:
        from rich.table import Table

        table = Table.grid(padding=(0, 2))
        table.title = title
        table.add_column(style="bold")
        table.add_column()
        for key, value in pairs:
            table.add_row(str(key), str(value))
        return table


def _plain_fragment_lines(fragment: Any) -> list[str]:
    ftype = _read(fragment, "fragment_type")
    if ftype == "choice" or ftype == "control":
        return []
    if ftype == "attributed":
        who = _read(fragment, "who") or _read(fragment, "speaker") or "Someone"
        how = _read(fragment, "how")
        content = _fragment_text(fragment)
        aside = f" ({how})" if how else ""
        return [f"{str(who).upper()}{aside}: {content}"]
    if ftype == "media":
        role = _read(fragment, "media_role") or _read(fragment, "role") or "media"
        content = _fragment_text(fragment)
        return [f"[{role}: {_basename(content)}]"]
    if ftype == "kv":
        content = _read(fragment, "content")
        if isinstance(content, list):
            return _kv_lines(content)
    if ftype == "user_event":
        event_type = _read(fragment, "event_type") or "event"
        return [f"* {event_type}: {_fragment_text(fragment)}"]

    text = _fragment_text(fragment)
    return [text] if text else []


def _rich_fragment_renderables(fragment: Any) -> list[Any]:
    ftype = _read(fragment, "fragment_type")
    if ftype == "choice" or ftype == "control":
        return []
    if ftype == "attributed":
        who = _read(fragment, "who") or _read(fragment, "speaker") or "Someone"
        how = _read(fragment, "how")
        text = _rich_text(str(who), style="bold")
        if how:
            text.append(f" ‹{how}›", style="italic dim")
        text.append(f"\n{_fragment_text(fragment)}")
        return [text]
    if ftype == "media":
        return [_rich_media_placeholder(fragment)]
    if ftype == "kv":
        content = _read(fragment, "content")
        if isinstance(content, list):
            return [_rich_kv_table(content)]
    if ftype == "user_event":
        event_type = _read(fragment, "event_type") or "event"
        return [_rich_text(f"‹ {event_type} › {_fragment_text(fragment)}", style="italic dim")]

    content_format = _read(fragment, "content_format")
    text = _fragment_text(fragment)
    if content_format == "md":
        try:
            from rich.markdown import Markdown

            return [Markdown(text)]
        except ImportError:
            return [_rich_text(text)]
    return [_rich_text(text)] if text else []


def _rich_choices(choices: list[Any], *, no_choices_text: str = "No available choices.") -> Any:
    if not choices:
        return _rich_text(no_choices_text, style="dim")

    from rich.table import Table
    from rich.text import Text

    table = Table.grid(padding=(0, 2))
    table.title = "Choices"
    table.add_column(justify="right", style="bold")
    table.add_column()
    table.add_column(style="dim")

    active_index = 1
    for choice in choices:
        label = _choice_label(choice)
        if _choice_active(choice):
            table.add_row(str(active_index), label, "")
            active_index += 1
            continue

        reason = _read(choice, "unavailable_reason")
        state = f"locked: {reason}" if reason else "locked"
        table.add_row("x", Text(label, style="dim"), Text(state, style="yellow"))
    return table


def _rich_kv_table(items: list[Any]) -> Any:
    from rich.table import Table

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    for item in items:
        if isinstance(item, Mapping):
            table.add_row(str(item.get("key", "")), str(item.get("value", "")))
    return table


def _rich_media_placeholder(fragment: Any) -> Any:
    from rich.panel import Panel

    role = _read(fragment, "media_role") or _read(fragment, "role") or "media"
    return Panel(_basename(_fragment_text(fragment)), title=str(role), expand=False)


def _rich_info_affordances(metadata: JsonMapping | None) -> list[Any]:
    lines = _plain_info_affordance_lines(metadata)
    if not lines:
        return []
    return [_rich_text(" · ".join(lines), style="dim")]


def _rich_text(text: str, *, style: str | None = None) -> Any:
    from rich.text import Text

    return Text(text, style=style)


def _rich_rule(title: str) -> Any:
    from rich.rule import Rule

    return Rule(title)


def _plain_info_affordance_lines(metadata: JsonMapping | None) -> list[str]:
    if not metadata:
        return []
    affordances = metadata.get("info_affordances")
    if not isinstance(affordances, list) or not affordances:
        return []

    info_state = metadata.get("info_state")
    available = None
    if isinstance(info_state, Mapping) and isinstance(info_state.get("available_kinds"), list):
        available = {str(kind) for kind in info_state["available_kinds"]}

    labels: list[str] = []
    for affordance in affordances:
        if not isinstance(affordance, Mapping):
            continue
        kind = str(affordance.get("kind") or "info")
        if available is not None and kind not in available:
            continue
        label = str(affordance.get("label") or kind)
        shortcuts = affordance.get("shortcuts")
        shortcut = ""
        if isinstance(shortcuts, list) and shortcuts:
            shortcut = f"/{shortcuts[0]} "
        labels.append(f"{shortcut}{label}")

    if not labels:
        return []
    return ["Info: " + " · ".join(labels)]


def _projected_section_lines(section: JsonMapping) -> list[str]:
    value = section.get("value")
    if not isinstance(value, Mapping):
        return [str(value)] if value is not None else []

    value_type = value.get("value_type")
    if value_type == "kv_list":
        items = value.get("items")
        if not isinstance(items, list):
            return []
        return [
            f"{item.get('key')}: {item.get('value')}"
            for item in items
            if isinstance(item, Mapping) and item.get("key") is not None
        ]
    if value_type == "item_list":
        return _item_list_lines(value.get("items"))
    if value_type == "table":
        return _table_lines(value)
    if value_type == "badges":
        badges = value.get("items")
        if isinstance(badges, list) and badges:
            return [", ".join(str(item) for item in badges)]
        return []
    if value_type == "scalar":
        scalar = value.get("value")
        return [str(scalar)] if scalar is not None else []
    return [str(value)]


def _item_list_lines(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        label = item.get("label")
        if label is None:
            continue
        line = str(label)
        detail = item.get("detail")
        tags = item.get("tags")
        extras: list[str] = []
        if detail:
            extras.append(str(detail))
        if isinstance(tags, list) and tags:
            extras.append(", ".join(str(tag) for tag in tags))
        if extras:
            line = f"{line}: {' | '.join(extras)}"
        lines.append(line)
    return lines


def _table_lines(value: JsonMapping) -> list[str]:
    columns = value.get("columns")
    rows = value.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []
    lines = [" | ".join(str(column) for column in columns)]
    for row in rows:
        if isinstance(row, list):
            lines.append(" | ".join(str(cell) for cell in row))
    return lines


def _kv_lines(items: list[Any]) -> list[str]:
    return [
        f"{item.get('key')}: {item.get('value')}"
        for item in items
        if isinstance(item, Mapping) and item.get("key") is not None
    ]


def _line_pairs(lines: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in lines:
        if ": " in line:
            key, value = line.split(": ", 1)
            pairs.append((key, value))
        else:
            pairs.append(("", line))
    return pairs


def _fragment_text(fragment: Any) -> str:
    for attr in ("content", "text", "label"):
        value = _read(fragment, attr)
        if isinstance(value, str) and value.strip():
            return value.strip().replace("_", " ")
    return str(fragment)


def _choice_label(choice: Any) -> str:
    label = _read(choice, "label") or _read(choice, "content") or _read(choice, "text")
    return str(label or _read(choice, "uid") or "choice").replace("_", " ")


def _choice_active(choice: Any) -> bool:
    active = _read(choice, "active", True)
    return bool(active)


def _read(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _basename(value: str) -> str:
    return Path(value).name or value


def _terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def _isatty(stream: Any) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())
