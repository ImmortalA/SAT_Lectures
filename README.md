# SAT Materials — Lessons, Planner, and Rubric UI

This project provides SAT Reading & Writing lessons, Math lectures, and a simple in-browser rubric/plan view based on practice results.

## Quick start
- Open `index.html` in your browser.
- Use the tabs:
  - **Reading & Writing**: browse lessons from `data/Reading_and_Writing/sat_full_lessons.json` with unified schema.
  - **Math**: browse lessons from `data/Math/lectures.json` with unified schema.
  - **Plan & Rubric**: view domain accuracy and generate personalized study plans based on target score improvements and available time.

## Features
- **Unified Lesson Schema**: Both R&W and Math use the same lesson format with `id`, `title`, `description`, `duration`, `difficulty`, `subject`, `unit`, `category`, `completed`, `locked`, `progress`, and `content` fields.
- **Interactive Planning**: Set target score improvement and study weeks to get a personalized schedule.
- **Search & Filter**: Find lessons by title, subject, unit, or description.
- **Progress Tracking**: Lessons remember your last viewed content.

## Repository structure
See `docs/REPO_STRUCTURE.md`. Tooling usage is in `docs/TOOLS.md`.

## Data sources
- **Questions CSV**: `data/SAT_Plan_Evaluation/questions.csv` - student performance data
- **Rubric spec**: `data/SAT_Plan_Evaluation/rubric_spec.json` - planning parameters
- **Rubric notes**: `data/SAT_Plan_Evaluation/rubric.md` - additional rubric documentation
- **Math lessons**: `data/Math/lectures.json` - 20 comprehensive math lessons
- **R&W lessons**: `data/Reading_and_Writing/sat_full_lessons.json` - unified R&W lessons

## Lesson Schema Format
Each lesson follows this structure:
```json
{
  "id": "1",
  "title": "Introduction to Linear Functions",
  "description": "Learn the basics of linear functions and their graphs",
  "duration": 15,
  "difficulty": "Easy",
  "subject": "Algebra",
  "unit": "Unit 1: Algebra Fundamentals", 
  "category": "Linear Functions",
  "completed": false,
  "locked": false,
  "progress": 0,
  "content": "# Introduction to Linear Functions\n\n## What is a Linear Function?\n..."
}
```

## Development
- UI code lives in `src/` (`src/app.js`, `src/styles.css`).
- Static data lives in `data/`.
- No build step required. Serve the folder with any static server or open `index.html` directly.
