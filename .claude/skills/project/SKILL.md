---
name: project
description: How work is done in this repository — issue-driven, one branch per issue, local tests, PR, CI green, then merge. Read this before starting any work on tachelhit-drills.
---

# How work is done here

Work is driven by GitHub issues, not by chat. The scope this project answers to is
`docs/SCOPE.md`; decisions that cost something to undo live in `docs/adr/`.

## When an idea arrives

An idea from the owner is not a task until it has been placed. Decide which of these it is, say
which one, and act accordingly:

| the idea is | what to do |
|---|---|
| **a small thing inside the scope** | open the issue, branch, do it |
| **a big feature that widens the scope** | **stop.** Ask whether the scope should grow. If yes, run the ADR wizard, then write the issues |
| **a technical shift inside the scope** (another store, another provider, a different data shape) | **stop.** Run the ADR wizard first: the record is written before the code |
| **an idea for later** | offer to park it as a `backlog` issue, and leave the current scope alone |
| **a bug or a layout constraint** | issue with acceptance criteria that name the constraint, measurable |

Placing it is not a formality: most of what went wrong in this repository went wrong because a
technical shift was made as if it were a small thing.

## Layout work

A screen is finished when it cannot break, not when it looks right once. An issue about layout
carries acceptance criteria that say, in terms a test can check:

- which layout mechanism holds the section together (flex, grid) and what must not change it;
- what may overlap and what may never (stacking, `z-index`, sticky headers over cards);
- the widths it must survive: 360, 768, 1280 and 1920 CSS pixels;
- what happens when the content is long: a sentence of 90 characters, a word with no spaces, a
  missing image, Tifinagh next to Latin on one line.

Test it at those widths before the pull request — with the browser tools when they are available,
resizing and looking, not by reasoning about the CSS.

## The lifecycle

1. **An issue, assigned.** Nothing is coded without an issue the owner has assigned. If a request
   arrives in chat, turn it into an issue first (`gh issue create`, labelled `feature`, `bug`,
   `chore`, `content`, or `blocked-on-owner`) and ask for it to be assigned. Exception: a change
   the owner approved as a plan in that same conversation.
2. **A branch per issue.** `feat/<n>-<short-name>`, `fix/<n>-…`, `chore/<n>-…`, `docs/<n>-…`,
   cut from an up-to-date `origin/main`. Never commit to `main`.
3. **Tests before the pull request**, run locally and green:
   - `cd backend && venv/Scripts/python.exe -X utf8 -m pytest tests -q`
   - `cd frontend && npx tsc -b && npm run build`
   Red tests are never explained away; they are fixed or the work is not finished.
4. **The pull request.** Against `main`, body in Catalan saying what was wrong and what changed,
   with `Closes #<n>`. End it with the attribution line the session requires.
5. **Wait for CI.** `.github/workflows/ci.yml` runs the backend suite and the web typecheck and
   build. **A red check is never merged** — not even when it looks like a flake. If it is a flake,
   say so with the evidence (a green run of the same commit elsewhere), or re-run it; do not merge
   on a hunch. This rule exists because PR #179 was merged with iOS red.
6. **Merge and close.** Squash, the issue closes itself through `Closes #<n>`.

## What never changes

- **A speaker's words are theirs.** No machine rewrites `text_tachelhit`, `text_catalan` or
  `text_arabic` in production; automatic output goes to the `*_suggested` fields and a person
  decides. See `docs/SCOPE.md`.
- **Nothing is deleted from production without an explicit yes** from the owner, and never without
  writing the full rows to a file first.
- **No secrets in the repository.** `backend/.env` holds the keys; `.env` is never committed and
  no key is ever pasted into a commit, a PR body or a test.
- **Never a bare `git stash`.** The stash is shared with the other worktrees and other sessions:
  use a WIP commit, or `git stash push -u -m "<tag>"` and `apply <sha>`.
- **Patches are written with the editor**, not with shell heredocs: a heredoc eats backslashes and
  has corrupted regexes and Windows paths in this repo more than once.

## Where things are

| | |
|---|---|
| scope | `docs/SCOPE.md` |
| decisions | `docs/adr/`, wizard at `.claude/skills/adr/` |
| repo map and rules | `CLAUDE.md` |
| backend | `backend/` (FastAPI, SQLite locally, Postgres on Render) |
| web and mobile | `frontend/` (React + Vite + Capacitor) |
| CI | `.github/workflows/ci.yml` |

## Writing

Commits and PR bodies in Catalan, plain and concrete: what was wrong, what changed, what it costs.
Code and code comments in English, in the voice of the file they live in. A comment says why, not
what — the code already says what.
