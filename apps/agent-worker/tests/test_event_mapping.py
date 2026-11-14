# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json

from plane_agent_worker.events import MAX_PART_CHARS, MAX_TEXT_CHARS, EventMapper, status_event


def assistant(uuid, block, message_id="msg_1"):
    return {"type": "assistant", "uuid": uuid, "message": {"id": message_id, "role": "assistant", "content": [block]}}


def tool_result(tool_id, content, is_error=False, uuid="u-result"):
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": content, "is_error": is_error}
    return {"type": "user", "uuid": uuid, "message": {"role": "user", "content": [block]}}


def test_text_thinking_and_tool_use_become_message_thought_and_tool_call():
    mapper = EventMapper(turn_index=0)

    events = (
        mapper.map(assistant("a1", {"type": "thinking", "thinking": "Look at the README."}))
        + mapper.map(
            assistant("a2", {"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {"path": "README.md"}})
        )
        + mapper.map(assistant("a3", {"type": "text", "text": "The README says hello."}))
    )

    assert events == [
        {"source_key": "t0:a1:0", "kind": "thought", "payload": {"text": "Look at the README."}},
        {
            "source_key": "t0:a2:0",
            "kind": "tool_call",
            "payload": {"call_id": "toolu_1", "name": "Read", "input": {"path": "README.md"}},
        },
        {
            "source_key": "t0:a3:0",
            "kind": "message",
            "payload": {"role": "assistant", "text": "The README says hello."},
        },
    ]


def test_tool_result_is_split_into_parts_with_the_call_id():
    mapper = EventMapper(turn_index=2)
    text = "x" * (MAX_PART_CHARS * 2 + 5)

    events = mapper.map(tool_result("toolu_9", [{"type": "text", "text": text}], is_error=True))

    assert [event["source_key"] for event in events] == [
        "t2:toolu_9:result:0",
        "t2:toolu_9:result:1",
        "t2:toolu_9:result:2",
    ]
    assert all(event["kind"] == "tool_result" for event in events)
    assert [event["payload"]["part"] for event in events] == [0, 1, 2]
    assert {event["payload"]["parts"] for event in events} == {3}
    assert {event["payload"]["is_error"] for event in events} == {True}
    assert "".join(event["payload"]["text"] for event in events) == text


def test_empty_tool_result_is_one_empty_part():
    events = EventMapper(turn_index=0).map(tool_result("toolu_2", ""))

    assert events == [
        {
            "source_key": "t0:toolu_2:result:0",
            "kind": "tool_result",
            "payload": {"call_id": "toolu_2", "part": 0, "parts": 1, "text": "", "is_error": False},
        }
    ]


def test_large_tool_input_is_truncated_as_text():
    big = {"command": "y" * (MAX_PART_CHARS + 10)}

    [event] = EventMapper(turn_index=0).map(
        assistant("a1", {"type": "tool_use", "id": "toolu_3", "name": "Bash", "input": big})
    )

    assert event["payload"]["input"]["truncated"] is True
    assert len(event["payload"]["input"]["text"]) == MAX_PART_CHARS
    assert json.dumps(big).startswith(event["payload"]["input"]["text"])


def test_long_message_text_is_cut():
    [event] = EventMapper(turn_index=0).map(assistant("a1", {"type": "text", "text": "z" * (MAX_TEXT_CHARS + 1)}))

    assert len(event["payload"]["text"]) == MAX_TEXT_CHARS
    assert event["payload"]["truncated"] is True


def test_replays_partial_events_empty_thinking_and_results_are_not_mapped():
    mapper = EventMapper(turn_index=0)

    assert (
        mapper.map({"type": "user", "isReplay": True, "uuid": "r", "message": {"role": "user", "content": "hi"}}) == []
    )
    assert mapper.map({"type": "stream_event", "event": {"type": "content_block_delta"}}) == []
    assert mapper.map(assistant("a1", {"type": "thinking", "thinking": ""})) == []
    assert mapper.map({"type": "result", "subtype": "success", "result": "done"}) == []
    assert mapper.map({"type": "system", "subtype": "hook_started"}) == []


def test_init_gives_one_status_event_with_the_model():
    mapper = EventMapper(turn_index=1)

    events = mapper.map({"type": "system", "subtype": "init", "model": "claude-haiku-4-5", "session_id": "s"})

    assert events == [
        {
            "source_key": "t1:init",
            "kind": "status",
            "payload": {"code": "turn_started", "text": "Claude Code started (claude-haiku-4-5)"},
        }
    ]


def test_message_without_uuid_uses_the_message_id_and_block_index():
    message = {
        "type": "assistant",
        "message": {"id": "msg_7", "content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]},
    }

    events = EventMapper(turn_index=0).map(message)

    assert [event["source_key"] for event in events] == ["t0:msg_7:0", "t0:msg_7:1"]


def test_status_event_has_a_stable_source_key():
    assert status_event(0, "cloning", "Cloning the repository") == {
        "source_key": "t0:status:cloning",
        "kind": "status",
        "payload": {"code": "cloning", "text": "Cloning the repository"},
    }
