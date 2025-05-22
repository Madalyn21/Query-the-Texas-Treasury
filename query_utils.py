from sqlalchemy import text
from logger_config import get_logger
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
import time

# Initialize logger
logger = get_logger('query_utils')

def build_base_query(table_choice: str) -> Tuple[str, Dict]:
    """
    Builds the initial SQL query based on which table the user wants to query.
    
    This function creates the foundation of the SQL query that will be used to fetch data.
    It handles two different tables:
    - Payment Information: Basic query to fetch payment records
    - Contract Information: Basic query to fetch contract records
    
    Args:
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        Tuple[str, Dict]: A tuple containing:
            - The SQL query as a SQLAlchemy text object
            - An empty parameters dictionary (to be filled by add_filters_to_query)
    """
    logger.info(f"Building base query for table choice: '{table_choice}'")
    
    # Determine which table to query based on selection
    if table_choice == "Payment Information":
        query = text("""
            SELECT p.*
            FROM paymentinformation p
        """)
        logger.info("Selected paymentinformation table for query")
    else:  # Contract Information
        query = text("""
            SELECT c.*
            FROM contractinfo c
        """)
        logger.info("Selected contractinfo table for query")
    
    logger.info(f"Generated query: {str(query)}")
    return query, {}

def add_filters_to_query(query: text, filters: Dict, params: Dict, table_choice: str) -> Tuple[text, Dict]:
    """
    Adds user-selected filters to the base query.
    
    This function dynamically builds the WHERE clause of the SQL query based on
    the filters selected by the user. Different filters are available depending
    on which table is being queried:
    
    Payment Information filters:
    - fiscal_year: Filter by specific fiscal year (converts 4-digit to 2-digit)
    - fiscal_month: Filter by fiscal month
    - agency: Filter by agency name (case-insensitive)
    - vendor: Filter by vendor name (case-insensitive)
    - appropriation_object: Filter by object title
    
    Contract Information filters:
    - fiscal_year: Filter by specific fiscal year (converts 4-digit to 2-digit)
    - fiscal_month: Filter by fiscal month (using 'fm' column)
    - agency: Filter by agency name (case-insensitive)
    - vendor: Filter by vendor name (case-insensitive)
    - category: Filter by contract category
    - procurement_method: Filter by procurement method
    - status: Filter by contract status
    - subject: Filter by contract subject
    
    Args:
        query (text): The base SQLAlchemy query
        filters (Dict): Dictionary containing the filter values selected by user
        params (Dict): Dictionary to store SQL parameters
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        Tuple[text, Dict]: Updated query and parameters dictionary
    """
    logger.info(f"Adding filters for {table_choice}")
    logger.info(f"Filters received: {filters}")
    
    # Start building the WHERE clause
    where_conditions = []
    
    if table_choice == "Payment Information":
        if filters.get('fiscal_year_start') and filters.get('fiscal_year_end'):
            # Convert 4-digit years to 2-digit years
            start_year = str(filters['fiscal_year_start'])[-2:]  # Get last 2 digits
            end_year = str(filters['fiscal_year_end'])[-2:]      # Get last 2 digits
            where_conditions.append("p.fiscal_year BETWEEN :fiscal_year_start AND :fiscal_year_end")
            params['fiscal_year_start'] = start_year
            params['fiscal_year_end'] = end_year
            logger.info(f"Added fiscal year range filter: {start_year} to {end_year}")
            
        if filters.get('fiscal_month_start') and filters.get('fiscal_month_end'):
            where_conditions.append("p.fiscal_month BETWEEN :fiscal_month_start AND :fiscal_month_end")
            params['fiscal_month_start'] = filters['fiscal_month_start']
            params['fiscal_month_end'] = filters['fiscal_month_end']
            logger.info(f"Added fiscal month range filter: {filters['fiscal_month_start']} to {filters['fiscal_month_end']}")
            
        if filters.get('agency'):
            where_conditions.append("LOWER(p.agency_title) = LOWER(:agency)")
            params['agency'] = filters['agency']
            logger.info(f"Added agency filter (case-insensitive): {filters['agency']}")
            
        if filters.get('vendor'):
            where_conditions.append("LOWER(p.vendor_name) = LOWER(:vendor)")
            params['vendor'] = filters['vendor']
            logger.info(f"Added vendor filter (case-insensitive): {filters['vendor']}")
            
        if filters.get('appropriation_object'):
            where_conditions.append("p.object_title = :appropriation_object")
            params['appropriation_object'] = filters['appropriation_object']
            logger.info(f"Added appropriation object filter: {filters['appropriation_object']}")
            
    elif table_choice == "Contract Information":
        if filters.get('fiscal_year_start') and filters.get('fiscal_year_end'):
            # Convert 4-digit years to 2-digit years
            start_year = str(filters['fiscal_year_start'])[-2:]  # Get last 2 digits
            end_year = str(filters['fiscal_year_end'])[-2:]      # Get last 2 digits
            where_conditions.append("c.fiscal_year BETWEEN :fiscal_year_start AND :fiscal_year_end")
            params['fiscal_year_start'] = start_year
            params['fiscal_year_end'] = end_year
            logger.info(f"Added fiscal year range filter: {start_year} to {end_year}")
            
        if filters.get('fiscal_month_start') and filters.get('fiscal_month_end'):
            where_conditions.append("c.fm BETWEEN :fiscal_month_start AND :fiscal_month_end")
            params['fiscal_month_start'] = filters['fiscal_month_start']
            params['fiscal_month_end'] = filters['fiscal_month_end']
            logger.info(f"Added fiscal month range filter: {filters['fiscal_month_start']} to {filters['fiscal_month_end']}")
            
        if filters.get('agency'):
            where_conditions.append("LOWER(c.agency) = LOWER(:agency)")
            params['agency'] = filters['agency']
            logger.info(f"Added agency filter (case-insensitive): {filters['agency']}")
            
        if filters.get('vendor'):
            where_conditions.append("LOWER(c.vendor) = LOWER(:vendor)")
            params['vendor'] = filters['vendor']
            logger.info(f"Added vendor filter (case-insensitive): {filters['vendor']}")
            
        if filters.get('category'):
            where_conditions.append("c.category = :category")
            params['category'] = filters['category']
            logger.info(f"Added category filter: {filters['category']}")
            
        if filters.get('procurement_method'):
            where_conditions.append("c.procurement_method = :procurement_method")
            params['procurement_method'] = filters['procurement_method']
            logger.info(f"Added procurement method filter: {filters['procurement_method']}")
            
        if filters.get('status'):
            where_conditions.append("c.status = :status")
            params['status'] = filters['status']
            logger.info(f"Added status filter: {filters['status']}")
            
        if filters.get('subject'):
            where_conditions.append("c.subject = :subject")
            params['subject'] = filters['subject']
            logger.info(f"Added subject filter: {filters['subject']}")
    
    # Add WHERE clause if we have any conditions
    if where_conditions:
        query = text(str(query) + " WHERE " + " AND ".join(where_conditions))
    
    logger.info(f"Final query: {str(query)}")
    logger.info(f"Query parameters: {params}")
    return query, params

def check_table_accessibility(engine) -> Dict[str, bool]:
    """
    Verifies if the database tables exist and are accessible.
    
    This function performs several checks:
    1. Checks if each table exists in the database
    2. Retrieves and logs the table structure (column names and types)
    3. Attempts to execute a simple query on each table
    4. Logs detailed information about table accessibility
    
    Args:
        engine: SQLAlchemy engine instance for database connection
        
    Returns:
        Dict[str, bool]: Dictionary indicating which tables are accessible:
            - 'paymentinformation': True if payment information table is accessible
            - 'contractinfo': True if contract information table is accessible
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
                # Log paymentinformation table structure
                payment_columns = text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'paymentinformation'
                    ORDER BY ordinal_position;
                """)
                payment_structure = connection.execute(payment_columns).fetchall()
                logger.info(f"Paymentinformation table structure: {payment_structure}")
                
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
                # Log contractinfo table structure
                contract_columns = text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'contractinfo'
                    ORDER BY ordinal_position;
                """)
                contract_structure = connection.execute(contract_columns).fetchall()
                logger.info(f"Contractinfo table structure: {contract_structure}")
                
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

def execute_query(query: text, params: Dict, engine, page_size: int = 150, page: int = 1) -> Tuple[List[Dict], bool]:
    """
    Executes the SQL query with pagination to handle large result sets efficiently.
    
    Args:
        query (text): The SQLAlchemy query to execute
        params (Dict): Dictionary of parameters for the query
        engine: SQLAlchemy engine instance
        page_size (int): Number of records to return per page
        page (int): Current page number (1-based)
        
    Returns:
        Tuple[List[Dict], bool]: List of dictionaries containing the query results and a boolean indicating if more results exist
    """
    start_time = time.time()
    logger.info(f"Executing query with pagination (page {page}, size {page_size})")
    logger.info(f"Query: {str(query)}")
    logger.info(f"Parameters: {params}")
    
    # First check if tables are accessible
    table_access = check_table_accessibility(engine)
    if not any(table_access.values()):
        logger.error("No tables are accessible")
        return [], False
    
    try:
        with engine.connect() as connection:
            # First, let's check if the table exists
            table_name = "paymentinformation" if "paymentinformation" in str(query).lower() else "contractinfo"
            logger.info(f"Checking for table: {table_name}")
            
            if not table_access.get(table_name, False):
                logger.error(f"Table {table_name} is not accessible")
                return [], False
            
            # Let's also check the columns
            columns_query = text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """)
            columns = [(row[0], row[1]) for row in connection.execute(columns_query)]
            logger.info(f"Available columns in {table_name}: {columns}")
            
            # Remove any existing LIMIT clause and add our pagination
            base_query = str(query)
            if "LIMIT" in base_query:
                base_query = base_query.split("LIMIT")[0].strip()
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Execute the query with pagination
            paginated_query = text(f"{base_query} LIMIT {page_size + 1} OFFSET {offset}")
            logger.info(f"Executing paginated query: {str(paginated_query)}")
            
            try:
                query_start_time = time.time()
                results = connection.execute(paginated_query, params).fetchall()
                query_time = time.time() - query_start_time
                logger.info(f"Query took {query_time:.2f} seconds")
                
                # Check if there are more results
                has_more = len(results) > page_size
                if has_more:
                    results = results[:-1]  # Remove the extra result we fetched
                
                # Convert to list of dicts using column names from the result
                data = []
                for row in results:
                    row_dict = {}
                    for i, col in enumerate(row._mapping.keys()):
                        row_dict[col] = row[i]
                    data.append(row_dict)
                
                total_time = time.time() - start_time
                logger.info(f"Total query execution took {total_time:.2f} seconds")
                logger.info(f"Query execution returned {len(data)} records")
                return data, has_more
                
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                return [], False
            
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}", exc_info=True)
        return [], False

def get_filtered_data(filters: Dict, table_choice: str, engine, page: int = 1) -> Tuple[pd.DataFrame, bool]:
    """
    Main function to get filtered data from the database and return it as a DataFrame.
    
    Args:
        filters (Dict): Dictionary containing filter values selected by user
        table_choice (str): Either "Payment Information" or "Contract Information"
        engine: SQLAlchemy engine instance
        page (int): Current page number (1-based)
        
    Returns:
        Tuple[pd.DataFrame, bool]: DataFrame containing the filtered data and a boolean indicating if more results exist
    """
    logger.info(f"Getting filtered data for {table_choice} (page {page})")
    logger.info(f"Filters received: {filters}")
    
    try:
        # Build the base query
        query, params = build_base_query(table_choice)
        logger.info(f"Base query built: {str(query)}")
        
        # Add filters to the query
        query, params = add_filters_to_query(query, filters, params, table_choice)
        logger.info(f"Query after adding filters: {str(query)}")
        logger.info(f"Parameters after adding filters: {params}")
        
        # Execute the query with pagination
        data, has_more = execute_query(query, params, engine, page_size=150, page=page)
        logger.info(f"Query execution returned {len(data)} records")
        
        # Convert to DataFrame
        if data:
            df = pd.DataFrame(data)
            # Sanitize column names
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            logger.info(f"DataFrame created with shape: {df.shape}")
            logger.info(f"DataFrame columns: {df.columns.tolist()}")
            return df, has_more
        else:
            logger.warning("No data returned from query")
            return pd.DataFrame(), False  # Return empty DataFrame if no data
            
    except Exception as e:
        logger.error(f"Error getting filtered data: {str(e)}", exc_info=True)
        return pd.DataFrame(), False  # Return empty DataFrame on error 

def get_complete_data(query: text, params: Dict, engine) -> List[Dict]:
    """
    Executes the SQL query to get the complete dataset without pagination.
    Used for downloading the full dataset.
    
    Args:
        query (text): The SQLAlchemy query to execute
        params (Dict): Dictionary of parameters for the query
        engine: SQLAlchemy engine instance
        
    Returns:
        List[Dict]: List of dictionaries containing all query results
    """
    start_time = time.time()
    logger.info("Executing query for complete dataset")
    logger.info(f"Query: {str(query)}")
    logger.info(f"Parameters: {params}")
    
    try:
        with engine.connect() as connection:
            # Remove any existing LIMIT clause
            base_query = str(query)
            if "LIMIT" in base_query:
                base_query = base_query.split("LIMIT")[0].strip()
            
            # Execute the query without pagination
            complete_query = text(base_query)
            logger.info(f"Executing complete query: {str(complete_query)}")
            
            try:
                query_start_time = time.time()
                results = connection.execute(complete_query, params).fetchall()
                query_time = time.time() - query_start_time
                logger.info(f"Query took {query_time:.2f} seconds")
                
                # Convert to list of dicts using column names from the result
                data = []
                for row in results:
                    row_dict = {}
                    for i, col in enumerate(row._mapping.keys()):
                        row_dict[col] = row[i]
                    data.append(row_dict)
                
                total_time = time.time() - start_time
                logger.info(f"Total query execution took {total_time:.2f} seconds")
                logger.info(f"Query execution returned {len(data)} records")
                return data
                
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                return []
            
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}", exc_info=True)
        return []

def get_complete_filtered_data(filters: Dict, table_choice: str, engine) -> pd.DataFrame:
    """
    Gets the complete filtered data from the database without pagination.
    Used for downloading the full dataset.
    
    Args:
        filters (Dict): Dictionary containing filter values selected by user
        table_choice (str): Either "Payment Information" or "Contract Information"
        engine: SQLAlchemy engine instance
        
    Returns:
        pd.DataFrame: DataFrame containing all filtered data
    """
    logger.info(f"Getting complete filtered data for {table_choice}")
    logger.info(f"Filters received: {filters}")
    
    try:
        # Build the base query
        query, params = build_base_query(table_choice)
        logger.info(f"Base query built: {str(query)}")
        
        # Add filters to the query
        query, params = add_filters_to_query(query, filters, params, table_choice)
        logger.info(f"Query after adding filters: {str(query)}")
        logger.info(f"Parameters after adding filters: {params}")
        
        # Execute the query without pagination
        data = get_complete_data(query, params, engine)
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