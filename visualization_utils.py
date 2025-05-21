import pandas as pd
import altair as alt
import numpy as np
from logger_config import get_logger
from typing import Dict, List, Optional, Tuple

# Initialize logger
logger = get_logger('visualization_utils')

def create_payment_distribution_chart(df: pd.DataFrame, table_choice: str) -> alt.Chart:
    """
    Create a chart showing the distribution of payments.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        alt.Chart: Altair chart object
    """
    try:
        logger.info("Creating payment distribution chart")
        
        # Determine the amount column based on table choice
        amount_column = 'amount_pay' if table_choice == "Payment Information" else 'curvalue'
        agency_column = 'agency_title' if table_choice == "Payment Information" else 'agency'
        
        # Group by agency and sum the amounts
        agency_totals = df.groupby(agency_column)[amount_column].sum().reset_index()
        
        # Create the chart
        chart = alt.Chart(agency_totals).mark_bar().encode(
            x=alt.X(f'{agency_column}:N', title='Agency', sort='-y'),
            y=alt.Y(f'{amount_column}:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
            tooltip=[
                alt.Tooltip(f'{agency_column}:N', title='Agency'),
                alt.Tooltip(f'{amount_column}:Q', title='Total Amount', format='$,.2f')
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

def create_trend_analysis_chart(df: pd.DataFrame, table_choice: str) -> alt.Chart:
    """
    Create a chart showing payment trends over time.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        alt.Chart: Altair chart object
    """
    try:
        logger.info("Creating trend analysis chart")
        
        # Determine the amount column based on table choice
        amount_column = 'amount_pay' if table_choice == "Payment Information" else 'curvalue'
        
        # Determine fiscal year and month columns based on table choice
        fiscal_year_col = 'fiscal year' if table_choice == "Payment Information" else 'fy'
        fiscal_month_col = 'fiscal_month' if table_choice == "Payment Information" else 'fm'
        
        # Group by fiscal year and month, sum the amounts
        monthly_totals = df.groupby([fiscal_year_col, fiscal_month_col])[amount_column].sum().reset_index()
        
        # Create the chart
        chart = alt.Chart(monthly_totals).mark_line().encode(
            x=alt.X(f'{fiscal_month_col}:N', title='Month'),
            y=alt.Y(f'{amount_column}:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
            color=f'{fiscal_year_col}:N',
            tooltip=[
                alt.Tooltip(f'{fiscal_year_col}:N', title='Fiscal Year'),
                alt.Tooltip(f'{fiscal_month_col}:N', title='Month'),
                alt.Tooltip(f'{amount_column}:Q', title='Total Amount', format='$,.2f')
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

def create_vendor_analysis_chart(df: pd.DataFrame, table_choice: str) -> alt.Chart:
    """
    Create a chart showing top vendors by payment amount.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        alt.Chart: Altair chart object
    """
    try:
        logger.info("Creating vendor analysis chart")
        
        # Determine the amount column based on table choice
        amount_column = 'amount_pay' if table_choice == "Payment Information" else 'curvalue'
        vendor_column = 'vendor_name' if table_choice == "Payment Information" else 'vendor'
        
        # Group by vendor and sum the amounts, get top 10
        vendor_totals = df.groupby(vendor_column)[amount_column].sum().reset_index()
        vendor_totals = vendor_totals.nlargest(10, amount_column)
        
        # Create the chart
        chart = alt.Chart(vendor_totals).mark_bar().encode(
            x=alt.X(f'{amount_column}:Q', title='Total Amount ($)', axis=alt.Axis(format='$,.0f')),
            y=alt.Y(f'{vendor_column}:N', title='Vendor', sort='-x'),
            tooltip=[
                alt.Tooltip(f'{vendor_column}:N', title='Vendor'),
                alt.Tooltip(f'{amount_column}:Q', title='Total Amount', format='$,.2f')
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

def create_category_analysis_chart(df: pd.DataFrame, table_choice: str) -> Optional[alt.Chart]:
    """
    Create a chart showing payment distribution by category.
    Only available for Contract Information.
    
    Args:
        df (pd.DataFrame): DataFrame containing payment data
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        Optional[alt.Chart]: Altair chart object or None if not applicable
    """
    try:
        logger.info("Creating category analysis chart")
        
        # Only create category chart for Contract Information
        if table_choice != "Contract Information":
            logger.info("Category analysis not available for Payment Information")
            return None
            
        # Determine the amount column based on table choice
        amount_column = 'curvalue'  # Only used for Contract Information
        
        # Group by category and sum the amounts
        category_totals = df.groupby('category')[amount_column].sum().reset_index()
        
        # Create the chart
        chart = alt.Chart(category_totals).mark_arc().encode(
            theta=alt.Theta(field=amount_column, type="quantitative"),
            color=alt.Color(field="category", type="nominal"),
            tooltip=[
                alt.Tooltip('category:N', title='Category'),
                alt.Tooltip(f'{amount_column}:Q', title='Total Amount', format='$,.2f')
            ]
        ).properties(
            title='Contract Distribution by Category',
            width=400,
            height=400
        )
        
        return chart
        
    except Exception as e:
        logger.error(f"Error creating category analysis chart: {str(e)}", exc_info=True)
        raise

def generate_all_visualizations(df: pd.DataFrame, table_choice: str) -> Dict[str, alt.Chart]:
    """
    Generate all visualizations for the given data.
    
    Args:
        df (pd.DataFrame): DataFrame containing the data
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        Dict[str, alt.Chart]: Dictionary containing all visualization charts
    """
    try:
        logger.info("Generating all visualizations")
        
        visualizations = {
            'payment_distribution': create_payment_distribution_chart(df, table_choice),
            'trend_analysis': create_trend_analysis_chart(df, table_choice),
            'vendor_analysis': create_vendor_analysis_chart(df, table_choice)
        }
        
        # Only add category analysis for Contract Information
        category_chart = create_category_analysis_chart(df, table_choice)
        if category_chart is not None:
            visualizations['category_analysis'] = category_chart
        
        return visualizations
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}", exc_info=True)
        raise 