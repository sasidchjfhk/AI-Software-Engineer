# Archon Project Memory
> Last full scan: 2026-03-03
> Repository: sasidchjfhk/AI-Software-Engineer

## Project Overview
This project is a Python-based AI Software Engineer assistant, likely designed to automate or assist with software development tasks. The system prompt is defined in `SYSTEM_PROMPT.md`, suggesting an LLM-driven agent architecture. The tech stack is primarily Python with dependencies listed in `reqirments.txt`.

## Architecture
- `main.py` — likely the primary entry point or CLI runner for the agent
- `app.py` — likely a web app or API wrapper (e.g., Flask/FastAPI) serving the agent
- `SYSTEM_PROMPT.md` — defines the AI agent's behavior and instructions
- `pysprit.log` — runtime log file; may capture agent actions or errors
- `reqirments.txt` — dependency manifest (note: filename is misspelled)
- `__pycache__/` — compiled bytecode for Python 3.12 and 3.13, suggesting dual-version usage

## Tech Stack
- Python 3.12 and 3.13
- LLM agent pattern (system prompt-based, model unknown)
- Likely Flask or FastAPI (inferred from `app.py`, unconfirmed)
- Dependencies unknown — `reqirments.txt` not provided for inspection

## Team Conventions (learned from reviews)
- Use parameterized queries, not string concatenation for SQL — `src/*.js` (PR #2)
- Validate and sanitize all user input at the boundary, not deep in logic — `src/*.js` (PR #2)
- Every async function must have proper error handling, not bare awaits — `src/*.js` (PR #2)
- Never log sensitive data (e.g., card numbers, tokens) to console or log files — `src/*.js` (PR #2)
- Use defined utility functions, not inline references to undefined symbols — `src/*.js` (PR #3)

## Known Weak Areas
- SQL injection risk — `src/*.js` — seen 3 times (PR #2, PR #3)
- Sensitive data (credit card number) written to console/log — `src/*.js` — seen 3 times (PR #2)
- Use of `eval()` with unsanitized user-supplied input — `src/*.js` — seen 2 times (PR #2)
- Authentication bypass risk — `src/*.js` — seen 2 times (PR #3)
- Undefined function reference (`processAmount`) — `src/*.js` — seen 1 time (PR #3)
- Missing error handling in async functions — `src/*.js` — seen 1 time (PR #2)
- Log file (`pysprit.log`) may capture sensitive agent output — root — seen 1 time

## Architecture Decisions
- System prompt in `SYSTEM_PROMPT.md` — externalizes agent behavior from code — reviewers: flag any hardcoded instructions inside `main.py` or `app.py` that should live in the prompt file
- Dual Python version support (3.12 + 3.13) — inferred from `__pycache__` — reviewers: flag any syntax or library usage incompatible with either version
- Split `main.py` / `app.py` entry points — suggests CLI vs. web serving separation — reviewers: verify shared logic is not duplicated between the two files

## Files to Always Check
- `main.py` — verify entry point logic, error handling, and no hardcoded secrets or prompts
- `app.py` — check for authentication middleware, input validation on all routes, and no sensitive data in responses
- `SYSTEM_PROMPT.md` — review for prompt injection risks or instructions that could be exploited
- `pysprit.log` — check that no sensitive data (API keys, user input, PII) is being logged
- `reqirments.txt` — verify no outdated or vulnerable dependencies; note filename typo may cause CI tooling misses

## Manual Overrides
_This section is edited by the team. It is currently empty._