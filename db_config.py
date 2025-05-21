import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from logger_config import get_logger

# Initialize logger
logger = get_logger('db_config')

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create and return a database connection"""
    try:
        # Get database credentials from environment variables
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_PORT = os.getenv('DB_PORT', '5432')
        DB_NAME = os.getenv('DB_NAME')
        DB_USER = os.getenv('DB_USER')
        DB_PASSWORD = os.getenv('DB_PASSWORD')

        # Check if we're in development mode
        is_development = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Construct database URL based on environment
        if is_development:
            # Local development connection string
            DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        else:
            # Production connection string with SSL
            DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
        
        # Create SQLAlchemy engine
        engine = create_engine(DATABASE_URL)
        
        # Test the connection
        with engine.connect() as connection:
            logger.info("Successfully connected to the database")
            return engine
            
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def get_db_session():
    """Create and return a database session"""
    try:
        engine = get_db_connection()
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        logger.error(f"Error creating database session: {str(e)}")
        raise 