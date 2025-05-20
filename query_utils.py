from sqlalchemy import text
from logger_config import get_logger
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from db_config import check_table_accessibility, execute_safe_query

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
    
    # Determine table alias and name
    table_info = {
        "Payment Information": ("p", "paymentinformation"),
        "Contract Information": ("c", "contractinfo")
    }
    
    alias, table_name = table_info.get(table_choice, ("p", "paymentinformation"))
    
    query = text(f"""
        SELECT {alias}.*
        FROM {table_name} {alias}
        WHERE 1=1
    """)
    
    return query, {}

def add_filters_to_query(query: text, filters: Dict, params: Dict, table_choice: str) -> Tuple[text, Dict]:
    """
    Add filters to the query based on the selected table.
    """
    logger.info(f"Adding filters for {table_choice}")
    logger.info(f"Filters received: {filters}")
    
    # Determine table alias
    alias = "p" if table_choice == "Payment Information" else "c"
    
    # Common filters for both tables
    common_filters = {
        'fiscal_year': f"{alias}.fiscal_year = :fiscal_year",
        'agency': f"LOWER({alias}.agency_title) = LOWER(:agency)",
        'appropriation_object': f"{alias}.object_title = :appropriation_object"
    }
    
    # Add filters to query
    for filter_name, filter_condition in common_filters.items():
        if filters.get(filter_name):
            query = text(str(query) + f" AND {filter_condition}")
            params[filter_name] = filters[filter_name]
            logger.info(f"Added {filter_name} filter: {filters[filter_name]}")
    
    logger.info(f"Final query: {str(query)}")
    logger.info(f"Query parameters: {params}")
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
    logger.info(f"Query: {str(query)}")
    logger.info(f"Parameters: {params}")
    
    # Check table accessibility
    table_access = check_table_accessibility(engine)
    if not any(table_access.values()):
        logger.error("No tables are accessible")
        return []
    
    all_data = []
    chunk_size = 100
    offset = 0
    
    try:
        with engine.connect() as connection:
            # Determine which table we're querying
            table_name = "paymentinformation" if "paymentinformation" in str(query).lower() else "contractinfo"
            
            if not table_access.get(table_name, False):
                logger.error(f"Table {table_name} is not accessible")
                return []
            
            # Execute query with chunking
            while True:
                chunk_query = text(str(query) + f" LIMIT {chunk_size} OFFSET {offset}")
                chunk_data = execute_safe_query(connection, chunk_query, params)
                
                if not chunk_data:
                    break
                    
                all_data.extend(chunk_data)
                offset += chunk_size
                
                if len(chunk_data) < chunk_size:
                    break
            
            return all_data
            
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return []

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
    logger.info(f"Filters received: {filters}")
    
    try:
        # Build and execute query
        query, params = build_base_query(table_choice)
        query, params = add_filters_to_query(query, filters, params, table_choice)
        results = execute_query(query, params, engine)
        
        # Convert to DataFrame
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting filtered data: {str(e)}")
        return pd.DataFrame() 