from sqlalchemy import text
from logger_config import get_logger
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
import time

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
    logger.info(f"Building base query for table choice: '{table_choice}'")
    
    # Determine which table to query based on selection
    if table_choice == "Payment Information":
        query = text("""
            SELECT p.*
            FROM paymentinformation p
            WHERE 1=1
            LIMIT 1000
        """)
        logger.info("Selected paymentinformation table for query")
    else:  # Contract Information
        query = text("""
            SELECT c.*
            FROM contractinfo c
            WHERE 1=1
            ORDER BY c.fiscal_year DESC, c.agency_title
            LIMIT 1000
        """)
        logger.info("Selected contractinfo table for query")
    
    logger.info(f"Generated query: {str(query)}")
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
            
        if filters.get('category'):
            query = text(str(query) + " AND c.category = :category")
            params['category'] = filters['category']
            logger.info(f"Added category filter: {filters['category']}")
            
        if filters.get('procurement_method'):
            query = text(str(query) + " AND c.procurement_method = :procurement_method")
            params['procurement_method'] = filters['procurement_method']
            logger.info(f"Added procurement method filter: {filters['procurement_method']}")
            
        if filters.get('status'):
            query = text(str(query) + " AND c.status = :status")
            params['status'] = filters['status']
            logger.info(f"Added status filter: {filters['status']}")
            
        if filters.get('subject'):
            query = text(str(query) + " AND c.subject = :subject")
            params['subject'] = filters['subject']
            logger.info(f"Added subject filter: {filters['subject']}")
    
    logger.info(f"Final query: {str(query)}")
    logger.info(f"Query parameters: {params}")
    return query, params

def check_table_accessibility(engine) -> Dict[str, bool]:
    """
    Check if both paymentinformation and contractinfo tables are accessible.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        Dict[str, bool]: Dictionary indicating which tables are accessible
    """
    accessibility = {
        'paymentinformation': False,
        'contractinfo': False
    }
    
    try:
        with engine.connect() as connection:
            # Check paymentinformation table
            check_payment = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'paymentinformation'
                );
            """)
            payment_exists = connection.execute(check_payment).scalar()
            logger.info(f"Paymentinformation table exists: {payment_exists}")
            
            if payment_exists:
                # Try to execute a simple query on paymentinformation
                test_payment = text("SELECT COUNT(*) FROM paymentinformation LIMIT 1")
                try:
                    payment_count = connection.execute(test_payment).scalar()
                    logger.info(f"Payment Information table is accessible. Sample count: {payment_count}")
                    accessibility['paymentinformation'] = True
                except Exception as e:
                    logger.error(f"Payment Information table exists but is not accessible: {str(e)}")
            else:
                logger.warning("Payment Information table does not exist")
            
            # Check contractinfo table
            check_contract = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'contractinfo'
                );
            """)
            contract_exists = connection.execute(check_contract).scalar()
            logger.info(f"Contractinfo table exists: {contract_exists}")
            
            if contract_exists:
                # Try to execute a simple query on contractinfo
                test_contract = text("SELECT COUNT(*) FROM contractinfo LIMIT 1")
                try:
                    contract_count = connection.execute(test_contract).scalar()
                    logger.info(f"Contract Information table is accessible. Sample count: {contract_count}")
                    accessibility['contractinfo'] = True
                except Exception as e:
                    logger.error(f"Contract Information table exists but is not accessible: {str(e)}")
            else:
                logger.warning("Contract Information table does not exist")
            
            # Log overall status
            if accessibility['paymentinformation'] and accessibility['contractinfo']:
                logger.info("Both tables are accessible")
            elif accessibility['paymentinformation']:
                logger.info("Only Payment Information table is accessible")
            elif accessibility['contractinfo']:
                logger.info("Only Contract Information table is accessible")
            else:
                logger.error("Neither table is accessible")
            
            return accessibility
            
    except Exception as e:
        logger.error(f"Error checking table accessibility: {str(e)}")
        return accessibility

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
    start_time = time.time()
    logger.info("Executing query with chunking")
    logger.info(f"Query: {str(query)}")
    logger.info(f"Parameters: {params}")
    
    # First check if tables are accessible
    table_access = check_table_accessibility(engine)
    if not any(table_access.values()):
        logger.error("No tables are accessible")
        return []
    
    all_data = []
    chunk_size = 100
    offset = 0
    
    try:
        with engine.connect() as connection:
            # First, let's check if the table exists
            table_name = "paymentinformation" if "paymentinformation" in str(query).lower() else "contractinfo"
            logger.info(f"Checking for table: {table_name}")
            
            if not table_access.get(table_name, False):
                logger.error(f"Table {table_name} is not accessible")
                return []
            
            # Let's also check the columns
            columns_query = text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = [(row[0], row[1]) for row in connection.execute(columns_query)]
            logger.info(f"Available columns in {table_name}: {columns}")
            
            # Now execute the main query with chunking
            while True:
                # Remove any existing LIMIT clause and add our chunking LIMIT
                base_query = str(query)
                if "LIMIT" in base_query:
                    base_query = base_query.split("LIMIT")[0].strip()
                
                chunk_query = text(f"{base_query} LIMIT {chunk_size} OFFSET {offset}")
                logger.info(f"Executing chunk query: {str(chunk_query)}")
                logger.info(f"Chunk parameters: {params}")
                
                try:
                    chunk_start_time = time.time()
                    chunk_data = connection.execute(chunk_query, params).fetchall()
                    chunk_time = time.time() - chunk_start_time
                    logger.info(f"Chunk query took {chunk_time:.2f} seconds")
                    
                    if not chunk_data:
                        break
                    
                    # Convert to list of dicts
                    chunk_dicts = [dict(row) for row in chunk_data]
                    all_data.extend(chunk_dicts)
                    logger.info(f"Retrieved {len(chunk_dicts)} records in this chunk")
                    
                    offset += chunk_size
                except Exception as e:
                    logger.error(f"Error executing chunk query: {str(e)}")
                    break
            
            total_time = time.time() - start_time
            logger.info(f"Total query execution took {total_time:.2f} seconds")
            logger.info(f"Query execution returned {len(all_data)} records")
            return all_data
            
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}", exc_info=True)
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