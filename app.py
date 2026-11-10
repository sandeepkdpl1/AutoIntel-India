from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

st.set_page_config(page_title='AutoIntel India', page_icon='🚗', layout='wide')
DB = Path(__file__).resolve().parent / 'database' / 'autointel.db'

@st.cache_data
def query(sql):
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query(sql, conn)

st.title('🚗 AutoIntel India')
st.caption('Prototype | 2022–2026 | Model-wise registration volumes are industry estimates, NOT official VAHAN registrations or OEM sales.')
page = st.sidebar.radio(
    'Select dashboard',
    [
        'Overview',
        'OEM insights',
        'Dealer insights',
        'Car comparison',
        'ML Forecasting',
        'Smart Car Recommendation',
        'AI Car Advisor'
    ]
)

monthly = query('SELECT Year, Month, Manufacturer, Model_Name, Estimated_Registrations, Date FROM forecast_monthly')
monthly['Date'] = pd.to_datetime(monthly['Date'])
specs = query('SELECT * FROM car_specs')

if page == 'Overview':
    by_month = monthly.groupby('Date', as_index=False)['Estimated_Registrations'].sum()
    st.metric('Car models covered', len(specs))
    st.plotly_chart(px.line(by_month, x='Date', y='Estimated_Registrations', title='Estimated monthly registration volume'), use_container_width=True)
    st.dataframe(monthly.head(30), use_container_width=True)
elif page == 'OEM insights':
    year = st.selectbox('Year', sorted(monthly.Year.unique(), reverse=True))
    df = monthly[monthly.Year == year].groupby('Manufacturer', as_index=False)['Estimated_Registrations'].sum().sort_values('Estimated_Registrations',ascending=False)
    st.plotly_chart(px.bar(df, x='Manufacturer', y='Estimated_Registrations', title=f'Estimated manufacturer volume: {year}'), use_container_width=True)
    st.dataframe(df, use_container_width=True)
elif page == 'Dealer insights':
    maker = st.selectbox('Manufacturer', sorted(monthly.Manufacturer.unique()))
    df = monthly[monthly.Manufacturer == maker].groupby(['Date'],as_index=False)['Estimated_Registrations'].sum()
    st.plotly_chart(px.line(df,x='Date',y='Estimated_Registrations',title=f'Estimated demand trend: {maker}'),use_container_width=True)
    st.info('Regional demand and dealer inventory planning require separate state-level or dealer data. National model estimates cannot establish local demand.')
elif page == 'Car comparison':
    options = sorted(specs['Manufacturer'].astype(str) + ' — ' + specs['Model_Name'].astype(str))
    chosen = st.multiselect('Choose up to 3 cars', options, max_selections=3)
    if chosen:
        specs['label'] = specs['Manufacturer'].astype(str) + ' — ' + specs['Model_Name'].astype(str)
        cols = ['Manufacturer','Model_Name','Variant_Name','Fuel_Type','Price_Min_INR','Price_Max_INR','Mileage_kmpl','Claimed_Range_km','Seating_Capacity','Transmission_Type','Safety_NCAP_Rating','Specification_Source_URL']
        st.dataframe(specs[specs.label.isin(chosen)][cols].set_index('Model_Name').T, use_container_width=True)
        st.warning('Specification values are sourced from the supplied CSV and have not been independently verified.')

elif page == 'ML Forecasting':
    st.header('Machine Learning Forecasting')
    st.caption(
        'One-month-ahead evaluation on estimated registrations.'
    )

    forecast_dir = Path(__file__).resolve().parent / 'outputs' / 'forecasting'

    metrics_file = forecast_dir / 'model_comparison.csv'
    predictions_file = forecast_dir / 'test_predictions.csv'

    if not metrics_file.exists() or not predictions_file.exists():
        st.error('Forecasting files not found.')
        st.stop()

    metrics = pd.read_csv(metrics_file)
    predictions = pd.read_csv(
        predictions_file, parse_dates=['Date']
    )

    st.subheader('Model Performance Comparison')

    best = metrics.sort_values('MAE').iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric('Best Model', best['Model'])
    c2.metric('MAE', f"{best['MAE']:.2f}")
    c3.metric('R² Score', f"{best['R2']:.4f}")

    st.dataframe(metrics.round(4), width='stretch')

    fig1 = px.bar(
        metrics,
        x='Model',
        y='MAE',
        color='Model',
        title='Model Comparison — MAE'
    )
    st.plotly_chart(fig1, width='stretch')

    st.subheader('Actual vs Predicted — 2026')

    chart_columns = [
        'Estimated_Registrations',
        'Previous Month Baseline',
        'Linear Regression',
        'Random Forest'
    ]

    monthly_results = predictions.groupby(
        'Date', as_index=False
    ).sum(numeric_only=True)

    fig2 = px.line(
        monthly_results,
        x='Date',
        y=chart_columns,
        markers=True,
        title='Estimated Registrations vs Predictions'
    )
    st.plotly_chart(fig2, width='stretch')

    st.subheader('Manufacturer-Level Evaluation')

    selected_maker = st.selectbox(
        'Select Manufacturer',
        sorted(predictions['Manufacturer'].unique())
    )

    maker_data = predictions[
        predictions['Manufacturer'] == selected_maker
    ]

    maker_monthly = maker_data.groupby(
        'Date', as_index=False
    ).sum(numeric_only=True)

    fig3 = px.line(
        maker_monthly,
        x='Date',
        y=chart_columns,
        markers=True,
        title=f'{selected_maker} — Forecast Evaluation'
    )
    st.plotly_chart(fig3, width='stretch')

    st.warning(
        'The figures are industry-estimated registrations, '
        'not official VAHAN records. The evaluation uses '
        'observed previous-month values and is not a '
        'fully independent future forecast.'
    )



elif page == 'Smart Car Recommendation':

    st.header('🚗 Smart Car Recommendation System')
    st.write(
        'Find suitable cars based on your budget, '
        'fuel preference and preferred vehicle type.'
    )

    # Customer preferences
    
    min_price_lakh, max_price_lakh = st.slider(
        'Select Price Range (₹ Lakhs)',
        min_value=0,
        max_value=50,
        value=(5, 15),
        step=1
    )

    min_budget = min_price_lakh * 100000
    max_budget = max_price_lakh * 100000


    fuel_options = ['Any'] + sorted(
        specs['Fuel_Type'].dropna().astype(str).unique()
    )

    fuel = st.selectbox(
        'Preferred Fuel Type',
        fuel_options
    )

    
    # Merge similar vehicle body styles
    body_style_map = {
        'HATCHBACK': 'Hatchback',
        'SEDAN': 'Sedan',
        'COMPACT SEDAN': 'Sedan',
        'LUXURY SEDAN': 'Sedan',

        'COMPACT SUV': 'Compact SUV',
        'SUBCOMPACT SUV': 'Compact SUV',
        'SMALL SUV': 'Compact SUV',
        'MICRO SUV': 'Compact SUV',

        'SUV': 'SUV',
        'MID-SIZE SUV': 'SUV',
        'MIDSIZE SUV': 'SUV',
        'FULL-SIZE SUV': 'SUV',
        'COUPE SUV': 'SUV',

        'MPV': 'MPV / MUV',
        'MUV': 'MPV / MUV'
    }

    specs = specs.copy()

    specs['Vehicle_Category'] = (
        specs['Body_Style']
        .fillna('')
        .astype(str)
        .str.strip()
        .str.upper()
        .map(body_style_map)
        .fillna('Other')
    )

    preferred_order = [
        'Hatchback',
        'Sedan',
        'Compact SUV',
        'SUV',
        'MPV / MUV'
    ]

    available_types = specs['Vehicle_Category'].unique()

    vehicle_types = ['Any'] + [
        category for category in preferred_order
        if category in available_types
    ]

        
    if 'Other' in available_types:
        vehicle_types.append('Other Vehicles')


    vehicle_type = st.selectbox(
        'Preferred Vehicle Type',
        vehicle_types
    )

    # Transmission preference
    transmission_options = [
        'Any',
        'Manual',
        'Automatic'
    ]

    transmission = st.selectbox(
        'Preferred Transmission',
        transmission_options
    )

    # Prepare car specifications
    cars = specs.copy()

    cars['Price_Min_INR'] = pd.to_numeric(
        cars['Price_Min_INR'],
        errors='coerce'
    )

    cars['Price_Max_INR'] = pd.to_numeric(
        cars['Price_Max_INR'],
        errors='coerce'
    )
    
    # Price range overlap filter
    cars = cars.dropna(
        subset=['Price_Min_INR', 'Price_Max_INR']
    )

    cars = cars[
        (cars['Price_Min_INR'] <= max_budget) &
        (cars['Price_Max_INR'] >= min_budget)
    ].copy()


    # Vehicle type filter
    
    # Filter using simplified vehicle categories
    if vehicle_type != 'Any':
        selected_category = (
            'Other' if vehicle_type == 'Other Vehicles'
            else vehicle_type
        )

        cars = cars[
            cars['Vehicle_Category'] == selected_category
        ].copy()



    # Fuel type filter
    if fuel != 'Any':
        cars = cars[
            cars['Fuel_Type'].astype(str) == fuel
        ].copy()
    
    
    # Transmission filter
    if transmission != 'Any':
        transmission_values = (
            cars['Transmission_Type']
            .fillna('')
            .astype(str)
            .str.strip()
            .str.upper()
        )

        if transmission == 'Manual':
            cars = cars[
                transmission_values.isin(['MANUAL', 'MT'])
            ].copy()
        else:
            cars = cars[
                transmission_values.isin([
                    'AUTOMATIC', 'AT', 'AMT',
                    'CVT', 'DCT', 'DSG',
                    'E-CVT', 'IVT'
                ])
            ].copy()

    if cars.empty:
        st.warning(
            'No matching cars found. Try increasing your '
            'budget or changing your preferences.'
        )

    else:
        
        # Lower-priced cars within the chosen range score higher
        
        # Calculate overlap with customer budget
        overlap_min = cars['Price_Min_INR'].clip(
            lower=min_budget
        )

        overlap_max = cars['Price_Max_INR'].clip(
            upper=max_budget
        )

        overlap_amount = (
            overlap_max - overlap_min
        ).clip(lower=0)

        budget_span = max(
            max_budget - min_budget, 1
        )

        # Percentage of selected budget covered
        cars['Recommendation_Score'] = (
            overlap_amount / budget_span * 100
        ).clip(0, 100).round(2)

        cars = cars.sort_values(
            'Recommendation_Score',
            ascending=False
        )


        
        st.success(
            f'{len(cars)} matching car models found!'
        )

        cars['Starting_Price_Lakh'] = (
            cars['Price_Min_INR'] / 100000
        ).round(2)

        cars['Maximum_Price_Lakh'] = (
            cars['Price_Max_INR'] / 100000
        ).round(2)

        cars['Matching_From_Lakh'] = (
            cars['Price_Min_INR']
            .clip(lower=min_budget) / 100000
        ).round(2)

        cars['Matching_To_Lakh'] = (
            cars['Price_Max_INR']
            .clip(upper=max_budget) / 100000
         ).round(2)
     
        st.subheader('Recommended Cars')

        
        
        
        display_cols = [
            'Manufacturer',
            'Model_Name',
            'Vehicle_Category',
            'Variant_Name',
            'Fuel_Type',
            'Starting_Price_Lakh',
            'Maximum_Price_Lakh',
            'Matching_From_Lakh',
            'Matching_To_Lakh',
            'Transmission_Type',
            'Recommendation_Score'
        ]

        st.dataframe(
            cars[display_cols].round(2),
            width='stretch',
            hide_index=True
        )

        st.subheader('Top 5 Recommendations')

        top5 = cars.head(5)

        fig = px.bar(
            top5,
            x='Model_Name',
            y='Recommendation_Score',
            color='Manufacturer',
            title='Top 5 Cars by Price-Range Overlap'
        )

        st.plotly_chart(
            fig,
            width='stretch'
        )
        
        st.info(
            'Cars are selected when their listed model '
            'price range overlaps with your chosen budget. '
            'The score measures the percentage of your '
            'selected budget covered by that price range. '
            'Exact variant availability and prices must '
            'be confirmed with the dealer.'
        )

        st.warning(
            'Vehicle specifications and prices come from '
            'the supplied academic dataset and have not '
            'been independently verified. Check current '
            'prices and variants with authorised dealers.'
        )

elif page == 'AI Car Advisor':

    st.header('🤖 Gemini AI Car Advisor')

    st.write(
        'Ask questions about cars available in the '
        'AutoIntel India dataset.'
    )


    ai_budget_lakh = st.slider(
        'Maximum Budget for AI Recommendations (₹ Lakhs)',
        min_value=1,
        max_value=50,
        value=15,
        step=1,
        key='ai_budget_lakh'
    )

    question = st.text_area(
        'What would you like to know?',
        placeholder='Example: Suggest automatic SUVs under ₹15 lakh'
    )

    if st.button('Ask Gemini AI'):

        if not question.strip():
            st.warning('Please enter a question.')

        else:
            try:
                # Load the existing car specifications
                ai_cars = specs.copy()

                # Customer budget for AI recommendations
                ai_budget_lakh = st.session_state.get(
                    'ai_budget_lakh', 15
                )
                ai_budget = ai_budget_lakh * 100000

                # Convert prices to numbers
                ai_cars['Price_Min_INR'] = pd.to_numeric(
                    ai_cars['Price_Min_INR'],
                    errors='coerce'
                )
                ai_cars['Price_Max_INR'] = pd.to_numeric(
                    ai_cars['Price_Max_INR'],
                    errors='coerce'
                )

                # Keep cars with prices overlapping the budget
                ai_cars = ai_cars[
                    (ai_cars['Price_Min_INR'] <= ai_budget) &
                    (ai_cars['Price_Max_INR'] >= 0)
                ].copy()


                # Select useful columns for the AI
                ai_columns = [
                    'Manufacturer',
                    'Model_Name',
                    'Variant_Name',
                    'Body_Style',
                    'Fuel_Type',
                    'Transmission_Type',
                    'Price_Min_INR',
                    'Price_Max_INR',
                    'Mileage_kmpl',
                    'Claimed_Range_km',
                    'Seating_Capacity',
                    'Safety_NCAP_Rating'
                ]

                car_data = ai_cars[ai_columns].fillna(
                    'Not available'
                ).to_json(orient='records')

                client = genai.Client(
                    api_key=st.secrets['GEMINI_API_KEY']
                )

                prompt = f"""
You are the AutoIntel India AI Car Advisor.

Answer the customer's question using ONLY the
car dataset provided below.

Rules:
1. Recommend only models present in the dataset.
2. Do not invent prices, variants, mileage, safety
   ratings, or specifications.
3. All prices in the dataset are in Indian Rupees.
   Convert prices to ₹ lakhs by dividing by 100000.
   Display every car price range in ₹ lakhs,
   rounded to 2 decimal places.
   Example: ₹749000 to ₹1549000 must be shown as
   ₹7.49 - 15.49 lakh.
   Do not display full rupee amounts in recommendations.
4. Price_Min_INR and Price_Max_INR represent
   model-level price ranges, not confirmed prices
   for every variant.
5. If a model's price range overlaps a budget,
   explain that a suitable variant may exist,
   but it is not guaranteed.
6. The fuel and transmission values may represent
   only one variant, not every available variant.
7. If information is missing, say it is unavailable.
8. Explain recommendations in simple language.
9. Clearly state that the dataset is academic and
   specifications have not been independently verified.

The customer's selected maximum budget is
₹{ai_budget_lakh} lakh.

Recommend only cars whose listed price ranges
overlap this budget.

If the written question mentions a different budget,
ask the customer to adjust the budget slider.

CAR DATA:
{car_data}

CUSTOMER QUESTION:
{question}
"""

                with st.spinner('Gemini is preparing your answer...'):
                    response = client.models.generate_content(
                        model='gemini-3.5-flash-lite',
                        contents=prompt
                    )

                if response.text:
                    st.subheader('AI Recommendation')
                    st.write(response.text)
                else:
                    st.warning(
                        'Gemini returned no text. '
                        'Please try another question.'
                    )

            except Exception as e:
                st.error(
                    f'Gemini request failed: {type(e).__name__}'
                )
                st.code(str(e))

