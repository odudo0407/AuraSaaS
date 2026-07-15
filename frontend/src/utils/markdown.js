/**
 * Markdown → HTML renderer using marked.
 */
import { marked } from 'marked'

// Configure marked for a chat-friendly experience
marked.setOptions({
  breaks: true,      // single newline → <br>
  gfm: true,         // GitHub Flavored Markdown: tables, strikethrough, task lists
})

/**
 * Render Markdown string to safe HTML.
 * marked escapes raw HTML tags by default, so XSS is already covered.
 */
export function renderMarkdown(text) {
  if (!text) return ''
  // Strip any HTML tags that might have slipped through
  const safe = String(text).replace(/<[^>]*>/g, '')
  return marked.parse(safe)
}
