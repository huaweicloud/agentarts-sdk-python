Explicitly save an insight, decision, or learning to AgentArts Memory for future sessions.

## Usage

```
/remember [what to remember]
```

## Instructions

1. Analyze what needs to be remembered — extract the core insight, decision, or fact.
2. Save it by calling the local memory server:

   ```bash
   curl -s -X POST "$AGENTARTS_MEMORY_SERVER_URL/add_messages/" \
     -H "Content-Type: application/json" \
     -d "{\"messages\": [{\"role\": \"user\", \"content\": \"<the full text to remember>\"}], \"user_id\": \"opencode-user\", \"scope_id\": \"<project>\"}"
   ```

3. Confirm the save and show a brief summary of what was stored.
4. Preserve the user's own phrasing — don't paraphrase.
