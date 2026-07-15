import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const roots = ['src', 'scripts', 'test']
const extensions = new Set(['.js', '.mjs', '.vue', '.json', '.md'])
const failures = []

function walk(dir) {
  if (!existsSync(dir)) return
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry)
    const stat = statSync(path)
    if (stat.isDirectory()) {
      walk(path)
      continue
    }
    if (![...extensions].some((ext) => path.endsWith(ext))) continue
    checkFile(path)
  }
}

function checkFile(path) {
  const text = readFileSync(path, 'utf8')
  const rel = relative(process.cwd(), path)
  if (!text.endsWith('\n')) {
    failures.push(`${rel}: missing final newline`)
  }
  text.split(/\r?\n/).forEach((line, index) => {
    if (/[ \t]+$/.test(line)) {
      failures.push(`${rel}:${index + 1}: trailing whitespace`)
    }
  })
}

for (const root of roots) {
  walk(join(process.cwd(), root))
}

if (failures.length) {
  console.error(failures.join('\n'))
  process.exit(1)
}

console.log('Frontend format checks passed.')
