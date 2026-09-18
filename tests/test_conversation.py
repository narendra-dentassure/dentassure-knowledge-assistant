"""Conversation memory tests."""

from src.conversation import ConversationMemory


def test_memory_keeps_latest_turns_only() -> None:
    memory = ConversationMemory(max_turns=2)
    memory.add("user", "q1")
    memory.add("assistant", "a1")
    memory.add("user", "q2")
    memory.add("assistant", "a2")
    memory.add("user", "q3")
    memory.add("assistant", "a3")
    assert len(memory.turns) == 4
    assert memory.turns[0]["content"] == "q2"


def test_prompt_block_and_clear() -> None:
    memory = ConversationMemory()
    assert "No previous" in memory.as_prompt_block()
    memory.add("user", "grace period?")
    memory.add("assistant", "15 days")
    block = memory.as_prompt_block()
    assert "User: grace period?" in block
    assert "Assistant: 15 days" in block
    memory.clear()
    assert memory.turns == []
