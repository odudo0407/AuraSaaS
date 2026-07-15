import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

test('package exposes quality scripts', () => {
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
  assert.equal(pkg.scripts.lint, 'node scripts/lint.mjs')
  assert.equal(pkg.scripts['format:check'], 'node scripts/format-check.mjs')
  assert.equal(pkg.scripts['test:run'], 'node --test')
})

test('request utility exports the public request helper', () => {
  const source = readFileSync(new URL('../src/utils/request.js', import.meta.url), 'utf8')
  assert.match(source, /export async function request/)
  assert.match(source, /aurasaas:auth-expired/)
})

test('batch selection composable keeps the expected public API', () => {
  const source = readFileSync(new URL('../src/composables/useBatchSelection.js', import.meta.url), 'utf8')
  for (const name of ['enterBatchMode', 'exitBatchMode', 'toggleBatchMode', 'toggleItem', 'toggleAll']) {
    assert.match(source, new RegExp(`\\b${name}\\b`))
  }
})
