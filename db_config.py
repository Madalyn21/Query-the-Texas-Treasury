import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from logger_config import get_logger
from typing import Dict, List, Tuple, Optional

# Initialize logger
logger = get_logger('db_config')

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    try:
        # Get database credentials from environment variables
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        db_name = os.getenv('DB_NAME')
        
        # Create database URL
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Create engine
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        logger.error(f"Error creating database connection: {str(e)}")
        raise

def check_table_exists(connection, table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        query = text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            );
        """)
        return connection.execute(query).scalar()
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {str(e)}")
        return False

def get_table_columns(connection, table_name: str) -> List[Tuple[str, str]]:
    """Get column information for a table"""
    try:
        query = text(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
        """)
        return [(row[0], row[1]) for row in connection.execute(query)]
    except Exception as e:
        logger.error(f"Error getting columns for table {table_name}: {str(e)}")
        return []

def check_table_accessibility(engine) -> Dict[str, bool]:
    """Check if tables are accessible"""
    accessibility = {
        'paymentinformation': False,
        'contractinfo': False
    }
    
    try:
        with engine.connect() as connection:
            for table_name in accessibility.keys():
                if check_table_exists(connection, table_name):
                    # Try to execute a simple query
                    test_query = text(f"SELECT COUNT(*) FROM {table_name} LIMIT 1")
                    try:
                        count = connection.execute(test_query).scalar()
                        logger.info(f"{table_name} table is accessible. Sample count: {count}")
                        accessibility[table_name] = True
                    except Exception as e:
                        logger.error(f"{table_name} table exists but is not accessible: {str(e)}")
                else:
                    logger.warning(f"{table_name} table does not exist")
            
            return accessibility
    except Exception as e:
        logger.error(f"Error checking table accessibility: {str(e)}")
        return accessibility

def execute_safe_query(connection, query: text, params: Dict = None) -> Optional[List[Dict]]:
    """Execute a query safely with error handling"""
    try:
        # Ensure params is a dictionary
        params = params or {}
        logger.info(f"Query being executed: {str(query)}")
        logger.info(f"Parameters being passed: {params}")
        logger.info(f"Parameter types: {[(k, type(v)) for k, v in params.items()]}")
        
        # Create a new dictionary with the same key-value pairs
        safe_params = {}
        for key, value in params.items():
            safe_params[key] = value
        logger.info(f"Safe parameters: {safe_params}")
        
        # Execute query with parameters as a dictionary
        result = connection.execute(query, safe_params)
        return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        return None

def get_db_session():
    """Create and return a database session"""
    try:
        engine = get_db_connection()
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Error creating database session: {str(e)}")
        raise 