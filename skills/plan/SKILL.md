---
name: plan
description: Draft one or more of your Commander decks' output/decks/<slug>/plan.md with a planner agent per deck, from the list and oracle text, show the drafts for your review and install the ones you approve, the plan each replaces kept as notes.md. Use for /plan <slug ...>, or when the owner asks for a deck's plan to be written.
argument-hint: "<slug> [slug ...]"
---

# plan

Run `python3 ${CLAUDE_PLUGIN_ROOT}/lib/settings.py` with the
arguments' `key=value` words for this run's settings. Dispatch every agent
`run_in_background` in the folder that holds `output/`, with `model` the
agent's entry in `models`; its prompt carries only the per-run
inputs named below.

For `/plan <slug> [slug ...]`:

1. Make a fresh scratchpad folder `<run>/`.
2. Dispatch one `mtg-toolbox:planner` per slug, its prompt giving `<run>`
   and the slug.
3. When all are back, show each draft, `<run>/<slug>-plan.md`, in chat and
   ask the owner which to install, a plain question, once.
4. For each approved slug: if `output/decks/<slug>/plan.md` exists and
   differs from the draft, move it to `output/decks/<slug>/notes.md`,
   overwriting an older one; then copy the draft to
   `output/decks/<slug>/plan.md`.
5. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/plan_check.py <slug> ...` with
   the approved slugs.

Report: per deck installed or kept, and the lines `plan_check.py` printed.
