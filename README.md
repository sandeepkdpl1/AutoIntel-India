# AutoIntel India — Phase 1 & 2 starter

## Setup on Windows (VS Code terminal)

1. Install Python 3.11 or 3.12 and VS Code with the Python extension.
2. Extract this ZIP to a folder such as `Documents/AutoIntel_India`.
3. Open that folder in VS Code.
4. Run the following in the VS Code terminal (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/build_database.py
python -m streamlit run app.py
```

If PowerShell blocks activation, use Command Prompt with `.venv\Scripts\activate.bat` instead, or run `.venv\Scripts\python.exe` explicitly.

## What is included

- `data/raw/`: four user-supplied CSV datasets (master kept for audit; not imported twice)
- `data/processed/`: three project-ready CSVs
- `database/autointel.db`: prebuilt SQLite database
- `scripts/build_database.py`: reproducible SQLite import
- `app.py`: working Streamlit starter with overview, OEM, dealer and comparison pages
- `DATA_AUDIT.md`: scope, data warnings and validation checks

## Data limitations

**Registration volumes in the model-wise CSV are labelled `Industry Model Estimate`.** They are not verified VAHAN counts or manufacturer sales. Dashboard and forecasting labels must preserve this qualification. OEM specification verification labels are user-provided and do not establish independent verification. Regional dealer insights need separately sourced state/RTO data.

## Next development phase

Implement model-wise dashboard filters, weighted customer recommendation, time-based forecasting, AI assistant, and deployment. Do not publish API secrets or pretend estimates are official registrations.
