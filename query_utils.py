from sqlalchemy import text
from logger_config import get_logger
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple

# Initialize logger
logger = get_logger('query_utils')

def build_base_query(table_choice: str) -> Tuple[str, Dict]:
    """
    Build the base query based on the selected table.
    
    Args:
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        Tuple[str, Dict]: The base query and parameters dictionary
    """
    logger.info(f"Building base query for {table_choice}")
    
    # Determine which table to query based on selection
    if table_choice == "Payment Information":
        query = text("""
            SELECT p.*
            FROM paymentinformation p
            WHERE 1=1
        """)
    else:  # Contract Information
        query = text("""
            SELECT c.*
            FROM contractinfo c
            WHERE 1=1
        """)
    
    return query, {}

def add_filters_to_query(query: text, params: Dict, filters: Dict, table_choice: str) -> Tuple[text, Dict]:
    """
    Add filter conditions to the query based on the provided filters.
    
    Args:
        query (text): The base SQLAlchemy query
        params (Dict): The parameters dictionary
        filters (Dict): Dictionary containing filter values
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        Tuple[text, Dict]: The modified query and parameters dictionary
    """
    logger.info(f"Adding filters to query: {filters}")
    
    # Add common filters
    if table_choice == "Payment Information":
        if filters.get('fiscal_year_start'):
            query = text(str(query) + " AND p.fiscal_year >= :fiscal_year_start")
            params['fiscal_year_start'] = filters['fiscal_year_start']
        
        if filters.get('fiscal_year_end'):
            query = text(str(query) + " AND p.fiscal_year <= :fiscal_year_end")
            params['fiscal_year_end'] = filters['fiscal_year_end']
        
        if filters.get('fiscal_month_start'):
            query = text(str(query) + " AND p.fiscal_month >= :fiscal_month_start")
            params['fiscal_month_start'] = filters['fiscal_month_start']
        
        if filters.get('fiscal_month_end'):
            query = text(str(query) + " AND p.fiscal_month <= :fiscal_month_end")
            params['fiscal_month_end'] = filters['fiscal_month_end']
    else:  # Contract Information
        if filters.get('fiscal_year_start'):
            query = text(str(query) + " AND EXTRACT(YEAR FROM c.completion_date_date) >= :fiscal_year_start")
            params['fiscal_year_start'] = filters['fiscal_year_start']
        
        if filters.get('fiscal_year_end'):
            query = text(str(query) + " AND EXTRACT(YEAR FROM c.completion_date_date) <= :fiscal_year_end")
            params['fiscal_year_end'] = filters['fiscal_year_end']
        
        if filters.get('fiscal_month_start'):
            query = text(str(query) + " AND EXTRACT(MONTH FROM c.completion_date_date) >= :fiscal_month_start")
            params['fiscal_month_start'] = filters['fiscal_month_start']
        
        if filters.get('fiscal_month_end'):
            query = text(str(query) + " AND EXTRACT(MONTH FROM c.completion_date_date) <= :fiscal_month_end")
            params['fiscal_month_end'] = filters['fiscal_month_end']
    
    # Add table-specific filters
    if table_choice == "Payment Information":
        if filters.get('agency'):
            query = text(str(query) + " AND p.agency_title = :agency")
            params['agency'] = filters['agency']
        
        if filters.get('vendor'):
            query = text(str(query) + " AND p.vendor_name = :vendor")
            params['vendor'] = filters['vendor']
        
        if filters.get('appropriation_title'):
            query = text(str(query) + " AND p.appropriation_title = :appropriation_title")
            params['appropriation_title'] = filters['appropriation_title']
        
        if filters.get('payment_source'):
            query = text(str(query) + " AND p.fund_title = :payment_source")
            params['payment_source'] = filters['payment_source']
        
        if filters.get('appropriation_object'):
            query = text(str(query) + " AND p.object_title = :appropriation_object")
            params['appropriation_object'] = filters['appropriation_object']
    
    else:  # Contract Information
        if filters.get('agency'):
            query = text(str(query) + " AND c.agency_name = :agency")
            params['agency'] = filters['agency']
        
        if filters.get('category'):
            query = text(str(query) + " AND c.category = :category")
            params['category'] = filters['category']
        
        if filters.get('vendor'):
            query = text(str(query) + " AND c.vendor_name = :vendor")
            params['vendor'] = filters['vendor']
        
        if filters.get('procurement_method'):
            query = text(str(query) + " AND c.procurement_method = :procurement_method")
            params['procurement_method'] = filters['procurement_method']
        
        if filters.get('status'):
            query = text(str(query) + " AND c.status = :status")
            params['status'] = filters['status']
        
        if filters.get('subject'):
            query = text(str(query) + " AND c.subject = :subject")
            params['subject'] = filters['subject']
    
    return query, params

def execute_query(query: text, params: Dict, engine) -> List[Dict]:
    """
    Execute the query with chunking to handle large result sets.
    
    Args:
        query (text): The SQLAlchemy query
        params (Dict): The parameters dictionary
        engine: SQLAlchemy engine instance
        
    Returns:
        List[Dict]: List of dictionaries containing the query results
    """
    logger.info("Executing query with chunking")
    
    all_data = []
    chunk_size = 100
    offset = 0
    
    try:
        with engine.connect() as connection:
            while True:
                # Add LIMIT and OFFSET to the query
                chunk_query = text(str(query) + f" LIMIT {chunk_size} OFFSET {offset}")
                result = connection.execute(chunk_query, params)
                chunk_data = [dict(row) for row in result]
                
                if not chunk_data:
                    break
                    
                all_data.extend(chunk_data)
                offset += chunk_size
                
                # Log progress
                logger.info(f"Retrieved {len(all_data)} records so far")
                
                # If we got less than chunk_size records, we've reached the end
                if len(chunk_data) < chunk_size:
                    break
        
        logger.info(f"Total records retrieved: {len(all_data)}")
        return all_data
        
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}", exc_info=True)
        raise

def get_filtered_data(filters: Dict, table_choice: str, engine) -> pd.DataFrame:
    """
    Main function to get filtered data from the database.
    
    Args:
        filters (Dict): Dictionary containing filter values
        table_choice (str): Either "Payment Information" or "Contract Information"
        engine: SQLAlchemy engine instance
        
    Returns:
        pd.DataFrame: DataFrame containing the filtered data
    """
    logger.info(f"Getting filtered data for {table_choice}")
    
    try:
        # Build the base query
        query, params = build_base_query(table_choice)
        
        # Add filters to the query
        query, params = add_filters_to_query(query, params, filters, table_choice)
        
        # Execute the query
        data = execute_query(query, params, engine)
        
        # Convert to DataFrame
        if data:
            df = pd.DataFrame(data)
            # Sanitize column names
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            return df
        else:
            return pd.DataFrame()  # Return empty DataFrame if no data
            
    except Exception as e:
        logger.error(f"Error getting filtered data: {str(e)}", exc_info=True)
        return pd.DataFrame()  # Return empty DataFrame on error 