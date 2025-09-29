## Repository structure

- `index.html`: Entry point; references `src/app.js` and `src/styles.css`.
- `src/`
  - `app.js`: UI logic for tabs, lessons, and rubric view.
  - `styles.css`: Minimal styling.
- `data/`
  - `Reading_and_Writing/`: Lesson JSON files and `lessons_manifest.json`.
  - `Math/lectures.json`: Math lectures and section content.
  - `SAT_Plan_Evaluation/`
    - `questions.csv`: Practice history used to compute domain accuracy.
    - `rubric_spec.json`: Parameters for quotas, thresholds, and structure.
    - `rubric.md`: Explanatory notes rendered in the rubric view.

To add or update content, drop files into the `data/` folders and the UI will pick them up on reload.

