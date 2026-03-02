# Archon Project Memory
> Last full scan: 2026-03-01
> Repository: sasidchjfhk/AI-Software-Engineer
> Last updated: 2026-03-02 (after PR #2)


## Project Overview
This project is an AI software engineer, likely designed to perform tasks related to software development. The tech stack appears to be primarily Python-based. The purpose of the project is not clearly defined in the provided README.


## Architecture
* The project has a simple directory structure with a few key files: `app.py`, `main.py`, and `reqirments.txt`.
* The `__pycache__` directory suggests that the project is using Python 3.12 and 3.13.
* The entry point of the project is unclear, but it may be `main.py` or `app.py`.
* The `pysprit.log` file may be a log file for the project.


## Tech Stack
* Python (versions 3.12 and 3.13)
* Unknown frameworks and libraries (listed in `reqirments.txt`, but not provided)


## Team Conventions
* No prior reviews are available, so this section is empty.
- Use parameterized queries — no string concatenation for SQL (learned from PR #2)


## Known Weak Areas
* No prior reviews are available, so this section is empty.
- SQL injection vulnerability in fetchUserData in `src/utils.js` (critical, PR #2)
- Sensitive information (card number) is logged to the console in `src/utils.js` (critical, PR #2)
- Use of eval in processPayment in `src/utils.js` (critical, PR #2)


## Architecture Decisions
* The use of Python 3.12 and 3.13 suggests that the project may be intended to be compatible with multiple versions of Python.
* The presence of a `__pycache__` directory suggests that the project is using compiled Python files.


## Files to Always Check
* `app.py` and `main.py` may be critical files that need extra attention during reviews, as they may contain the main logic of the project.
* `reqirments.txt` may be important for understanding the project's dependencies.


## Manual Overrides
_This section is edited by the team. It is currently empty._
