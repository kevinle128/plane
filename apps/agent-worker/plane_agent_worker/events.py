# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Claude stream-JSON messages as durable Run events.

Each event has a ``source_key`` that is the same when the Worker sends it again,
so Plane stores it once. Keys start with the turn index. Assistant blocks become
``message``, ``thought`` and ``tool_call`` events; a tool result becomes
``tool_result`` parts of at most ``MAX_PART_CHARS`` characters that the panel joins
by call ID and part index. Partial-message events, replays of the prompt and the
final ``result`` are not mapped: the prompt is the Run's first event in Plane, and
the result becomes the conclusion.
"""

import json

MAX_PART_CHARS = 16_384
MAX_TEXT_CHARS = 60_000


def status_event(turn_index, code, text):
    return {"source_key": f"t{turn_index}:status:{code}", "kind": "status", "payload": {"code": code, "text": text}}


def _blocks(message):
    content = (message.get("message") or {}).get("content")
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block.get("text", "") for block in content if isinstance(block, dict) and block.get("text"))
    return ""


def _cut(text):
    payload = {"text": text[:MAX_TEXT_CHARS]}
    if len(text) > MAX_TEXT_CHARS:
        payload["truncated"] = True
    return payload


class EventMapper:
    """Maps the messages of one turn."""

    def __init__(self, turn_index):
        self.turn_index = turn_index

    def _key(self, *parts):
        return ":".join([f"t{self.turn_index}", *(str(part) for part in parts)])

    def map(self, message):
        kind = message.get("type")
        if kind == "system" and message.get("subtype") == "init":
            model = message.get("model")
            text = f"Claude Code started ({model})" if isinstance(model, str) and model else "Claude Code started"
            return [
                {"source_key": self._key("init"), "kind": "status", "payload": {"code": "turn_started", "text": text}}
            ]
        if kind == "assistant":
            return self._assistant(message)
        if kind == "user" and not message.get("isReplay"):
            return self._tool_results(message)
        return []

    def _assistant(self, message):
        source = message.get("uuid") or (message.get("message") or {}).get("id") or "message"
        events = []
        for index, block in enumerate(_blocks(message)):
            key = self._key(source, index)
            block_type = block.get("type")
            if block_type == "text" and isinstance(block.get("text"), str) and block["text"]:
                events.append(
                    {"source_key": key, "kind": "message", "payload": {"role": "assistant", **_cut(block["text"])}}
                )
            elif block_type == "thinking" and isinstance(block.get("thinking"), str) and block["thinking"]:
                events.append({"source_key": key, "kind": "thought", "payload": _cut(block["thinking"])})
            elif block_type == "tool_use" and isinstance(block.get("id"), str):
                tool_input = block.get("input")
                encoded = json.dumps(tool_input, ensure_ascii=False)
                if len(encoded) > MAX_PART_CHARS:
                    tool_input = {"truncated": True, "text": encoded[:MAX_PART_CHARS]}
                payload = {"call_id": block["id"], "name": str(block.get("name") or ""), "input": tool_input}
                events.append({"source_key": key, "kind": "tool_call", "payload": payload})
        return events

    def _tool_results(self, message):
        events = []
        for block in _blocks(message):
            call_id = block.get("tool_use_id")
            if block.get("type") != "tool_result" or not isinstance(call_id, str):
                continue
            text = _text_of(block.get("content"))
            parts = [text[start : start + MAX_PART_CHARS] for start in range(0, len(text), MAX_PART_CHARS)] or [""]
            for index, part in enumerate(parts):
                payload = {
                    "call_id": call_id,
                    "part": index,
                    "parts": len(parts),
                    "text": part,
                    "is_error": block.get("is_error") is True,
                }
                events.append(
                    {"source_key": self._key(call_id, "result", index), "kind": "tool_result", "payload": payload}
                )
        return events
