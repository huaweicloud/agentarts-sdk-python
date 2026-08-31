Search past session memories and summaries for relevant context.

## Usage

```
/recall [query]
```

## Instructions

1. The local AgentArts memory server exposes `/search_memory/` and `/search_summary/` REST endpoints.
2. Since OpenCode slash commands can't call HTTP directly, run:

   ```bash
   curl -s -X POST "$AGENTARTS_MEMORY_SERVER_URL/search_memory/" \
     -H "Content-Type: application/json" \
     -d "{\"query\": \"<query>\", \"num\": 5, \"threshold\": 0.3, \"user_id\": \"opencode-user\", \"scope_id\": \"<project>\"}"
   ```

   and similarly for `/search_summary/` with `num: 3`.
3. Combine and present results:
   - Group memories by type (semantic, episodic, user_preference)
   - Show history summaries separately
   - Highlight high-score memories (score >= 0.7)
4. If no results, suggest 2-3 alternative search terms.
5. **Never hallucinate results.** Only present what the server returns.
