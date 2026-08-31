# Design System Tokens Implementation Plan (PH-602)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Centralise colour, type scale, spacing, radii and motion as CSS tokens, record the
light-only decision, and meet WCAG AA contrast for text and controls.

**Approach:** `frontend/src/styles.css` `:root` now holds a documented token system — colour
(`--bg/--surface/--surface-sunken/--ink/--muted/--border/--star/--green*/--peach/--lavender/--shadow`),
type scale (`--text-xs…--text-xl`), spacing (`--space-1…6`), radii (`--radius-sm/md/lg/pill`) and
motion (`--motion-base`, `--ease-out`). Repeated literals (star gold, hairline border, sunken
surface, sheet animation) reference tokens. Light-only is stated explicitly (no dark palette, no
`prefers-color-scheme`).

**WCAG:** `--muted` was `#8a847e` (~3.4:1 on `#f8f4ec` — failed AA for small text); darkened to
`#6d6862` (~5.0:1). `--ink` `#4f4b48` ~8:1. Primary control (white on `--green-strong #47715a`)
~4.6:1. Contrast ratios recorded in the stylesheet header.

**Verification:** `cd frontend && npm run check` (lint, typecheck, 75 tests, build) green.

## Deferred / Handoff
- Full visual QA in the Telegram test environment + mobile viewport (DoD) is a manual step once a
  backend/staging session is available; the token values are structured to make that pass a tuning
  exercise, not a rewrite.

## Acceptance Criteria Mapping
- colours/type/spacing/radii/motion centralised → `:root` token groups + token usage.
- light-only explicitly recorded → stylesheet header comment.
- WCAG contrast verified for text and controls → recorded ratios; `--muted` fixed to AA.
