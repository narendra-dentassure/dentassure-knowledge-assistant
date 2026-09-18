"""Conversation memory for follow-up questions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    """Keep a short rolling history so follow-up questions stay grounded."""

    max_turns: int = 6
    turns: list[dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        """Append one turn and drop the oldest turns beyond max_turns."""
        self.turns.append({"role": role, "content": content})
        overflow = max(0, len(self.turns) - self.max_turns * 2)
        if overflow:
            self.turns = self.turns[overflow:]

    def as_prompt_block(self) -> str:
        """Format history for the generation prompt."""
        if not self.turns:
            return "No previous conversation."
        lines = []
        for turn in self.turns:
            label = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{label}: {turn['content']}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset history (Clear conversation in the UI)."""
        self.turns.clear()
