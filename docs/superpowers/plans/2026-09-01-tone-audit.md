# Tone-of-Voice Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Guarantee no UI/push/error text carries streak, missed-day, pressure, ranking, personality-judgement, or psychologist-advice wording — and keep a regression guard.

**Architecture:** An automated frontend test (`tone-audit.test.ts`) scans all non-test `src` source (comments stripped) for a forbidden wordlist. The bot copy has its own guard (`FORBIDDEN_TONE_WORDS` + `test_start_greeting_keeps_a_calm_pressure_free_tone`). The semantic checks (no personality judgement, no psychologist-voice advice) are a manual review recorded here.

**Spec:** `docs/backlog.md` — `PH-604`; product-brief invariant 1; `AGENTS.md` guardrails.

---

### Task 1: Automated wordlist guard (DONE)
- `frontend/src/lib/tone-audit.test.ts` scans `src/**/*.{ts,tsx}` (excluding tests) for
  «серия/серию/серий/пропустил/пропущен/не потеряй/не теряй/подряд/streak/рейтинг».
- Backend bot copy guarded by the existing `FORBIDDEN_TONE_WORDS` test.

### Manual audit (recorded)
Reviewed every current user-facing string:
- **Home** — «Тихое место на сегодня», «Можно даже за мелочь», «За что ты хочешь похвалить себя
  сегодня?», privacy note. Calm, no pressure/judgement.
- **Composer** — «Похвала тоже считается», «Только ты сможешь это прочитать», «Сохранить похвалу»,
  success «Сохранили ⭐», error «Не удалось сохранить. Можно попробовать ещё раз.» No guilt/streak.
- **Bootstrap/recovery** — loading / session-error / storage-error copy: gentle, offers retry, no blame.
- **Calendar** — «⭐ N в месяце», day labels «N сентября, есть похвала». No streak wording.
- **Bot `/start`** — calm greeting «…заметить, за что можно похвалить себя… Без оценок и без спешки».
- No text gives advice in a psychologist's voice or judges the person.

### Verification (DONE)
- `cd frontend && npm run check` green (tone-audit test included).

---

## Acceptance Criteria Mapping
- no «серия»/«пропустил»/«не потеряй» in any UI/push/error text → automated scan + bot guard.
- no personality judgement or psychologist-voice advice → manual audit above; re-check when copy changes.
