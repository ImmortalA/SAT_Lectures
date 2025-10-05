## Repository structure

- `index.html`: Entry point; references `src/app.js` and `src/styles.css`.
- `src/`
  - `app.js`: UI logic for tabs, lessons, and rubric view with unified schema support.
  - `styles.css`: Minimal styling for responsive layout.
- `data/`
  - `Reading_and_Writing/`
    - `sat_full_lessons.json`: Unified R&W lessons with new schema format.
  - `Math/`
    - `lectures.json`: Math lessons using unified schema format (20 comprehensive lessons).
  - `SAT_Plan_Evaluation/`
    - `questions.csv`: Practice history used to compute domain accuracy.
    - `rubric_spec.json`: Parameters for quotas, thresholds, and lesson planning.
    - `rubric.md`: Explanatory notes for the rubric system.
- `docs/`
  - `REPO_STRUCTURE.md`: This file, explaining the project organization.
  - `TOOLS.md`: Documentation for Python evaluation scripts.
  - `scoring.png`, `table.txt`: Supporting documentation files.
- `tools/`
  - `sat_planner.py`: Python script for SAT lesson planning.
  - `accuracy_by_domain.py`: Domain accuracy analysis script.
  - `sat_utils.py`: Utility functions for SAT analysis.

## Lesson Schema
Both R&W and Math lessons now use a unified schema with these fields:
- `id`: Unique identifier
- `title`: Lesson title
- `description`: Brief description
- `duration`: Estimated minutes
- `difficulty`: Easy/Medium/Hard
- `subject`: Subject area (e.g., Algebra, Reading & Writing)
- `unit`: Unit grouping
- `category`: Specific category within subject
- `completed`: Boolean completion status
- `locked`: Boolean lock status
- `progress`: Progress percentage (0-100)
- `content`: Lesson content in markdown format

To add or update content, modify the JSON files in `data/` folders and the UI will pick them up on reload.

