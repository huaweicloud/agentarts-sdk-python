"""Structured input and output models for AgentArts Memory MCP tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects fields outside the public MCP contract."""

    model_config = ConfigDict(extra="forbid")


class SearchMatch(StrictModel):
    """One normalized result in the portable ``ltm_search`` contract."""

    content: str
    score: float | None = None
    strategy_type: str | None = None


class SearchResponse(StrictModel):
    """Structured response returned by ``ltm_search``."""

    query: str
    results: list[SearchMatch]


class LegacySearchMatch(StrictModel):
    """One result in the existing ``search_memories`` response shape."""

    content: str
    score: float | None = None
    type: str = ""


class LegacySearchResponse(StrictModel):
    """Structured response returned by ``search_memories``."""

    query: str
    results: list[LegacySearchMatch]
    total: int


class MessageInput(StrictModel):
    """One conversation message accepted by ``add_messages``."""

    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)


class AddMessagesResponse(StrictModel):
    """Structured response returned after recording messages."""

    session_id: str
    count: int


class MemoryListItem(StrictModel):
    """One normalized item returned by ``list_memories``."""

    id: str
    content: str
    type: str = ""
    created_at: str = ""


class MemoryListResponse(StrictModel):
    """Structured paginated memory-list response."""

    results: list[MemoryListItem]
    total: int


class SummaryMatch(StrictModel):
    """Normalized search or list item returned by ``search_summary``."""

    id: str | None = None
    content: str
    score: float | None = None
    type: str = ""
    created_at: str | None = None


class SummaryResponse(StrictModel):
    """Structured response returned by ``search_summary``."""

    query: str
    results: list[SummaryMatch]
    total: int
