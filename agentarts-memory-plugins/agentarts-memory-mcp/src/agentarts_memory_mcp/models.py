"""Public structured output models for MCP tools."""

from pydantic import BaseModel, ConfigDict


class SearchMatch(BaseModel):
    """One normalized AgentArts Memory search match."""

    model_config = ConfigDict(extra="forbid")

    content: str
    score: float | None = None
    strategy_type: str | None = None


class SearchResponse(BaseModel):
    """Structured response returned by ltm_search."""

    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[SearchMatch]
