## Evaluation tools

Python scripts moved to `tools/`:

- `tools/accuracy_by_domain.py`
- `tools/sat_planner.py`
- `tools/sat_utils.py`

They operate on files in `data/SAT_Plan_Evaluation/`:

- `questions.csv`
- `rubric_spec.json`

Example usage (Windows PowerShell):

```powershell
py -3 .\tools\sat_planner.py --csv data\SAT_Plan_Evaluation\questions.csv --spec data\SAT_Plan_Evaluation\rubric_spec.json
py -3 .\tools\accuracy_by_domain.py --csv data\SAT_Plan_Evaluation\questions.csv --output table
```

