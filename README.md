# SAT Materials — Lessons, Planner, and Rubric UI

This project provides SAT Reading & Writing lessons, Math lectures, and a simple in-browser rubric/plan view based on practice results.

## Quick start
- Open `index.html` in your browser.
- Use the tabs:
  - Reading & Writing: browse lesson units from `data/Reading_and_Writing/`.
  - Math: browse lecture content from `data/Math/lectures.json`.
  - Plan & Rubric: view domain accuracy from `data/SAT_Plan_Evaluation/questions.csv` and an auto-generated lesson plan derived from `data/SAT_Plan_Evaluation/rubric_spec.json`.

## Repository structure
See `docs/REPO_STRUCTURE.md`. Tooling usage is in `docs/TOOLS.md`.

## Data sources
- Questions CSV: `data/SAT_Plan_Evaluation/questions.csv`
- Rubric spec: `data/SAT_Plan_Evaluation/rubric_spec.json`
- Rubric notes: `data/SAT_Plan_Evaluation/rubric.md`
- Math lectures: `data/Math/lectures.json`
- R&W lessons: `data/Reading_and_Writing/*.json`

## Development
- UI code lives in `src/` (`src/app.js`, `src/styles.css`).
- Static data lives in `data/`.

No build step is required. Serve the folder with any static server or open `index.html` directly.
