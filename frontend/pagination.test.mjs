import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const [app, consumer] = await Promise.all([
  readFile(new URL('./src/App.vue', import.meta.url), 'utf8'),
  readFile(new URL('../backend/comments/consumers.py', import.meta.url), 'utf8')
])

assert.equal(/pageLimit:\s*5\b/.test(app), false, 'the frontend must not hard-code a page size')
assert.equal(/this\.pageLimit\s*=\s*limit/.test(app), true, 'the frontend must use the server-provided page size')
const fetchPage = app.match(/fetchPage\(offset\)\s*\{([\s\S]*?)\n    \},\n    loadNextPage/)
assert.ok(fetchPage, 'the frontend must define its WebSocket pagination request')
assert.equal(/limit\s*:/.test(fetchPage[1]), false, 'WebSocket pagination must not override the server default')
assert.equal(/api_settings\.PAGE_SIZE/.test(consumer), true, 'the WebSocket page size must come from DRF settings')
assert.equal(/"limit":\s*limit/.test(consumer), true, 'the WebSocket response must expose its effective page size')
