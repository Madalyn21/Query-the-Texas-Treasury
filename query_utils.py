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
    
    # Build a more detailed base query
    query = text(f"""
        SELECT {alias}.*
        FROM {table_name} {alias}
        WHERE 1=1
    """)
    
    logger.info(f"Base query built: {str(query)}")
    return query, {}

def add_filters_to_query(query: text, filters: Dict, params: Dict, table_choice: str) -> Tuple[text, Dict]:
    """
    Add filters to the query based on the selected table.
    """
    logger.info(f"Adding filters for {table_choice}")
    logger.info(f"Filters received: {filters}")
    
    # Determine table alias
    alias = "p" if table_choice == "Payment Information" else "c"
    
    # Add fiscal year range filter
    if filters.get('fiscal_year_start') and filters.get('fiscal_year_end'):
        query = text(str(query) + f" AND {alias}.fiscal_year BETWEEN :fiscal_year_start AND :fiscal_year_end")
        params['fiscal_year_start'] = int(filters['fiscal_year_start'])
        params['fiscal_year_end'] = int(filters['fiscal_year_end'])
        logger.info(f"Added fiscal year range filter: {filters['fiscal_year_start']} to {filters['fiscal_year_end']}")
    
    # Add fiscal month range filter
    if filters.get('fiscal_month_start') and filters.get('fiscal_month_end'):
        query = text(str(query) + f" AND {alias}.fiscal_month BETWEEN :fiscal_month_start AND :fiscal_month_end")
        params['fiscal_month_start'] = int(filters['fiscal_month_start'])
        params['fiscal_month_end'] = int(filters['fiscal_month_end'])
        logger.info(f"Added fiscal month range filter: {filters['fiscal_month_start']} to {filters['fiscal_month_end']}")
    
    # Add vendor filter
    if filters.get('vendor') and len(filters['vendor']) > 0:
        query = text(str(query) + f" AND LOWER({alias}.vendor_name) = LOWER(:vendor)")
        params['vendor'] = str(filters['vendor'][0]).strip()
        logger.info(f"Added vendor filter: {filters['vendor'][0]}")
    
    # Add other filters based on table choice
    if table_choice == "Payment Information":
        if filters.get('agency'):
            # Agency number is numeric, so we'll cast the input to integer
            try:
                agency_number = int(filters['agency'])
                query = text(str(query) + f" AND {alias}.agency_number = :agency")
                params['agency'] = agency_number
                logger.info(f"Added agency filter: {agency_number}")
            except ValueError:
                # If agency is not a number, try to match by agency title/name
                column_name = "agency_title" if table_choice == "Payment Information" else "agency"
                query = text(str(query) + f" AND LOWER({alias}.{column_name}) = LOWER(:agency)")
                params['agency'] = str(filters['agency']).strip()
                logger.info(f"Added agency filter using {column_name}: {filters['agency']}")
        
        if filters.get('appropriation_title'):
            # Appropriation number is numeric
            try:
                appropriation_number = int(filters['appropriation_title'])
                query = text(str(query) + f" AND {alias}.appropriation_number = :appropriation_title")
                params['appropriation_title'] = appropriation_number
                logger.info(f"Added appropriation number filter: {appropriation_number}")
            except ValueError:
                # If not a number, try to match by title
                query = text(str(query) + f" AND LOWER({alias}.appropriation_title) = LOWER(:appropriation_title)")
                params['appropriation_title'] = str(filters['appropriation_title']).strip()
                logger.info(f"Added appropriation title filter: {filters['appropriation_title']}")
        
        if filters.get('payment_source'):
            # Fund number is numeric
            try:
                fund_number = int(filters['payment_source'])
                query = text(str(query) + f" AND {alias}.fund_number = :payment_source")
                params['payment_source'] = fund_number
                logger.info(f"Added fund number filter: {fund_number}")
            except ValueError:
                # If not a number, try to match by name
                query = text(str(query) + f" AND LOWER({alias}.fund_name) = LOWER(:payment_source)")
                params['payment_source'] = str(filters['payment_source']).strip()
                logger.info(f"Added fund name filter: {filters['payment_source']}")
        
        if filters.get('appropriation_object'):
            # Object number is numeric
            try:
                object_number = int(filters['appropriation_object'])
                query = text(str(query) + f" AND {alias}.object_number = :appropriation_object")
                params['appropriation_object'] = object_number
                logger.info(f"Added object number filter: {object_number}")
            except ValueError:
                # If not a number, try to match by title
                query = text(str(query) + f" AND LOWER({alias}.object_title) = LOWER(:appropriation_object)")
                params['appropriation_object'] = str(filters['appropriation_object']).strip()
                logger.info(f"Added object title filter: {filters['appropriation_object']}")
    else:
        if filters.get('agency'):
            # Agency number is numeric
            try:
                agency_number = int(filters['agency'])
                query = text(str(query) + f" AND {alias}.agency_number = :agency")
                params['agency'] = agency_number
                logger.info(f"Added agency filter: {agency_number}")
            except ValueError:
                # If agency is not a number, try to match by agency name
                query = text(str(query) + f" AND LOWER({alias}.agency_name) = LOWER(:agency)")
                params['agency'] = str(filters['agency']).strip()
                logger.info(f"Added agency name filter: {filters['agency']}")
        
        if filters.get('category'):
            query = text(str(query) + f" AND LOWER({alias}.category) = LOWER(:category)")
            params['category'] = str(filters['category']).strip()
            logger.info(f"Added category filter: {filters['category']}")
        
        if filters.get('procurement_method'):
            query = text(str(query) + f" AND LOWER({alias}.procurement_method) = LOWER(:procurement_method)")
            params['procurement_method'] = str(filters['procurement_method']).strip()
            logger.info(f"Added procurement method filter: {filters['procurement_method']}")
        
        if filters.get('status'):
            query = text(str(query) + f" AND LOWER({alias}.status) = LOWER(:status)")
            params['status'] = str(filters['status']).strip()
            logger.info(f"Added status filter: {filters['status']}")
        
        if filters.get('subject'):
            query = text(str(query) + f" AND LOWER({alias}.subject) = LOWER(:subject)")
            params['subject'] = str(filters['subject']).strip()
            logger.info(f"Added subject filter: {filters['subject']}")
    
    logger.info(f"Final query: {str(query)}")
    logger.info(f"Query parameters: {params}")
    return query, params

def execute_query(query: text, params: Dict, engine) -> List[Dict]:
    """
    Execute the query with chunking to handle large result sets.
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
            
            # First, let's check if there's any data in the table at all
            count_query = text(f"SELECT COUNT(*) as count FROM {table_name}")
            count_result = execute_safe_query(connection, count_query, {})
            total_count = count_result[0]['count'] if count_result else 0
            logger.info(f"Total records in {table_name}: {total_count}")
            
            # Execute query with chunking
            while True:
                chunk_query = text(str(query) + f" LIMIT {chunk_size} OFFSET {offset}")
                logger.info(f"Executing chunk query: {str(chunk_query)}")
                # Convert params to a list of tuples for proper parameter binding
                params_list = [(k, v) for k, v in params.items()]
                chunk_data = execute_safe_query(connection, chunk_query, dict(params_list))
                
                if not chunk_data:
                    logger.info(f"No more data found at offset {offset}")
                    break
                    
                logger.info(f"Found {len(chunk_data)} records in chunk")
                all_data.extend(chunk_data)
                offset += chunk_size
                
                if len(chunk_data) < chunk_size:
                    break
            
            logger.info(f"Total records found after filtering: {len(all_data)}")
            return all_data
            
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        return []

def get_filtered_data(filters: Dict, table_choice: str, engine) -> pd.DataFrame:
    """
    Main function to get filtered data from the database.
    """
    logger.info(f"Getting filtered data for {table_choice}")
    logger.info(f"Filters received: {filters}")
    
    try:
        # Build and execute query
        query, params = build_base_query(table_choice)
        logger.info(f"Base query: {str(query)}")
        
        query, params = add_filters_to_query(query, filters, params, table_choice)
        logger.info(f"Query after adding filters: {str(query)}")
        logger.info(f"Parameters after adding filters: {params}")
        
        results = execute_query(query, params, engine)
        
        # Convert to DataFrame
        if results:
            df = pd.DataFrame(results)
            logger.info(f"DataFrame created with {len(df)} rows and columns: {df.columns.tolist()}")
            return df
        logger.info("No results found, returning empty DataFrame")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting filtered data: {str(e)}")
        return pd.DataFrame() 