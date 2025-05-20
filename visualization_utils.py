import pandas as pd
import altair as alt
import numpy as np
from logger_config import get_logger
from typing import Dict, List, Optional, Tuple
from functools import wraps

# Initialize logger
logger = get_logger('visualization_utils')

def handle_chart_errors(func):
    """Decorator to handle errors in chart creation functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"Creating {func.__name__} chart")
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating {func.__name__} chart: {str(e)}", exc_info=True)
            raise
    return wrapper

def get_default_chart_properties(title: str, width: int = 600, height: int = 400) -> dict:
    """Get default chart properties."""
    return {
        'title': title,
        'width': width,
        'height': height
    }

def get_amount_tooltip() -> List[alt.Tooltip]:
    """Get standard tooltip for amount fields."""
    return [alt.Tooltip('amount:Q', title='Total Amount', format='$,.2f')]

@handle_chart_errors
def create_payment_distribution_chart(df: pd.DataFrame) -> alt.Chart:
    """Create a chart showing the distribution of payments."""
    agency_totals = df.groupby('agency_name')['amount'].sum().reset_index()
    
    chart = alt.Chart(agency_totals).mark_bar().encode(
        x=alt.X('agency_name:N', title='Agency', sort='-y'),
        y=alt.Y('amount:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
        tooltip=[
            alt.Tooltip('agency_name:N', title='Agency'),
            *get_amount_tooltip()
        ]
    ).properties(**get_default_chart_properties('Payment Distribution by Agency'))
    
    return chart

@handle_chart_errors
def create_trend_analysis_chart(df: pd.DataFrame) -> alt.Chart:
    """Create a chart showing payment trends over time."""
    monthly_totals = df.groupby(['fiscal_year', 'fiscal_month'])['amount'].sum().reset_index()
    
    chart = alt.Chart(monthly_totals).mark_line().encode(
        x=alt.X('fiscal_month:N', title='Month'),
        y=alt.Y('amount:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
        color='fiscal_year:N',
        tooltip=[
            alt.Tooltip('fiscal_year:N', title='Fiscal Year'),
            alt.Tooltip('fiscal_month:N', title='Month'),
            *get_amount_tooltip()
        ]
    ).properties(**get_default_chart_properties('Payment Trends Over Time'))
    
    return chart

@handle_chart_errors
def create_vendor_analysis_chart(df: pd.DataFrame) -> alt.Chart:
    """Create a chart showing top vendors by payment amount."""
    vendor_totals = df.groupby('vendor_name')['amount'].sum().reset_index()
    vendor_totals = vendor_totals.nlargest(10, 'amount')
    
    chart = alt.Chart(vendor_totals).mark_bar().encode(
        x=alt.X('amount:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
        y=alt.Y('vendor_name:N', title='Vendor', sort='-x'),
        tooltip=[
            alt.Tooltip('vendor_name:N', title='Vendor'),
            *get_amount_tooltip()
        ]
    ).properties(**get_default_chart_properties('Top 10 Vendors by Payment Amount'))
    
    return chart

@handle_chart_errors
def create_category_analysis_chart(df: pd.DataFrame) -> alt.Chart:
    """Create a chart showing payment distribution by category."""
    category_totals = df.groupby('category')['amount'].sum().reset_index()
    
    chart = alt.Chart(category_totals).mark_arc().encode(
        theta=alt.Theta(field="amount", type="quantitative"),
        color=alt.Color(field="category", type="nominal"),
        tooltip=[
            alt.Tooltip('category:N', title='Category'),
            *get_amount_tooltip()
        ]
    ).properties(**get_default_chart_properties('Payment Distribution by Category', width=400, height=400))
    
    return chart

@handle_chart_errors
def generate_all_visualizations(df: pd.DataFrame) -> Dict[str, alt.Chart]:
    """Generate all visualizations for the given data."""
    # Convert amount column to numeric, handling any non-numeric values
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # Log data types after conversion
    logger.info(f"Data types after conversion: {df.dtypes}")
    
    visualizations = {
        'payment_distribution': create_payment_distribution_chart(df),
        'trend_analysis': create_trend_analysis_chart(df),
        'vendor_analysis': create_vendor_analysis_chart(df),
        'category_analysis': create_category_analysis_chart(df)
    }
    
    return visualizations
