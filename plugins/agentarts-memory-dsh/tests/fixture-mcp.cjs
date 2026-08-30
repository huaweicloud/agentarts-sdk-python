// Minimal synchronous stdio MCP fixture. It intentionally avoids process.stdin
// so the smoke test also works under Node 24 runners whose singleton stdin can
// report EOF for nested child pipes.
const fs = require('node:fs')

function send(id, result) {
  fs.writeSync(1, `${JSON.stringify({ jsonrpc: '2.0', id, result })}\n`)
}

let pending = ''
const chunk = Buffer.alloc(16 * 1024)
while (true) {
  const bytes = fs.readSync(0, chunk, 0, chunk.length, null)
  if (bytes === 0) break
  pending += chunk.toString('utf8', 0, bytes)
  while (pending.includes('\n')) {
    const newline = pending.indexOf('\n')
    const line = pending.slice(0, newline).trim()
    pending = pending.slice(newline + 1)
    if (line === '') continue
    const message = JSON.parse(line)
    if (message.method === 'initialize') {
      send(message.id, {
        protocolVersion: message.params.protocolVersion,
        capabilities: { tools: {} },
        serverInfo: { name: 'agentarts-memory-fixture', version: '0.1.0' },
      })
    } else if (message.method === 'tools/list') {
      send(message.id, {
        tools: [{
          name: 'ltm_search',
          description: 'Search AgentArts long-term memory.',
          inputSchema: {
            type: 'object',
            properties: { query: { type: 'string' } },
            required: ['query'],
          },
          annotations: {
            readOnlyHint: true,
            destructiveHint: false,
            idempotentHint: true,
            openWorldHint: true,
          },
        }],
      })
    } else if (message.method === 'tools/call') {
      send(message.id, {
        content: [{ type: 'text', text: '{"query":"fixture","results":[]}' }],
      })
    }
  }
}
