<template>
  <router-view />
</template>

<script setup>
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #f7f7f7; color: #222222; font-family: 'Circular', -apple-system, system-ui, Roboto, 'Helvetica Neue', sans-serif; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #dddddd; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #c1c1c1; }

/* === Global interactive surface normalization === */
:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover) {
  outline: none;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where(
  [class*="hover:"],
  [class*="group-hover:"],
  [class*="transition"],
  [class*="card-hover"]
) {
  border: 0 !important;
  outline: none !important;
  background-color: #e9e9e9 !important;
  background-image: none !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="bg-primary"]) {
  background-color: #ff385c !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="bg-ink"]) {
  background-color: #222222 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="bg-error-text"]) {
  background-color: #c13515 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-red-"]) {
  background-color: #dc2626 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"]):where([class*="hover:bg"]):not(
  [class*="bg-"],
  [class*="bg["]
) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-transparent"]) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where(
  [class*="bg-white"],
  [class*="bg-canvas"],
  [class*="bg-surface-soft"],
  [class*="bg-[#fbfaf8]"],
  [class*="bg-[#f5f4f0]"]
) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-primary/"]) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="hover:bg-primary/"]):hover {
  background-color: #ffd1dc !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="hover:bg-primary-active"]):hover {
  background-color: #e00b41 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="hover:bg-body"]):hover {
  background-color: #3f3f3f !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="hover:bg-hairline"]):hover {
  background-color: #dddddd !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="hover:bg-surface-soft"]):hover {
  background-color: #f7f7f7 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class~="hover:bg-red-700"]):hover {
  background-color: #b91c1c !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-error-text/"]) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="hover:bg-error-text/"]):hover {
  background-color: #f2c5ba !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-muted/"]) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-ink/"]) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-white/"]) {
  background-color: #e9e9e9 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="bg-black/"]) {
  background-color: #222222 !important;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="hover:border-ink"]):hover {
  box-shadow: inset 0 0 0 1px #222222;
}

:where(button, a, label, [role="button"], [class*="cursor-pointer"], .card-hover):where([class*="hover:border-primary"]):hover {
  box-shadow: inset 0 0 0 1px #ff385c;
}

/* === Page transitions === */
.page-enter-active { animation: pageIn 0.35s cubic-bezier(0.22, 1, 0.36, 1); }
.page-leave-active { animation: pageOut 0.2s cubic-bezier(0.22, 1, 0.36, 1); }
@keyframes pageIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pageOut {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-4px); }
}

/* === Card animations === */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInScale {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-12px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(12px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
@keyframes countUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes ripple {
  0% { transform: scale(0); opacity: 0.6; }
  100% { transform: scale(4); opacity: 0; }
}

/* === Staggered entrance === */
.stagger-1 { animation-delay: 0.05s; }
.stagger-2 { animation-delay: 0.1s; }
.stagger-3 { animation-delay: 0.15s; }
.stagger-4 { animation-delay: 0.2s; }
.stagger-5 { animation-delay: 0.25s; }

/* === Card hover — lift + shadow === */
.card-hover {
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              border-color 0.25s ease;
}
.card-hover:hover {
  transform: translateY(-2px);
  box-shadow: rgba(0,0,0,0.02) 0 0 0 1px, rgba(0,0,0,0.04) 0 4px 12px, rgba(0,0,0,0.08) 0 8px 24px;
}

/* === Button press effect === */
.btn-press {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.btn-press:active {
  transform: scale(0.97);
}

/* === Ripple effect container === */
.ripple-container {
  position: relative;
  overflow: hidden;
}
.ripple-container::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, rgba(255,56,92,0.15) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s;
}
.ripple-container:active::after {
  opacity: 1;
}

/* === Smooth focus === */
input:focus, select:focus {
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

/* === Tooltip === */
.tooltip-trigger { position: relative; }
.tooltip-trigger .tooltip-text {
  opacity: 0;
  transform: translateX(4px);
  transition: opacity 0.2s ease, transform 0.2s ease;
  pointer-events: none;
}
.tooltip-trigger:hover .tooltip-text {
  opacity: 1;
  transform: translateX(0);
}

/* === Number counter animation === */
.animate-count {
  animation: countUp 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
}

/* === Floating animation === */
.animate-float {
  animation: float 3s ease-in-out infinite;
}

/* === Markdown rendered content === */
.markdown-body h1 { font-size: 1.5em; font-weight: 700; margin: 1em 0 0.5em; color: #222; }
.markdown-body h2 { font-size: 1.25em; font-weight: 700; margin: 0.8em 0 0.4em; color: #222; }
.markdown-body h3 { font-size: 1.1em; font-weight: 600; margin: 0.6em 0 0.3em; color: #333; }
.markdown-body p { margin: 0.4em 0; }
.markdown-body strong { font-weight: 700; color: #111; }
.markdown-body ul, .markdown-body ol { padding-left: 1.5em; margin: 0.4em 0; }
.markdown-body li { margin: 0.2em 0; }
.markdown-body table { border-collapse: collapse; width: 100%; margin: 0.6em 0; }
.markdown-body th { background: #f5f4f0; font-weight: 700; text-align: left; padding: 6px 10px; border: 1px solid #ddd; font-size: 0.9em; }
.markdown-body td { padding: 5px 10px; border: 1px solid #eee; font-size: 0.9em; }
.markdown-body code { background: #f0ede8; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
.markdown-body pre { background: #f5f4f0; padding: 12px 16px; border-radius: 8px; overflow-x: auto; margin: 0.5em 0; }
.markdown-body pre code { background: none; padding: 0; }
.markdown-body blockquote { border-left: 3px solid #ff385c; padding-left: 12px; margin: 0.5em 0; color: #666; }
.markdown-body hr { border: none; border-top: 1px solid #eee; margin: 1em 0; }
.markdown-body a { color: #ff385c; text-decoration: underline; }
.markdown-body em { font-style: italic; }
</style>
