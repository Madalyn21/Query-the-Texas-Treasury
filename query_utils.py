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

def add_filters_to_query(query: text, filters: Dict, params: Dict, table_choice: str) -> Tuple[text, Dict]:
    """
    Add filters to the query based on the selected table.
    """
    logger.info(f"Adding filters for {table_choice}")
    logger.info(f"Filters received: {filters}")
    
    if table_choice == "Payment Information":
        if filters.get('fiscal_year'):
            query = text(str(query) + " AND p.fiscal_year = :fiscal_year")
            params['fiscal_year'] = filters['fiscal_year']
            logger.info(f"Added fiscal year filter: {filters['fiscal_year']}")
            
        if filters.get('agency'):
            # Make agency filter case-insensitive
            query = text(str(query) + " AND LOWER(p.agency_title) = LOWER(:agency)")
            params['agency'] = filters['agency']
            logger.info(f"Added agency filter (case-insensitive): {filters['agency']}")
            
        if filters.get('appropriation_object'):
            query = text(str(query) + " AND p.object_title = :appropriation_object")
            params['appropriation_object'] = filters['appropriation_object']
            logger.info(f"Added appropriation object filter: {filters['appropriation_object']}")
            
    elif table_choice == "Contract Information":
        if filters.get('fiscal_year'):
            query = text(str(query) + " AND c.fiscal_year = :fiscal_year")
            params['fiscal_year'] = filters['fiscal_year']
            logger.info(f"Added fiscal year filter: {filters['fiscal_year']}")
            
        if filters.get('agency'):
            # Make agency filter case-insensitive
            query = text(str(query) + " AND LOWER(c.agency_title) = LOWER(:agency)")
            params['agency'] = filters['agency']
            logger.info(f"Added agency filter (case-insensitive): {filters['agency']}")
            
        if filters.get('appropriation_object'):
            query = text(str(query) + " AND c.object_title = :appropriation_object")
            params['appropriation_object'] = filters['appropriation_object']
            logger.info(f"Added appropriation object filter: {filters['appropriation_object']}")
    
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
    
    all_data = []
    chunk_size = 100
    offset = 0
    
    try:
        with engine.connect() as connection:
            # First, let's check if the table exists
            table_name = "paymentinformation" if "paymentinformation" in str(query).lower() else "contractinfo"
            check_table = text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                );
            """)
            table_exists = connection.execute(check_table).scalar()
            logger.info(f"Table {table_name} exists: {table_exists}")
            
            if not table_exists:
                logger.error(f"Table {table_name} does not exist in the database")
                return []
            
            # Let's also check the columns
            columns_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}';
            """)
            columns = [row[0] for row in connection.execute(columns_query)]
            logger.info(f"Available columns in {table_name}: {columns}")
            
            # Let's check if we have any data for the agency
            if params.get('agency'):
                # First check exact match
                agency_check = text(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE agency_title = :agency
                """)
                agency_count = connection.execute(agency_check, {'agency': params['agency']}).scalar()
                logger.info(f"Found {agency_count} records for exact agency match: {params['agency']}")
                
                # Then check case-insensitive match
                agency_check_ci = text(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE LOWER(agency_title) = LOWER(:agency)
                """)
                agency_count_ci = connection.execute(agency_check_ci, {'agency': params['agency']}).scalar()
                logger.info(f"Found {agency_count_ci} records for case-insensitive agency match: {params['agency']}")
                
                # If no matches, let's see what agencies are similar
                if agency_count_ci == 0:
                    similar_agencies = text(f"""
                        SELECT DISTINCT agency_title 
                        FROM {table_name} 
                        WHERE agency_title ILIKE :agency_pattern
                        LIMIT 5
                    """)
                    similar = connection.execute(similar_agencies, {'agency_pattern': f'%{params["agency"]}%'}).fetchall()
                    logger.info(f"Similar agencies found: {[row[0] for row in similar]}")
            
            # Check if we have any data for the fiscal year
            if params.get('fiscal_year'):
                year_check = text(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE fiscal_year = :fiscal_year
                """)
                year_count = connection.execute(year_check, {'fiscal_year': params['fiscal_year']}).scalar()
                logger.info(f"Found {year_count} records for fiscal year: {params['fiscal_year']}")
            
            while True:
                # Add LIMIT and OFFSET to the query
                chunk_query = text(str(query) + f" LIMIT {chunk_size} OFFSET {offset}")
                logger.info(f"Executing chunk query: {str(chunk_query)}")
                
                result = connection.execute(chunk_query, params)
                chunk_data = [dict(row) for row in result]
                
                logger.info(f"Chunk returned {len(chunk_data)} records")
                
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
    logger.info(f"Filters received: {filters}")
    
    try:
        # Build the base query
        query, params = build_base_query(table_choice)
        logger.info(f"Base query built: {str(query)}")
        
        # Add filters to the query
        query, params = add_filters_to_query(query, filters, params, table_choice)
        logger.info(f"Query after adding filters: {str(query)}")
        logger.info(f"Parameters after adding filters: {params}")
        
        # Execute the query
        data = execute_query(query, params, engine)
        logger.info(f"Query execution returned {len(data)} records")
        
        # Convert to DataFrame
        if data:
            df = pd.DataFrame(data)
            # Sanitize column names
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            logger.info(f"DataFrame created with shape: {df.shape}")
            logger.info(f"DataFrame columns: {df.columns.tolist()}")
            return df
        else:
            logger.warning("No data returned from query")
            return pd.DataFrame()  # Return empty DataFrame if no data
            
    except Exception as e:
        logger.error(f"Error getting filtered data: {str(e)}", exc_info=True)
        return pd.DataFrame()  # Return empty DataFrame on error 