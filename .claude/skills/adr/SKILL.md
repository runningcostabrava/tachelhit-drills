---
name: adr
description: The ADR wizard — ask one question at a time about a technical decision, then write the numbered record in docs/adr/ and open a pull request. Use when a decision would be costly to undo.
---

# The ADR wizard

An Architectural Decision Record says **why** something was decided, and what was turned down. It
exists for the person who arrives later and finds the code without the reason — most often the
owner, three months on.

## When to write one

Write one when undoing the decision would cost real work: the shape of the data, who may do what,
a provider outside the project, the format of a lesson, what may enter the library. Do **not**
write one for a variable name, a layout tweak, or anything a single commit could reverse.

## How to run it

**One question at a time.** Wait for the answer before asking the next one — a wizard that asks
four things at once is a form, and a form gets filled in badly.

1. **What happened?** What was seen, where, and what did not work. Ask for the fact, not the
   intention; if there is a measurement, ask for it.
2. **What else could we do?** Collect the options, including doing nothing. For each, what it has
   going for it and against it. If the owner names only one, offer the obvious alternatives and
   let them be rejected on the record — a rejected option is half the value of an ADR.
3. **What do we decide, and why this one?** One sentence for the decision.
4. **What does it cost?** What this now forces or forbids, and what gets worse. A decision with no
   drawback usually means the drawback has not been looked for.

Then:

- read `docs/adr/` and take the next free number (`0002`, `0003`, …);
- write `docs/adr/<n>-<short-name-in-catalan>.md` from `docs/adr/0000-plantilla.md`, in Catalan,
  with the owner's own words where they said something well;
- branch `docs/<issue>-adr-<n>`, commit, and open the pull request following
  `.claude/skills/project/SKILL.md`.

## Rules

- An accepted ADR is not edited afterwards. If the decision changes, write a new one that says it
  supersedes the old, and add a line to the old one pointing forward.
- The record carries the issue number when there is one, and the date it was accepted.
- Never invent the context: if what happened is not clear, ask again rather than fill the gap.

## Written and still missing

`0001` records the decision to keep ADRs. These were decided on 21-22 October 2026 and still need
writing: audio in Tamazight only, the note kept per (sentence, unit) pair, who may change a drill,
and mail over a provider's HTTPS API because Render blocks SMTP.
