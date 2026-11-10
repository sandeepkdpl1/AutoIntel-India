"""Phase 3: validate, clean, process, and generate reproducible EDA outputs.
Run from the AutoIntel_India project folder: python scripts/clean_analyze.py
"""
from pathlib import Path
import json,sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data'/'raw'; OUT=ROOT/'data'/'processed'; REPORT=ROOT/'outputs'
OUT.mkdir(parents=True,exist_ok=True);REPORT.mkdir(exist_ok=True)
NAMES={'forecast_monthly':'forecast_monthly.csv','dashboard_estimates':'dashboard_estimates.csv','car_specs':'car_specs.csv','master_estimates':'master_estimates.csv'}
frames={k:pd.read_csv(RAW/v) for k,v in NAMES.items()}
checks=[]
def check(label,ok,detail=''):
    checks.append({'check':label,'passed':bool(ok),'detail':str(detail)})
    if not ok:print('WARNING:',label,detail)
for k,df in frames.items():
    check(k+' nonempty',len(df)>0,len(df))
    check(k+' no exact duplicates',not df.duplicated().any(),int(df.duplicated().sum()))
    check(k+' year bounds',df.Year.between(2022,2026).all(),'2022–2026')
    for col in ('Manufacturer','Model_Name'):
        if col in df:df[col]=df[col].astype('string').str.strip()
    if 'Estimated_Registrations' in df:
        df['Estimated_Registrations']=pd.to_numeric(df['Estimated_Registrations'],errors='coerce')
        check(k+' nonnegative estimates',df.Estimated_Registrations.notna().all() and df.Estimated_Registrations.ge(0).all())
    frames[k]=df
f=frames['forecast_monthly'];a=frames['dashboard_estimates'];m=frames['master_estimates'];s=frames['car_specs']
check('forecast monthly unique',not f.duplicated(['Year','Month','Manufacturer','Model_Name']).any())
check('dashboard aggregate unique',not a.duplicated(['Year','Month','Manufacturer','Body_Style','Fuel_Type']).any())
check('specifications model unique',not s.duplicated(['Manufacturer','Model_Name']).any())
check('master monthly unique',not m.duplicated(['Year','Month','Manufacturer','Model_Name']).any())
check('forecast/dashboard/master totals match',f.Estimated_Registrations.sum()==a.Estimated_Registrations.sum()==m.Estimated_Registrations.sum(),f'{f.Estimated_Registrations.sum():,.0f}')
check('master estimates clearly labeled',m.Registration_Data_Status.eq('Industry Model Estimate').all())
# Explicit month consistency: Date, Month_Num, Month must agree
f['Date']=pd.to_datetime(f.Date,errors='coerce')
check('forecast date valid',f.Date.notna().all())
check('forecast date/month/year consistent',((f.Date.dt.year==f.Year)&(f.Date.dt.month==f.Month_Num)).all())
check('forecast covers 2026 only through October',f.loc[f.Year==2026,'Month_Num'].max()<=10)
# Preserve missing values: NA in EV engine and ICE battery fields is often not applicable.
# Keep provenance; do not replace unknown ratings or feature flags with fabricated values.
s=s.drop(columns=['Year','Month','Estimated_Registrations','Registration_Data_Status'],errors='ignore').copy()
frames['car_specs']=s
for name,df in frames.items():df.to_csv(OUT/(name+'.csv'),index=False)
with sqlite3.connect(ROOT/'database'/'autointel.db') as con:
    for name,df in frames.items():df.to_sql(name,con,if_exists='replace',index=False)
    con.execute('CREATE INDEX IF NOT EXISTS idx_forecast_date ON forecast_monthly(Date)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_forecast_model ON forecast_monthly(Manufacturer,Model_Name)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_dashboard_brand ON dashboard_estimates(Manufacturer,Year)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_specs_model ON car_specs(Manufacturer,Model_Name)')
# Analyses on estimates, not official registration data
annual=f.groupby('Year',as_index=False).Estimated_Registrations.sum()
annual.to_csv(REPORT/'annual_estimated_volumes.csv',index=False)
brand=f.groupby('Manufacturer',as_index=False).Estimated_Registrations.sum().sort_values('Estimated_Registrations',ascending=False)
brand.to_csv(REPORT/'brand_estimated_volumes.csv',index=False)
monthly=f.groupby('Date',as_index=False).Estimated_Registrations.sum().sort_values('Date')
monthly.to_csv(REPORT/'monthly_estimated_volumes.csv',index=False)
model=f.groupby(['Manufacturer','Model_Name'],as_index=False).Estimated_Registrations.sum().sort_values('Estimated_Registrations',ascending=False)
model.to_csv(REPORT/'model_estimated_volumes.csv',index=False)
fuel=a.groupby(['Year','Fuel_Type'],as_index=False).Estimated_Registrations.sum()
fuel.to_csv(REPORT/'fuel_type_estimated_volumes.csv',index=False)
# Note 2026 is partial: do not directly compare its total to full calendar years.
plt.figure(figsize=(10,4.8));plt.plot(monthly.Date,monthly.Estimated_Registrations);plt.title('Monthly estimated registrations (not official VAHAN counts)');plt.xlabel('Month');plt.ylabel('Estimated registrations');plt.tight_layout();plt.savefig(REPORT/'01_monthly_trend.png',dpi=160);plt.close()
plt.figure(figsize=(10,5.2));top=brand.head(12).sort_values('Estimated_Registrations');plt.barh(top.Manufacturer,top.Estimated_Registrations);plt.title('Top manufacturers: summed estimates, 2022–Oct 2026');plt.xlabel('Estimated registrations');plt.tight_layout();plt.savefig(REPORT/'02_manufacturer_ranking.png',dpi=160);plt.close()
fig,ax=plt.subplots(figsize=(10,5));pivot=fuel.pivot(index='Year',columns='Fuel_Type',values='Estimated_Registrations').fillna(0);pivot.plot(kind='bar',stacked=True,ax=ax);ax.set_title('Fuel-type estimated volumes (2026 partial year)');ax.set_ylabel('Estimated registrations');fig.tight_layout();fig.savefig(REPORT/'03_fuel_mix.png',dpi=160);plt.close(fig)
missing=s.isna().sum().sort_values(ascending=False)
missing.rename('missing_rows').to_csv(REPORT/'specification_missing_values.csv')
summary={'row_counts':{k:len(v) for k,v in frames.items()},'model_count':int(s[['Manufacturer','Model_Name']].drop_duplicates().shape[0]),'manufacturer_count':int(s.Manufacturer.nunique()),'year_range':[int(f.Year.min()),int(f.Year.max())],'estimate_total':int(f.Estimated_Registrations.sum()),'checks_passed':sum(x['passed'] for x in checks),'checks_total':len(checks),'important_notes':['All model-level volumes are industry estimates, not official registrations or sales.','2026 is a partial year (through October); avoid comparing unadjusted totals with complete years.','Missing vehicle attributes may be not applicable; do not automatically fill with zero.','Specification source verification remains a separate manual task.','These EDA charts describe the supplied dataset, not the actual national market.']}
(REPORT/'data_quality_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
pd.DataFrame(checks).to_csv(REPORT/'data_validation_checks.csv',index=False)
print(json.dumps(summary,indent=2));print('Outputs saved to',REPORT)
