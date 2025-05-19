import pandas as pd
import altair as alt
import numpy as np
from logger_config import get_logger
from typing import Dict, List, Optional, Tuple

# Initialize logger
logger = get_logger('visualization_utils')

def create_payment_distribution_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Create a chart showing the distribution of payments.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        
    Returns:
        alt.Chart: Altair chart object
    """
    try:
        logger.info("Creating payment distribution chart")
        
        # Group by agency and sum the amounts
        agency_totals = df.groupby('agency_name')['amount'].sum().reset_index()
        
        # Create the chart
        chart = alt.Chart(agency_totals).mark_bar().encode(
            x=alt.X('agency_name:N', title='Agency', sort='-y'),
            y=alt.Y('amount:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
            tooltip=[
                alt.Tooltip('agency_name:N', title='Agency'),
                alt.Tooltip('amount:Q', title='Total Amount', format='$,.2f')
            ]
        ).properties(
            title='Payment Distribution by Agency',
            width=600,
            height=400
        )
        
        return chart
        
    except Exception as e:
        logger.error(f"Error creating payment distribution chart: {str(e)}", exc_info=True)
        raise

def create_trend_analysis_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Create a chart showing payment trends over time.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        
    Returns:
        alt.Chart: Altair chart object
    """
    try:
        logger.info("Creating trend analysis chart")
        
        # Group by fiscal year and month, sum the amounts
        monthly_totals = df.groupby(['fiscal_year', 'fiscal_month'])['amount'].sum().reset_index()
        
        # Create the chart
        chart = alt.Chart(monthly_totals).mark_line().encode(
            x=alt.X('fiscal_month:N', title='Month'),
            y=alt.Y('amount:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
            color='fiscal_year:N',
            tooltip=[
                alt.Tooltip('fiscal_year:N', title='Fiscal Year'),
                alt.Tooltip('fiscal_month:N', title='Month'),
                alt.Tooltip('amount:Q', title='Total Amount', format='$,.2f')
            ]
        ).properties(
            title='Payment Trends Over Time',
            width=600,
            height=400
        )
        
        return chart
        
    except Exception as e:
        logger.error(f"Error creating trend analysis chart: {str(e)}", exc_info=True)
        raise

def create_vendor_analysis_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Create a chart showing top vendors by payment amount.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        
    Returns:
        alt.Chart: Altair chart object
    """
    try:
        logger.info("Creating vendor analysis chart")
        
        # Group by vendor and sum the amounts, get top 10
        vendor_totals = df.groupby('vendor_name')['amount'].sum().reset_index()
        vendor_totals = vendor_totals.nlargest(10, 'amount')
        
        # Create the chart
        chart = alt.Chart(vendor_totals).mark_bar().encode(
            x=alt.X('amount:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
            y=alt.Y('vendor_name:N', title='Vendor', sort='-x'),
            tooltip=[
                alt.Tooltip('vendor_name:N', title='Vendor'),
                alt.Tooltip('amount:Q', title='Total Amount', format='$,.2f')
            ]
        ).properties(
            title='Top 10 Vendors by Payment Amount',
            width=600,
            height=400
        )
        
        return chart
        
    except Exception as e:
        logger.error(f"Error creating vendor analysis chart: {str(e)}", exc_info=True)
        raise

def create_category_analysis_chart(df: pd.DataFrame) -> alt.Chart:
    """
    Create a chart showing payment distribution by category.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        
    Returns:
        alt.Chart: Altair chart object
    """
    try:
        logger.info("Creating category analysis chart")
        
        # Group by category and sum the amounts
        category_totals = df.groupby('category')['amount'].sum().reset_index()
        
        # Create the chart
        chart = alt.Chart(category_totals).mark_arc().encode(
            theta=alt.Theta(field="amount", type="quantitative"),
            color=alt.Color(field="category", type="nominal"),
            tooltip=[
                alt.Tooltip('category:N', title='Category'),
                alt.Tooltip('amount:Q', title='Total Amount', format='$,.2f')
            ]
        ).properties(
            title='Payment Distribution by Category',
            width=400,
            height=400
        )
        
        return chart
        
    except Exception as e:
        logger.error(f"Error creating category analysis chart: {str(e)}", exc_info=True)
        raise

def generate_all_visualizations(df: pd.DataFrame) -> Dict[str, alt.Chart]:
    """
    Generate all visualizations for the given data.
    
    Args:
        df (pd.DataFrame): DataFrame containing the data
        
    Returns:
        Dict[str, alt.Chart]: Dictionary containing all visualization charts
    """
    try:
        logger.info("Generating all visualizations")
        
        visualizations = {
            'payment_distribution': create_payment_distribution_chart(df),
            'trend_analysis': create_trend_analysis_chart(df),
            'vendor_analysis': create_vendor_analysis_chart(df),
            'category_analysis': create_category_analysis_chart(df)
        }
        
        return visualizations
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}", exc_info=True)
        raise 