## SAT Course Rubric — Personalized Lesson Plan

### Student snapshot
- Math Section Score: 514
- Reading & Writing Section Score: 522
- Total Score: 1036

### Domain accuracy (lower → higher priority)
- Math → Problem-Solving and Data Analysis: 0.357 (5/14)
- Reading & Writing → Craft and Structure: 0.429 (6/14)
- Math → Advanced Math: 0.444 (4/9)
- Reading & Writing → Expression of Ideas: 0.500 (6/12)
- Math → Geometry and Trigonometry: 0.556 (5/9)
- Reading & Writing → Standard English Conventions: 0.571 (8/14)
- Reading & Writing → Information and Ideas: 0.643 (9/14)
- Math → Algebra: 0.750 (9/12)

### Lesson structure (2 hours per unit)
- Warm-up diagnostics: 20 min (5 mixed quick checks from the day’s domain)
- Concept teaching (key ideas + misconceptions): 35 min (use listed lectures)
- Guided examples (I do → We do): 15 min
- Independent practice: 45 min per unit
  - Per unit: 15 easy (difficulty=1), 10 medium (difficulty=2), 5 hard (difficulty=3)
- Error log + reflection + exit ticket: 5 min

Session scaling (multiple units per lesson)
- Let n_units be the number of units covered in the lesson.
- Session total practice = n_units × per-unit quotas.
- Example: if n_units = 3 → 45 easy, 30 medium, 15 hard in total.

Question selection rule per unit
- Filter `questions.csv` by `section`, `domain`, and `difficulty`.
- Prefer items the student previously missed; otherwise randomize within the domain.

### Lesson plan (10 lessons)

1) Math — Problem-Solving and Data Analysis (Lesson 1)
- Focus: Ratios/rates/units, two-variable data, inference and margin of error, probability basics
- Lectures to use (from `lectures.json`):
  - Unit 2: Percent (2.1 Definition of Percent; 2.2 Percent Change; 2.3 Simple vs. Compound Interest)
  - Unit 2: Positive/Negative Association (2.8)
  - Unit 4: Rates (4.1–4.5)
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Problem-Solving and Data Analysis)

2) Reading & Writing — Craft and Structure (Lesson 2)
- Focus: Text structure & purpose, words in context, cross-text connections
- Lectures/resources: teacher notes on identifying purpose, structure signals, and context clues; paired passages strategy
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Craft and Structure)

3) Math — Advanced Math (Lesson 3)
- Focus: Nonlinear functions and equations, quadratics, systems, radicals
- Lectures to use:
  - Unit 1: Exponents & Radicals (1.1–1.4)
  - Unit 3: Quadratic Equations (3.4), Radical Equations (3.6), Systems (3.7)
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Advanced Math)

4) Reading & Writing — Expression of Ideas (Lesson 4)
- Focus: Rhetorical synthesis and transitions
- Lectures/resources: coherence, adding/removing sentences, transition selection by logical relation
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Expression of Ideas)

5) Math — Problem-Solving and Data Analysis (Lesson 5)
- Focus: Two-variable models & scatterplots, percentages, statistical claims/inference
- Lectures to use:
  - Unit 2: Exponential vs. Linear Growth (2.5), Linear Growth/Decay (2.6)
  - Unit 2: Positive/Negative Association (2.8)
  - Unit 4: Word Problems and unit conversions (4.5–4.6)
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Problem-Solving and Data Analysis)

6) Reading & Writing — Standard English Conventions (Lesson 6)
- Focus: Boundaries; form, structure, and sense (sentence-level grammar)
- Lectures/resources: comma splices vs. run-ons; clause types; agreement & punctuation
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Standard English Conventions)

7) Math — Geometry and Trigonometry (Lesson 7)
- Focus: Lines/angles/triangles, circles, right-triangle trig basics
- Lectures to use:
  - Geometry fundamentals (lines/angles/triangles), circles, area/volume
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Geometry and Trigonometry)

8) Reading & Writing — Information and Ideas (Lesson 8)
- Focus: Central ideas & details, command of evidence, inferences
- Lectures/resources: main idea mapping; evidence alignment; paraphrasing traps
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Information and Ideas)

9) Math — Advanced Math (Lesson 9)
- Focus: Systems and quadratics mixed set; equivalent and rational expressions review
- Lectures to use:
  - Unit 3: Systems (3.7), Quadratic Equations (3.4)
  - Unit 5: Expressions (5.1–5.4)
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Advanced Math)

10) Math — Algebra (Lesson 10)
- Focus: Linear equations/inequalities, linear functions, systems intro
- Lectures to use:
  - Unit 3: Solving linear equations (3.1–3.3)
  - Unit 5: Expressions (5.1–5.2)
- Per unit practice set: 15 easy, 10 medium, 5 hard (domain = Algebra)

### Mastery criteria (per lesson)
- Complete all practice (15E/10M/5H) with ≥ 80% overall and ≤ 3 repeated error types.
- Exit ticket: 5 questions (2E/2M/1H) ≥ 4/5 correct.
- Maintain error log with corrected solutions and rule statements.

### Weekly pacing suggestion
- 3 lessons/week (6 hours): finish in ~3.5 weeks.
- 2 lessons/week (4 hours): finish in ~5 weeks.

### Notes
- If a domain exceeds 70% accuracy after a lesson, shift one planned lesson to the lowest domain.
- Use `sat_planner.py` to re-prioritize with the latest `questions.csv` before each week.

### Score-based recommendations
- If a section’s initial score is < 600: finishing all domains (across their units) can add about 30–50 points for that section.
- If a section’s initial score is > 700: take a small domain diagnostic to identify weak skills before allocating full-study units.
- Otherwise (600–700): steady gains expected; focus on lowest-accuracy domains first.

### Terminal usage
- Print accuracy table and estimated section/total scores (prompts for targets if omitted):
  - `py -3 .\sat_planner.py --csv questions.csv --spec rubric_spec.json`
- Pass targets directly to get a readable units plan and pacing estimates:
  - `py -3 .\sat_planner.py --csv questions.csv --spec rubric_spec.json --target-math 200`
  - `py -3 .\sat_planner.py --csv questions.csv --spec rubric_spec.json --target-rw 150`
  - `py -3 .\sat_planner.py --csv questions.csv --spec rubric_spec.json --target-math 200 --target-rw 150`
- Accuracy-only utility (table or JSON output):
  - `py -3 .\accuracy_by_domain.py --csv questions.csv --output table`
  - `py -3 .\accuracy_by_domain.py --csv questions.csv --output json > results.json`
  - Optional conversion table for score estimation: `--convert conversion.csv`
- Notes:
  - `sat_planner.py` locates lectures via `rubric_spec.json` (`data_sources.lectures_json`) and falls back to `Math/lectures.json` if unspecified.
  - On Windows, run these in CMD after activating your `sat_env` if applicable.

Output includes:
- Domains prioritized by low accuracy with unit counts and cumulative points toward the target.
- Total units and hours (2 hours/unit).
- Pacing estimates assuming 1 unit/day (e.g., 2, 3, 5 days/week).
- If the target exceeds what available domains can deliver: "With this practice you can improve to ~+X points; you need more advanced practice and tests to further improve."


