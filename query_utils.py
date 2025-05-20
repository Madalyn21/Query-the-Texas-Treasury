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
            
            # Let's check if we have any data for the agency
            if params.get('agency'):
                # First check exact match
                agency_check = text(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE agency_title = :agency
                """)
                try:
                    agency_count = connection.execute(agency_check, {'agency': params['agency']}).scalar()
                    logger.info(f"Found {agency_count} records for exact agency match: {params['agency']}")
                except Exception as e:
                    logger.error(f"Error checking exact agency match: {str(e)}")
                    # Try with different column names
                    for col in ['agency', 'agency_name', 'agency_title']:
                        try:
                            agency_check = text(f"""
                                SELECT COUNT(*) 
                                FROM {table_name} 
                                WHERE {col} = :agency
                            """)
                            agency_count = connection.execute(agency_check, {'agency': params['agency']}).scalar()
                            logger.info(f"Found {agency_count} records for agency match using column {col}: {params['agency']}")
                            if agency_count > 0:
                                # Update the query to use this column
                                query = text(str(query).replace('agency_title', col))
                                logger.info(f"Updated query to use column {col}")
                                break
                        except Exception as e:
                            logger.error(f"Error checking agency match with column {col}: {str(e)}")
                
                # Then check case-insensitive match
                agency_check_ci = text(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE LOWER(agency_title) = LOWER(:agency)
                """)
                try:
                    agency_count_ci = connection.execute(agency_check_ci, {'agency': params['agency']}).scalar()
                    logger.info(f"Found {agency_count_ci} records for case-insensitive agency match: {params['agency']}")
                except Exception as e:
                    logger.error(f"Error checking case-insensitive agency match: {str(e)}")
                
                # If no matches, let's see what agencies are similar
                if agency_count_ci == 0:
                    similar_agencies = text(f"""
                        SELECT DISTINCT agency_title 
                        FROM {table_name} 
                        WHERE agency_title ILIKE :agency_pattern
                        LIMIT 5
                    """)
                    try:
                        similar = connection.execute(similar_agencies, {'agency_pattern': f'%{params["agency"]}%'}).fetchall()
                        logger.info(f"Similar agencies found: {[row[0] for row in similar]}")
                    except Exception as e:
                        logger.error(f"Error finding similar agencies: {str(e)}")
            
            # Check if we have any data for the fiscal year
            if params.get('fiscal_year'):
                year_check = text(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE fiscal_year = :fiscal_year
                """)
                try:
                    year_count = connection.execute(year_check, {'fiscal_year': params['fiscal_year']}).scalar()
                    logger.info(f"Found {year_count} records for fiscal year: {params['fiscal_year']}")
                except Exception as e:
                    logger.error(f"Error checking fiscal year: {str(e)}")
                    # Try with different column names
                    for col in ['fiscal_year', 'year', 'payment_year', 'contract_year']:
                        try:
                            year_check = text(f"""
                                SELECT COUNT(*) 
                                FROM {table_name} 
                                WHERE {col} = :fiscal_year
                            """)
                            year_count = connection.execute(year_check, {'fiscal_year': params['fiscal_year']}).scalar()
                            logger.info(f"Found {year_count} records for fiscal year using column {col}: {params['fiscal_year']}")
                            if year_count > 0:
                                # Update the query to use this column
                                query = text(str(query).replace('fiscal_year', col))
                                logger.info(f"Updated query to use column {col}")
                                break
                        except Exception as e:
                            logger.error(f"Error checking fiscal year with column {col}: {str(e)}")
            
            # Now execute the main query with chunking
            while True:
                chunk_query = text(str(query) + f" LIMIT {chunk_size} OFFSET {offset}")
                logger.info(f"Executing chunk query: {str(chunk_query)}")
                logger.info(f"Chunk parameters: {params}")
                
                try:
                    chunk_data = connection.execute(chunk_query, params).fetchall()
                    if not chunk_data:
                        break
                    
                    # Convert to list of dicts using column names with proper encoding
                    columns = chunk_data[0]._mapping.keys()
                    chunk_dicts = []
                    for row in chunk_data:
                        # Convert each value to string with proper encoding
                        row_dict = {}
                        for col in columns:
                            value = row[col]
                            if isinstance(value, str):
                                # Handle string encoding
                                try:
                                    # Try to decode if it's bytes
                                    if isinstance(value, bytes):
                                        value = value.decode('utf-8')
                                    # Ensure it's properly encoded
                                    value = value.encode('utf-8', errors='replace').decode('utf-8')
                                except Exception as e:
                                    logger.warning(f"Error encoding value for column {col}: {str(e)}")
                                    value = str(value)
                            row_dict[col] = value
                        chunk_dicts.append(row_dict)
                    
                    all_data.extend(chunk_dicts)
                    logger.info(f"Retrieved {len(chunk_dicts)} records in this chunk")
                    
                    offset += chunk_size
                except Exception as e:
                    logger.error(f"Error executing chunk query: {str(e)}")
                    break
            
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