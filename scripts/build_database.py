"""Rebuild SQLite database from provided CSVs. Run from the project root."""
from pathlib import Path
import sqlite3
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data'/'raw'
DB=ROOT/'database'/'autointel.db'
inputs={'forecast_monthly':'forecast_monthly.csv','dashboard_estimates':'dashboard_estimates.csv','car_specs':'car_specs.csv'}
DB.parent.mkdir(parents=True,exist_ok=True)
with sqlite3.connect(DB) as con:
    for table,name in inputs.items():
        df=pd.read_csv(RAW/name)
        if table=='car_specs':
            df=df.drop(columns=['Year','Month','Estimated_Registrations','Registration_Data_Status'],errors='ignore')
            assert not df.duplicated(['Manufacturer','Model_Name']).any(), 'Duplicate model specifications'
        elif table=='forecast_monthly':
            assert not df.duplicated(['Year','Month','Manufacturer','Model_Name']).any(), 'Duplicate forecast keys'
        else:
            assert not df.duplicated(['Year','Month','Manufacturer','Body_Style','Fuel_Type']).any(), 'Duplicate dashboard keys'
        df.to_sql(table,con,if_exists='replace',index=False)
        print(f'{table}: {len(df)} rows')
    con.execute('CREATE INDEX IF NOT EXISTS ix_forecast_date ON forecast_monthly(Date)')
    con.execute('CREATE INDEX IF NOT EXISTS ix_forecast_brand ON forecast_monthly(Manufacturer, Model_Name)')
    con.execute('CREATE INDEX IF NOT EXISTS ix_dash_brand ON dashboard_estimates(Manufacturer,Year)')
    con.execute('CREATE INDEX IF NOT EXISTS ix_specs_model ON car_specs(Manufacturer,Model_Name)')
print('Created',DB)
