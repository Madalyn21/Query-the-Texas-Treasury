# Standard library imports
import io
import json
import os
import platform
import secrets
import sys
import time
import zipfile
from datetime import datetime, timedelta
import tempfile

# Configure pandas before importing
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

# Set environment variables
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':/home/ubuntu/Query-the-Texas-Treasury/venv/lib/python3.8/site-packages'

# Third-party imports
import pandas as pd
import psutil
import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from sqlalchemy import text

# Local imports
from logger_config import get_logger
from query_utils import (
    get_filtered_data, 
    check_table_accessibility, 
    get_complete_filtered_data,
    get_complete_data
)
from db_config import get_db_connection

# Additional imports for visualizations
import numpy as np
import altair as alt
import streamlit.components.v1 as components
import base64

# Configure pandas options
pd.options.mode.chained_assignment = None  # default='warn'
pd.options.display.max_rows = 100
pd.options.display.max_columns = 100

# Version identifier
APP_VERSION = "1.1.5-DB-TEST-2024-05-16"

# Check Python version
if sys.version_info < (3, 8) or sys.version_info >= (3, 9):
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    st.error(f"""
    ⚠️ **Python Version Error**
    
    Current Python version: {current_version}
    Required Python version: 3.8.x
    
    Please ensure you are using Python 3.8.x to run this application.
    You can check your Python version by running:
    ```
    python --version
    ```
    
    To fix this:
    1. Install Python 3.8.x from [python.org](https://www.python.org/downloads/)
    2. Create a new virtual environment with Python 3.8.x
    3. Reinstall the requirements:
    ```
    pip install -r requirements.txt
    ```
    """)
    st.stop()

# Initialize logger
logger = get_logger('app')

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

def get_current_time():
    """Get current time without timezone information"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_current_time_iso():
    """Get current time in ISO format without timezone information"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

# Add caching decorator at the top of the file after imports
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_csv_data(file_path, encoding='utf-8'):
    """Load CSV data with caching"""
    try:
        return pd.read_csv(file_path, encoding=encoding)
    except UnicodeDecodeError:
        # Try alternative encodings if utf-8 fails
        for enc in ['latin1', 'cp1252', 'iso-8859-1']:
            try:
                return pd.read_csv(file_path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise Exception(f"Could not read file with any of the attempted encodings: {file_path}")
    except FileNotFoundError:
        raise Exception(f"File not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading {file_path}: {str(e)}")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def process_dropdown_data(df, column_name):
    """Process dropdown data with caching"""
    values = df[column_name].unique()
    return sorted([(str(val), str(val)) for val in values])

def validate_input(data):
    """Validate and sanitize user input"""
    if isinstance(data, str):
        # Remove any potentially dangerous characters
        return ''.join(c for c in data if c.isalnum() or c in ' -_.,')
    return data

def secure_request(url, method='GET', **kwargs):
    """Make secure HTTP requests with proper headers and timeout"""
    try:
        headers = {
            'User-Agent': 'Texas-Treasury-Query/1.0',
            'Accept': 'application/json',
            'X-Request-ID': st.session_state.session_id
        }
        
        # Add API key if available
        api_key = os.getenv('API_KEY')
        if not api_key:
            logger.warning("API_KEY not found in environment variables. API requests may fail.")
            st.warning("API authentication not configured. Some features may be limited.")
        else:
            headers['Authorization'] = f'Bearer {api_key}'
        
        # Set timeout and verify SSL
        kwargs.setdefault('timeout', 30)
        kwargs.setdefault('verify', True)
        kwargs['headers'] = headers
        
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        if "401" in str(e):
            st.error("Authentication failed. Please check API credentials.")
        elif "403" in str(e):
            st.error("Access denied. Please check API permissions.")
        else:
            st.error(f"Request failed: {str(e)}")
        raise

# Get API URL from environment variable with fallback
API_URL = os.getenv('API_URL', 'http://127.0.0.1:5000')
logger.info(f"Using API URL: {API_URL}")

def get_filter_options():
    """Get filter options from database"""
    logger.info("Starting to retrieve filter options")
    try:
        logger.info("Getting database connection")
        engine = get_db_connection()
        
        with engine.connect() as connection:
            logger.info("Database connection established")
            
            # First, let's check if we can access the table
            test_query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'paymentinformation'
                );
            """)
            table_exists = connection.execute(test_query).scalar()
            logger.info(f"Paymentinformation table exists: {table_exists}")
            
            if not table_exists:
                st.error("Required table 'paymentinformation' not found in database")
                return {
                    'agencies': [],
                    'vendors': [],
                    'appropriation_titles': [],
                    'fiscal_years': []
                }
            
            # Get column names to verify they exist
            columns_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'paymentinformation';
            """)
            columns = [row[0] for row in connection.execute(columns_query)]
            logger.info(f"Available columns: {columns}")
            
            # Get unique values for each filter using actual column names
            try:
                agency_query = text("SELECT DISTINCT agency_number FROM paymentinformation WHERE agency_number IS NOT NULL ORDER BY agency_number")
                agencies = [str(row[0]) for row in connection.execute(agency_query)]
                logger.info(f"Retrieved {len(agencies)} agency numbers")
                st.write(f"Found {len(agencies)} agency numbers")  # Debug output
            except Exception as e:
                logger.error(f"Error getting agency numbers: {str(e)}")
                st.error(f"Error getting agency numbers: {str(e)}")
                agencies = []
            
            try:
                vendor_query = text("SELECT DISTINCT vendor_number FROM paymentinformation WHERE vendor_number IS NOT NULL ORDER BY vendor_number")
                vendors = [str(row[0]) for row in connection.execute(vendor_query)]
                logger.info(f"Retrieved {len(vendors)} vendor numbers")
                st.write(f"Found {len(vendors)} vendor numbers")  # Debug output
            except Exception as e:
                logger.error(f"Error getting vendor numbers: {str(e)}")
                st.error(f"Error getting vendor numbers: {str(e)}")
                vendors = []
            
            try:
                appropriation_query = text("SELECT DISTINCT appropriation_number FROM paymentinformation WHERE appropriation_number IS NOT NULL ORDER BY appropriation_number")
                appropriation_titles = [str(row[0]) for row in connection.execute(appropriation_query)]
                logger.info(f"Retrieved {len(appropriation_titles)} appropriation numbers")
                st.write(f"Found {len(appropriation_titles)} appropriation numbers")  # Debug output
            except Exception as e:
                logger.error(f"Error getting appropriation numbers: {str(e)}")
                st.error(f"Error getting appropriation numbers: {str(e)}")
                appropriation_titles = []
            
            try:
                fiscal_year_query = text("SELECT DISTINCT fiscal_year FROM paymentinformation WHERE fiscal_year IS NOT NULL ORDER BY fiscal_year")
                fiscal_years = [str(row[0]) for row in connection.execute(fiscal_year_query)]
                logger.info(f"Retrieved {len(fiscal_years)} fiscal years")
                st.write(f"Found {len(fiscal_years)} fiscal years")  # Debug output
            except Exception as e:
                logger.error(f"Error getting fiscal years: {str(e)}")
                st.error(f"Error getting fiscal years: {str(e)}")
                fiscal_years = []
            
            options = {
                'agencies': agencies,
                'vendors': vendors,
                'appropriation_titles': appropriation_titles,
                'fiscal_years': fiscal_years
            }
            logger.info(f"Returning filter options: {options}")
            return options
            
    except Exception as e:
        logger.error(f"Error in get_filter_options: {str(e)}", exc_info=True)
        st.error(f"Error retrieving filter options: {str(e)}")
        return {
            'agencies': [],
            'vendors': [],
            'appropriation_titles': [],
            'fiscal_years': []
        }

def df_to_zip(df):
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('data.csv', csv_bytes)
    buffer.seek(0)
    return buffer.getvalue()

def get_system_status():
    """Get system status information"""
    try:
        status = {
            'status': 'healthy',
            'timestamp': get_current_time_iso(),
            'version': '1.0.0',  # Update this with your app version
            'system': {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent
            },
            'app': {
                'session_count': len(st.session_state),
                'api_url': API_URL,
                'log_level': os.getenv('LOG_LEVEL', 'INFO')
            }
        }
        return status
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}", exc_info=True)
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': get_current_time_iso()
        }

def check_deployment_health():
    """Check deployment health and return status"""
    try:
        # Check API connectivity
        api_status = "healthy"
        try:
            response = secure_request(f"{API_URL}/health", timeout=5)
            api_status = response.json().get('status', 'unknown')
        except Exception as e:
            logger.error(f"API health check failed: {str(e)}")
            api_status = "unhealthy"

        # Check disk space
        disk_status = "healthy"
        if psutil.disk_usage('/').percent > 90:
            disk_status = "warning"
            logger.warning("Disk usage above 90%")

        # Check memory usage
        memory_status = "healthy"
        if psutil.virtual_memory().percent > 90:
            memory_status = "warning"
            logger.warning("Memory usage above 90%")

        # Overall status
        overall_status = "healthy"
        if api_status == "unhealthy" or disk_status == "warning" or memory_status == "warning":
            overall_status = "warning"
        if api_status == "unhealthy" and (disk_status == "warning" or memory_status == "warning"):
            overall_status = "unhealthy"

        return {
            'status': overall_status,
            'components': {
                'api': api_status,
                'disk': disk_status,
                'memory': memory_status
            },
            'timestamp': get_current_time_iso()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': get_current_time_iso()
        }

def get_table_columns():
    """Get column names for all tables"""
    try:
        from db_config import get_db_connection
        engine = get_db_connection()
        
        tables = ['paymentinformation', 'contractinfo', 'mergedinfo']
        table_columns = {}
        
        with engine.connect() as connection:
            for table in tables:
                query = text(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """)
                result = connection.execute(query)
                columns = [(row[0], row[1]) for row in result]
                table_columns[table] = columns
                
        return table_columns
    except Exception as e:
        logger.error(f"Error getting table columns: {str(e)}", exc_info=True)
        return {}

def test_database_connection():
    """Test database connection and display data"""
    print(f"\n=== Database Connection Test - Version {APP_VERSION} ===")
    print("Attempting to connect to database...")
    
    try:
        from db_config import get_db_connection
        from query_utils import check_table_accessibility
        
        # Add loading spinner for database connection
        with st.spinner('Connecting to database...'):
            engine = get_db_connection()
            print("Database connection established successfully!")
        
        # Test basic connection with spinner
        query = "SELECT current_timestamp;"
        print(f"Executing test query: {query}")
        with st.spinner('Testing database connection...'):
            with engine.connect() as connection:
                result = connection.execute(text(query))
                timestamp = result.scalar()
                st.success(f"Database connection successful! Current timestamp: {timestamp}")
        
        # Check table accessibility with spinner
        st.subheader("Database Table Structure")
        with st.spinner('Checking table accessibility...'):
            accessibility = check_table_accessibility(engine)
        
        # Display table status and columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Payment Information Table")
            if accessibility['paymentinformation']:
                st.success("✅ Payment Information table is accessible")
                # Get and display columns
                with engine.connect() as connection:
                    columns_query = text("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'paymentinformation'
                        ORDER BY ordinal_position;
                    """)
                    columns = connection.execute(columns_query).fetchall()
                    st.write("Columns:")
                    for col in columns:
                        st.write(f"- {col[0]} ({col[1]})")
            else:
                st.error("❌ Payment Information table is not accessible")
                
        with col2:
            st.subheader("Contract Information Table")
            if accessibility['contractinfo']:
                st.success("✅ Contract Information table is accessible")
                # Get and display columns
                with engine.connect() as connection:
                    columns_query = text("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'contractinfo'
                        ORDER BY ordinal_position;
                    """)
                    columns = connection.execute(columns_query).fetchall()
                    st.write("Columns:")
                    for col in columns:
                        st.write(f"- {col[0]} ({col[1]})")
            else:
                st.error("❌ Contract Information table is not accessible")
        
        # Display overall status
        if accessibility['paymentinformation'] and accessibility['contractinfo']:
            st.success("Both tables are accessible and ready for queries")
        elif accessibility['paymentinformation']:
            st.warning("Only Payment Information table is accessible")
        elif accessibility['contractinfo']:
            st.warning("Only Contract Information table is accessible")
        else:
            st.error("Neither table is accessible. Please check database configuration.")
            
    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        st.error(error_msg)
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
    print("=== End of Database Connection Test ===\n")

def download_csv(df):
    """Convert DataFrame to CSV and create download button"""
    try:
        # Add download button for CSV
        if not df.empty:
            try:
                # Create a temporary file to store the CSV
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
                temp_file.close()
                
                # Write the DataFrame to CSV in chunks
                chunk_size = 10000  # Process 10,000 rows at a time
                total_rows = len(df)
                
                with open(temp_file.name, 'w', newline='', encoding='utf-8') as f:
                    # Write header
                    df.head(0).to_csv(f, index=False)
                    
                    # Write data in chunks
                    for start in range(0, total_rows, chunk_size):
                        end = min(start + chunk_size, total_rows)
                        chunk = df.iloc[start:end]
                        chunk.to_csv(f, index=False, header=False, mode='a')
                
                # Create download button
                with open(temp_file.name, 'rb') as f:
                    csv_data = f.read()
                
                # Clean up the temporary file
                os.unlink(temp_file.name)
                
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"{table_choice.lower().replace(' ', '_')}_data.csv",
                    mime="text/csv",
                    key="download_csv_button_1"
                )
            except Exception as e:
                logger.error(f"Error creating CSV: {str(e)}")
                st.error("Error creating CSV file. Please try again or contact support if the issue persists.")
    except Exception as e:
        logger.error(f"Error creating CSV download: {str(e)}", exc_info=True)
        st.error("Error creating CSV download")

def initialize_session_state():
    """Initialize session state variables"""
    if 'filter_options' not in st.session_state:
        st.session_state.filter_options = {
            'Payment Information': None,
            'Contract Information': None
        }
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            'agency': None,
            'vendor': None,
            'appropriation_title': None,
            'payment_source': None,
            'appropriation_object': None,
            'fiscal_year_start': None,
            'fiscal_year_end': None,
            'fiscal_month_start': None,
            'fiscal_month_end': None,
            'category': None,
            'procurement_method': None,
            'status': None,
            'subject': None
        }
    if 'vendor_limit' not in st.session_state:
        st.session_state.vendor_limit = 15  # Default limit for vendor search results
    if 'selected_vendor' not in st.session_state:
        st.session_state.selected_vendor = None

    # Initialize session state for pagination if not exists
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'has_more_results' not in st.session_state:
        st.session_state.has_more_results = False

def load_filter_options(table_choice):
    """Load all filter options for a given table choice"""
    # Check if we already have the data cached in session state
    if st.session_state.filter_options[table_choice] is not None:
        return st.session_state.filter_options[table_choice]

    try:
        if table_choice == "Payment Information":
            with st.spinner('Loading payment information filters...'):
                progress_bar = st.progress(0)
                
                # Define file paths
                file_paths = [
                    'Dropdown_Menu/payments_agy_titlelist.csv',
                    'Dropdown_Menu/payments_apro_titlelist.csv',
                    'Dropdown_Menu/payments_fund_titlelist.csv',
                    'Dropdown_Menu/payments_obj_titlelist.csv',
                    'Dropdown_Menu/payments_ven_namelist.csv'
                ]
                
                # Load files sequentially with chunking for large files
                data_dict = {}
                for i, file_path in enumerate(file_paths):
                    try:
                        if file_path.endswith('payments_ven_namelist.csv'):
                            # Initialize empty DataFrame for vendors - we'll load them on demand
                            data_dict[file_path] = pd.DataFrame(columns=['Ven_NAME'])
                            logger.info("Initialized empty vendor DataFrame for on-demand loading")
                        else:
                            data_dict[file_path] = load_csv_data(file_path)
                        progress_bar.progress((i + 1) / len(file_paths))
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        logger.error(f"Detailed error loading {file_path}:\n{error_details}")
                        st.error(f"""
                        Error loading {file_path}:
                        Error type: {type(e).__name__}
                        Error message: {str(e)}
                        
                        Please check:
                        1. File exists at: {os.path.abspath(file_path)}
                        2. File is readable
                        3. File has correct format
                        """)
                        data_dict[file_path] = pd.DataFrame()
                
                # Process the data with error handling
                try:
                    agencies = process_dropdown_data(data_dict[file_paths[0]], 'AGY_TITLE')
                except Exception as e:
                    logger.error(f"Error processing agencies: {str(e)}")
                    agencies = []
                
                try:
                    appropriation_titles = process_dropdown_data(data_dict[file_paths[1]], 'APRO_TITLE')
                except Exception as e:
                    logger.error(f"Error processing appropriation titles: {str(e)}")
                    appropriation_titles = []
                
                try:
                    payment_sources = process_dropdown_data(data_dict[file_paths[2]], 'FUND_TITLE')
                except Exception as e:
                    logger.error(f"Error processing payment sources: {str(e)}")
                    payment_sources = []
                
                try:
                    appropriation_objects = process_dropdown_data(data_dict[file_paths[3]], 'OBJ_TITLE')
                except Exception as e:
                    logger.error(f"Error processing appropriation objects: {str(e)}")
                    appropriation_objects = []
                
                # Initialize empty vendors list - we'll load them on demand
                vendors = []
                
                result = {
                    'agencies': agencies,
                    'appropriation_titles': appropriation_titles,
                    'payment_sources': payment_sources,
                    'appropriation_objects': appropriation_objects,
                    'vendors': vendors,
                    'vendor_file_path': file_paths[4]  # Store the vendor file path for later use
                }
                
                # Cache the result in session state
                st.session_state.filter_options[table_choice] = result
                return result
                
        else:
            with st.spinner('Loading contract information filters...'):
                progress_bar = st.progress(0)
                
                # Define file paths
                file_paths = [
                    'Dropdown_Menu/contract_agency_list.csv',
                    'Dropdown_Menu/contract_category_list.csv',
                    'Dropdown_Menu/contract_vendor_list.csv',
                    'Dropdown_Menu/contract_procurement_method_list.csv',
                    'Dropdown_Menu/contract_status_list.csv',
                    'Dropdown_Menu/contract_subject_list.csv'
                ]
                
                # Load files sequentially with chunking for large files
                data_dict = {}
                for i, file_path in enumerate(file_paths):
                    try:
                        if file_path.endswith('contract_vendor_list.csv'):
                            # Use chunking for the large vendor file with smaller chunks
                            logger.info(f"Loading large vendor file: {file_path}")
                            unique_vendors = set()
                            chunk_size = 5000  # Increased chunk size since we're only keeping unique values
                            total_chunks = 0
                            
                            try:
                                # Read with specific encoding and quote handling
                                for chunk in pd.read_csv(
                                    file_path,
                                    chunksize=chunk_size,
                                    usecols=['Vendor'],
                                    encoding='latin1',  # Use latin1 which can handle all byte values
                                    quoting=3,  # QUOTE_NONE
                                    quotechar=None,
                                    escapechar='\\',
                                    on_bad_lines='skip'  # Skip problematic lines
                                ):
                                    # Clean the vendor names
                                    cleaned_vendors = (
                                        chunk['Vendor']
                                        .str.replace('"', '')    # Remove double quotes
                                        .str.strip()             # Remove whitespace
                                    )
                                    unique_vendors.update(cleaned_vendors.dropna().unique())
                                    total_chunks += 1
                                    logger.info(f"Processed chunk {total_chunks}, current unique vendors: {len(unique_vendors)}")
                                
                                # Convert set to DataFrame
                                data_dict[file_path] = pd.DataFrame({'Vendor': list(unique_vendors)})
                                logger.info(f"Successfully loaded {len(unique_vendors)} unique vendors")
                                
                                # Verify the number of unique vendors
                                if len(unique_vendors) > 50000:
                                    logger.warning(f"Number of unique vendors ({len(unique_vendors)}) is higher than expected (45k)")
                            except Exception as e:
                                import traceback
                                error_details = traceback.format_exc()
                                logger.error(f"Detailed error loading {file_path}:\n{error_details}")
                                st.error(f"""
                                Error loading {file_path}:
                                Error type: {type(e).__name__}
                                Error message: {str(e)}
                                
                                Please check:
                                1. File exists at: {os.path.abspath(file_path)}
                                2. File is readable
                                3. File has correct format
                                """)
                                data_dict[file_path] = pd.DataFrame()
                        else:
                            data_dict[file_path] = load_csv_data(file_path)
                        progress_bar.progress((i + 1) / len(file_paths))
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        logger.error(f"Detailed error loading {file_path}:\n{error_details}")
                        st.error(f"""
                        Error loading {file_path}:
                        Error type: {type(e).__name__}
                        Error message: {str(e)}
                        
                        Please check:
                        1. File exists at: {os.path.abspath(file_path)}
                        2. File is readable
                        3. File has correct format
                        """)
                        data_dict[file_path] = pd.DataFrame()
                
                # Process the data with error handling
                try:
                    agency_df = pd.read_csv('Dropdown_Menu/contract_agency_list.csv')
                    logger.info(f"Found columns in agency list: {agency_df.columns.tolist()}")
                    if 'Agency' not in agency_df.columns:
                        raise Exception(f"Column 'Agency' not found. Available columns: {agency_df.columns.tolist()}")
                    agencies = [(str(row['Agency']), str(row['Agency'])) for _, row in agency_df.iterrows()]
                    agencies.sort()
                except Exception as e:
                    logger.error(f"Error loading agency list: {str(e)}", exc_info=True)
                    agencies = []
                
                try:
                    category_df = pd.read_csv('Dropdown_Menu/contract_category_list.csv')
                    logger.info(f"Found columns in contract_category_list.csv: {category_df.columns.tolist()}")
                    if 'Category' not in category_df.columns:
                        raise Exception(f"Column 'Category' not found. Available columns: {category_df.columns.tolist()}")
                    categories = [(str(row['Category']), str(row['Category'])) for _, row in category_df.iterrows()]
                    categories.sort(key=lambda x: x[0])
                except Exception as e:
                    logger.error(f"Error loading category data: {str(e)}", exc_info=True)
                    categories = []
                
                try:
                    vendors = process_dropdown_data(data_dict[file_paths[2]], 'Vendor')
                except Exception as e:
                    logger.error(f"Error processing vendors: {str(e)}")
                    vendors = []
                
                try:
                    procurement_methods = process_dropdown_data(data_dict[file_paths[3]], 'Procurement Method')
                except Exception as e:
                    logger.error(f"Error processing procurement methods: {str(e)}")
                    procurement_methods = []
                
                try:
                    statuses = process_dropdown_data(data_dict[file_paths[4]], 'Status')
                except Exception as e:
                    logger.error(f"Error processing statuses: {str(e)}")
                    statuses = []
                
                try:
                    subjects = process_dropdown_data(data_dict[file_paths[5]], 'Subject')
                except Exception as e:
                    logger.error(f"Error processing subjects: {str(e)}")
                    subjects = []
                
                result = {
                    'agencies': agencies,
                    'categories': categories,
                    'vendors': vendors,
                    'procurement_methods': procurement_methods,
                    'statuses': statuses,
                    'subjects': subjects
                }
                
                # Cache the result in session state
                st.session_state.filter_options[table_choice] = result
                return result
                
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Detailed error in load_filter_options:\n{error_details}")
        st.error(f"""
        Error loading filter options:
        Error type: {type(e).__name__}
        Error message: {str(e)}
        
        Full error details have been logged.
        """)
        return None

def search_vendors(search_term, file_path, limit=15, offset=0):
    """Search for vendors matching the search term"""
    if not search_term or len(search_term) < 2:
        return []
    
    try:
        # Read the vendor file in chunks and filter for matches
        matching_vendors = set()
        chunk_size = 1000
        
        # Determine which column name to use based on the file path
        column_name = 'Vendor' if 'contract_vendor_list.csv' in file_path else 'Ven_NAME'
        
        for chunk in pd.read_csv(
            file_path,
            chunksize=chunk_size,
            usecols=[column_name],
            encoding='latin1',
            quoting=3,
            quotechar=None,
            escapechar='\\',
            on_bad_lines='skip'
        ):
            # Clean and filter vendor names
            cleaned_vendors = (
                chunk[column_name]
                .str.replace('"""', '')
                .str.replace('"', '')
                .str.strip()
            )
            
            # Filter for matches
            matches = cleaned_vendors[
                cleaned_vendors.str.lower().str.contains(search_term.lower(), na=False)
            ].unique()
            
            matching_vendors.update(matches)
            
            # If we have enough matches, we can stop
            if len(matching_vendors) >= offset + limit:
                break
        
        # Convert to sorted list and get the requested slice
        sorted_vendors = sorted(list(matching_vendors))
        return sorted_vendors[offset:offset + limit]
    
    except Exception as e:
        logger.error(f"Error searching vendors: {str(e)}")
        return []

from visualization_utils import generate_all_visualizations

def main():
    # Initialize session state at the start
    initialize_session_state()
    
    # Configure Streamlit security settings first
    logger.info("Starting main function")
    st.set_page_config(
        page_title="Texas Treasury Query",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    logger.info("Page config set")
    
    # Add loading delay with error handling
    try:
        with st.spinner('Loading application...'):
            time.sleep(1)  # Wait for 1 second
        logger.info("Loading spinner completed")
    except Exception as e:
        logger.error(f"Error during initial loading: {str(e)}")
        st.error("Error loading application. Please refresh the page.")
        return

    # Configure other security settings with error handling
    try:
        if 'session_id' not in st.session_state:
            st.session_state.session_id = secrets.token_urlsafe(32)
            logger.info("New session ID generated")
        
        # Set session expiry (24 hours)
        if 'session_start' not in st.session_state:
            st.session_state.session_start = datetime.now()
            logger.info("Session start time set")
        
        # Check session expiry
        if datetime.now() - st.session_state.session_start > timedelta(hours=24):
            logger.warning("Session expired, clearing session state")
            st.session_state.clear()
            st.session_state.session_id = secrets.token_urlsafe(32)
            st.session_state.session_start = datetime.now()
    except Exception as e:
        logger.error(f"Error in session management: {str(e)}")
        st.error("Error managing session. Please refresh the page.")
        return

    # Add memory management
    try:
        # Clear any large data from previous sessions
        if 'df' in st.session_state and len(st.session_state.df) > 10000:
            logger.info("Clearing large DataFrame from session state")
            del st.session_state.df
            st.session_state.df = None
    except Exception as e:
        logger.error(f"Error in memory management: {str(e)}")

    # Display version in sidebar
    logger.info("Setting up sidebar")
    st.sidebar.title("Database Status")
    st.sidebar.info(f"App Version: {APP_VERSION}")
    
    # Add a button to clear session state
    if st.sidebar.button("Clear Session Data"):
        st.session_state.clear()
        st.rerun()
    
    if st.sidebar.button("Test Database Connection"):
        test_database_connection()

    # Health check endpoint
    if st.query_params.get('health') == 'check':
        health_status = check_deployment_health()
        st.json(health_status)
        return

    # System status endpoint
    if st.query_params.get('status') == 'check':
        system_status = get_system_status()
        st.json(system_status)
        return
    
    # Privacy statement modal/checkbox with error handling
    try:
        if 'privacy_accepted' not in st.session_state:
            st.session_state['privacy_accepted'] = False
            logger.info("Privacy statement not accepted yet")

        if not st.session_state['privacy_accepted']:
            logger.info("Displaying privacy statement")
            st.markdown("""
            ## Privacy Statement
            By using this application, you acknowledge and accept that the queries you make may be recorded for research, quality assurance, or improvement purposes.
            """)
            if st.button("I Accept the Privacy Statement"):
                st.session_state['privacy_accepted'] = True
                logger.info("Privacy statement accepted")
                st.rerun()  # Rerun the app after accepting
            st.stop()  # Stop execution until privacy is accepted
    except Exception as e:
        logger.error(f"Error in privacy statement handling: {str(e)}")
        st.error("Error displaying privacy statement. Please refresh the page.")
        return

    # Title Container
    with st.container():
        st.title("Query the Texas Treasury")
        st.subheader("Committee on the Delivery of Government Efficiency")
        st.markdown("---")

    # Query Functionality Container
    with st.container():
        st.markdown("""
            <style>
            .query-container {
                background-color: #f0f2f6;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Create columns for the filter interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            logger.info("Setting up filter criteria")
            st.subheader("Filter Criteria")
            
            # Add table selection
            table_choice = st.radio(
                "Select Data Source",
                ["Payment Information", "Contract Information"],
                help="Choose which table to query data from"
            )
            
            # Add fiscal year and month sliders
            st.subheader("Fiscal Year and Month")
            
            # Load fiscal years
            try:
                fiscal_years_df = pd.read_csv('Dropdown_Menu/fiscal_years_both.csv')
                fiscal_years = fiscal_years_df['fiscal_year'].tolist()
                fiscal_years.sort()
            except Exception as e:
                logger.error(f"Error loading fiscal years: {str(e)}", exc_info=True)
                fiscal_years = []
            
            # Fiscal Year Slider
            if fiscal_years:
                selected_fiscal_year = st.select_slider(
                    "Fiscal Year",
                    options=fiscal_years,
                    value=(fiscal_years[0], fiscal_years[-1]),
                    help="Select a range of fiscal years"
                )
                
                # Store the selected fiscal year range
                st.session_state.filters['fiscal_year_start'] = selected_fiscal_year[0]
                st.session_state.filters['fiscal_year_end'] = selected_fiscal_year[1]
            
            # Fiscal Month Slider
            month_names = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            
            selected_fiscal_month = st.select_slider(
                "Fiscal Month",
                options=month_names,
                value=("January", "December"),
                help="Select a range of fiscal months"
            )
            
            # Convert month names to numbers
            month_to_number = {name: i+1 for i, name in enumerate(month_names)}
            st.session_state.filters['fiscal_month_start'] = month_to_number[selected_fiscal_month[0]]
            st.session_state.filters['fiscal_month_end'] = month_to_number[selected_fiscal_month[1]]
            
            # Load and display filter options
            filter_options = load_filter_options(table_choice)
            if filter_options is None:
                return
                
            # Display appropriate dropdowns based on table choice
            if table_choice == "Payment Information":
                # Payment Information dropdowns
                agency_options = ["All"] + [agency[0] for agency in filter_options['agencies']]
                selected_agency = st.selectbox("Agency", agency_options)
                st.session_state.filters['agency'] = selected_agency if selected_agency != "All" else None
                
                appropriation_options = ["All"] + [title[0] for title in filter_options['appropriation_titles']]
                selected_appropriation = st.selectbox("Appropriation Title", appropriation_options)
                
                payment_source_options = ["All"] + [source[0] for source in filter_options['payment_sources']]
                selected_payment_source = st.selectbox("Payment Source", payment_source_options)
                
                appropriation_object_options = ["All"] + [obj[0] for obj in filter_options['appropriation_objects']]
                selected_appropriation_object = st.selectbox("Appropriation Object", appropriation_object_options)
                
                vendor_file_path = 'Dropdown_Menu/payments_ven_namelist.csv'
            else:
                # Contract Information dropdowns
                agency_options = ["All"] + [agency[0] for agency in filter_options['agencies']]
                selected_agency = st.selectbox("Agency", agency_options)
                st.session_state.filters['agency'] = selected_agency if selected_agency != "All" else None
                
                category_options = ["All"] + [category[0] for category in filter_options['categories']]
                selected_category = st.selectbox("Category", category_options)
                
                procurement_method_options = ["All"] + [method[0] for method in filter_options['procurement_methods']]
                selected_procurement_method = st.selectbox("Procurement Method", procurement_method_options)
                
                status_options = ["All"] + [status[0] for status in filter_options['statuses']]
                selected_status = st.selectbox("Status", status_options)
                
                subject_options = ["All"] + [subject[0] for subject in filter_options['subjects']]
                selected_subject = st.selectbox("Subject", subject_options)
                
                vendor_file_path = 'Dropdown_Menu/contract_vendor_list.csv'
            
            # Vendor search
            st.subheader("Vendor Search")
            
            # Create a container for vendor search
            vendor_container = st.container()
            
            with vendor_container:
                # Initialize session state for vendor display limit if not exists
                if 'vendor_display_limit' not in st.session_state:
                    st.session_state.vendor_display_limit = 150
                if 'matching_vendors' not in st.session_state:
                    st.session_state.matching_vendors = []
                if 'last_search' not in st.session_state:
                    st.session_state.last_search = ""
                
                # Simple search input with help text
                vendor_search = st.text_input(
                    "Search for a vendor",
                    help="Type to search for vendors. Delete the text to clear your search.",
                    key="vendor_search_input"
                )
                
                # Handle vendor search and selection
                if vendor_search:
                    try:
                        # Only perform search if we don't have results or search term changed
                        if not st.session_state.matching_vendors or vendor_search != st.session_state.last_search:
                            # Read the vendor file with a specific encoding
                            vendors_df = pd.read_csv(
                                vendor_file_path,
                                encoding='latin1',
                                usecols=['Ven_NAME' if table_choice == "Payment Information" else 'Vendor'],
                                on_bad_lines='skip'
                            )
                            
                            # Get the correct column name
                            vendor_column = 'Ven_NAME' if table_choice == "Payment Information" else 'Vendor'
                            
                            # Basic cleaning
                            vendors_df[vendor_column] = vendors_df[vendor_column].astype(str).str.strip()
                            
                            # Simple search
                            matching_vendors = vendors_df[
                                vendors_df[vendor_column].str.contains(vendor_search, case=False, na=False)
                            ][vendor_column].unique().tolist()
                            
                            # Sort results and store in session state
                            st.session_state.matching_vendors = sorted(matching_vendors)
                            st.session_state.last_search = vendor_search
                        
                        # Get total count
                        total_vendors = len(st.session_state.matching_vendors)
                        
                        # Display current results
                        current_vendors = st.session_state.matching_vendors[:st.session_state.vendor_display_limit]
                        
                        if current_vendors:
                            # Show results count
                            st.write(f"Found {total_vendors} matching vendors")
                            
                            # Create a selectbox for vendor selection
                            selected_vendor = st.selectbox(
                                "Select a vendor",
                                options=[""] + current_vendors,
                                index=0,
                                key="vendor_select"
                            )
                            
                            if selected_vendor:
                                st.session_state.selected_vendor = selected_vendor
                                st.session_state.filters['vendor'] = selected_vendor
                                st.success(f"Selected vendor: {selected_vendor}")
                        else:
                            st.info("No matching vendors found. Try different search terms.")
                            st.session_state.filters['vendor'] = None
                            
                    except Exception as e:
                        logger.error(f"Error searching vendors: {str(e)}", exc_info=True)
                        st.error("Error searching vendors. Please try again.")
                else:
                    # Clear vendor selection when search is empty
                    st.session_state.selected_vendor = None
                    st.session_state.filters['vendor'] = None
                    st.session_state.matching_vendors = []  # Clear matching vendors
                    st.session_state.last_search = ""  # Clear last search
        
        with col2:
            st.subheader("Query Actions")
            submit_clicked = st.button("Submit Query", type="primary", use_container_width=True)
            readme_clicked = st.button("About", use_container_width=True)
            
            if readme_clicked:
                with st.expander("**About the Data and How to Use**", expanded=True):
                    st.markdown("""
                    ### Data Overview
                    This dashboard allows you to query the Texas Treasury database containing every payment made from the Texas Treasury, 
                    provided and managed by the Texas Comptroller of Public Accounts.
                    
                    ### How to Use
                    1. Select your desired filters from the dropdown menus
                    2. Use 'All' to include all values for that field
                    3. Click 'Submit Query' to view the results
                    4. Download the results using the download button
                    
                    ### Understanding the Dropdown Categories
                    
                    #### Payment Information Categories
                    - **Agency**: The government agency making the payment
                    - **Vendor**: The recipient of the payment
                    - **Appropriation Title**: The official name of a pot of money that the legislature has set aside for a specific purpose in the budget
                    - **Payment Source (Fund Title)**: The name of the account that actually holds the money
                    - **Appropriation Object**: A more detailed category within an appropriation that describes what the money will buy
                    
                    #### Contract Information Categories
                    - **Agency**: The government agency managing the contract
                    - **Vendor**: The company or entity providing the goods or services
                    - **Category**: The general type or classification of the contract
                    - **Procurement Method**: How the government chose the vendor for a contract
                    - **Status**: The current state of the contract
                    - **Subject**: A short description of what the contract covers
                    """)

            # Handle query submission
            if submit_clicked:
                logger.info("Query submitted")
                # Prepare and validate the filter payload
                filter_payload = {
                    k: validate_input(v) 
                    for k, v in st.session_state.filters.items() 
                    if v != 'All' and v is not None
                }
                
                logger.info(f"Filter payload: {filter_payload}")
                logger.info(f"Table choice: {table_choice}")
                
                try:
                    # Reset pagination when new query is submitted
                    st.session_state.current_page = 1
                    st.session_state.has_more_results = False
                    
                    # Get database connection with spinner and better error handling
                    with st.spinner('Connecting to database...'):
                        try:
                            engine = get_db_connection()
                            # Store the engine in session state
                            st.session_state.db_engine = engine
                            logger.info("Database connection established")
                        except Exception as db_error:
                            error_msg = str(db_error)
                            logger.error(f"Database connection error: {error_msg}", exc_info=True)
                            if "502" in error_msg:
                                st.error("""
                                Unable to connect to the database server. This could be due to:
                                1. The database server is temporarily unavailable
                                2. Network connectivity issues
                                3. Server maintenance
                                
                                Please try again in a few minutes. If the problem persists, contact support.
                                """)
                            else:
                                st.error(f"Database connection error: {error_msg}")
                            return
                    
                    # Get filtered data using the query utilities with spinner
                    with st.spinner('Executing query... This may take a few moments.'):
                        logger.info("Calling get_filtered_data with:")
                        logger.info(f"- filters: {filter_payload}")
                        logger.info(f"- table_choice: {table_choice}")
                        logger.info(f"- engine: {engine}")
                        
                        df, has_more = get_filtered_data(filter_payload, table_choice, engine)
                    
                    # Clear the loading container
                    st.empty()
                    
                    logger.info(f"Query result type: {type(df)}")
                    logger.info(f"Query result shape: {df.shape if isinstance(df, pd.DataFrame) else 'Not a DataFrame'}")
                    
                    # Store the results in session state
                    st.session_state['df'] = df
                    st.session_state.has_more_results = has_more
                    
                    # Display results if they exist
                    if 'df' in st.session_state and not st.session_state['df'].empty:
                        try:
                            # Display results count
                            st.write(f"Showing {len(df)} records")
                            
                            # Get total count from complete data
                            with st.spinner('Calculating total records...'):
                                complete_df = get_complete_filtered_data(
                                    st.session_state.filters, 
                                    table_choice, 
                                    st.session_state.db_engine
                                )
                                total_records = len(complete_df)
                                st.info(f"Showing {len(df)} records of {total_records:,} total records")
                            
                            # Display the dataframe
                            with st.spinner("Loading results..."):
                                st.dataframe(st.session_state['df'], use_container_width=True)
                            
                            # Download buttons and Load More button in a row
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                try:
                                    with st.spinner('Preparing CSV download...'):
                                        complete_df = get_complete_filtered_data(
                                            st.session_state.filters, 
                                            table_choice, 
                                            st.session_state.db_engine
                                        )
                                        csv_data = complete_df.to_csv(index=False)
                                        st.download_button(
                                            label="Download CSV",
                                            data=csv_data,
                                            file_name=f"{table_choice.lower().replace(' ', '_')}_data.csv",
                                            mime='text/csv',
                                            key="download_csv_button_1"
                                        )
                                except Exception as e:
                                    logger.error(f"Error preparing CSV download: {str(e)}", exc_info=True)
                                    st.error("Error preparing CSV download. Please try again.")
                            
                            with col2:
                                try:
                                    with st.spinner('Preparing ZIP download...'):
                                        complete_df = get_complete_filtered_data(
                                            st.session_state.filters, 
                                            table_choice, 
                                            st.session_state.db_engine
                                        )
                                        zip_data = df_to_zip(complete_df)
                                        st.download_button(
                                            label="Download ZIP",
                                            data=zip_data,
                                            file_name=f"{table_choice.lower().replace(' ', '_')}_data.zip",
                                            mime='application/zip',
                                            key="download_zip_button_1"
                                        )
                                except Exception as e:
                                    logger.error(f"Error preparing ZIP download: {str(e)}", exc_info=True)
                                    st.error("Error preparing ZIP download. Please try again.")
                            
                            with col3:
                                # Add Load More button if there are more results
                                if st.session_state.has_more_results:
                                    if st.button("Load 150 More", use_container_width=True, key="load_more_button"):
                                        try:
                                            # Store current state
                                            current_df = st.session_state['df']
                                            current_filters = st.session_state.filters.copy()
                                            
                                            # Increment page number
                                            st.session_state.current_page += 1
                                            
                                            # Get next page of results using the stored engine
                                            with st.spinner('Loading more results...'):
                                                next_df, has_more = get_filtered_data(
                                                    current_filters, 
                                                    table_choice, 
                                                    st.session_state.db_engine, 
                                                    page=st.session_state.current_page
                                                )
                                            
                                            if not next_df.empty:
                                                # Append new results to existing dataframe
                                                st.session_state['df'] = pd.concat([current_df, next_df], ignore_index=True)
                                                st.session_state.has_more_results = has_more
                                                st.success(f"Loaded {len(next_df)} more records!")
                                                # Force a rerun to update the display
                                                st.rerun()
                                            else:
                                                st.warning("No more results to load.")
                                                st.session_state.has_more_results = False
                                                st.session_state.current_page -= 1  # Reset page number if no more results
                                        except Exception as e:
                                            logger.error(f"Error loading more results: {str(e)}", exc_info=True)
                                            st.error(f"Error loading more results: {str(e)}")
                                            # Reset page number on error
                                            st.session_state.current_page -= 1
                        except Exception as e:
                            logger.error(f"Error displaying results: {str(e)}", exc_info=True)
                            st.error("Error displaying results. Please try again.")
                    else:
                        st.info("No results found for the selected filters.")
                        
                except Exception as e:
                    logger.error(f"Error executing query: {str(e)}", exc_info=True)
                    st.error("Error executing query. Please try again.")

    # Visualization Section
    with st.container():
        st.subheader("Visualization")
        st.info("Visualization Function Coming Soon!")

    # AI Analysis Container
    with st.container():
        st.markdown("""
            <style>
            .ai-container {
                background-color: #ffffff;
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 1rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.header("AI Analysis")
        st.info("AI-powered analysis and insights coming soon!")

    # Logos Container (always visible)
    with st.container():
        st.markdown("""
            <style>
            .logo-container {
                background-color: #ffffff;
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 1rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .logo-flex-container {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 2vw;
                flex-wrap: wrap;
                margin-top: 2em;
            }
            .logo-item {
                display: flex;
                align-items: center;
                justify-content: center;
                min-width: 120px;
                max-width: 25vw;
                padding: 1rem;
                border-radius: 0.5rem;
            }
            .logo-item img, .logo-item svg {
                width: 100%;
                height: auto;
                max-width: 200px;
            }
            .doge-logo-box {
                background-color: #000000;
                padding: 0.5rem;
                border-radius: 0.5rem;
                width: 50%;
                margin: 0 auto;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .doge-logo-box img {
                width: 100%;
                height: auto;
            }
            .house-logo-box {
                background-color: #000080;
                padding: 1rem;
                border-radius: 0.5rem;
            }
            .x-logo-box {
                background-color: #000000;
                padding: 0.5rem;
                border-radius: 0.5rem;
                display: inline-flex;
                align-items: center;
            }
            @media (max-width: 600px) {
                .logo-flex-container {
                    flex-direction: column;
                }
                .logo-item {
                    max-width: 60vw;
                }
            }
            .find-x-container {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5em;
                margin-top: 2em;
                font-size: 1.2em;
            }
            .x-logo-img {
                width: 32px;
                height: 32px;
                vertical-align: middle;
            }
            </style>
        """, unsafe_allow_html=True)
        
        try:
            # Responsive side-by-side clickable logos
            logo_path = os.path.join(os.path.dirname(__file__), "Texas DOGE_White.png")
            doge_img_html = ""
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as image_file:
                    encoded = base64.b64encode(image_file.read()).decode()
                doge_img_html = (
                    f'<div class="logo-item">'
                    f'<a href="https://house.texas.gov/committees/committee/233" target="_blank">'
                    f'<div class="doge-logo-box">'
                    f'<img src="data:image/png;base64,{encoded}" alt="DOGE Logo"/></div></a></div>'
                )
            
            svg_path = os.path.join(os.path.dirname(__file__), "Texas_House_Logo.svg")
            svg_img_html = ""
            if os.path.exists(svg_path):
                with open(svg_path, "r") as svg_file:
                    svg_content = svg_file.read()
                svg_img_html = (
                    f'<div class="logo-item">'
                    f'<a href="https://house.texas.gov/" target="_blank">'
                    f'<div class="house-logo-box">{svg_content}</div></a></div>'
                )
            
            if doge_img_html or svg_img_html:
                st.markdown(
                    f"""
                    <div class="logo-flex-container">
                        {doge_img_html}
                        {svg_img_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Add Find us on X section
                x_logo_path = os.path.join(os.path.dirname(__file__), "x_logo.png")
                x_logo_html = ""
                if os.path.exists(x_logo_path):
                    with open(x_logo_path, "rb") as x_img_file:
                        x_encoded = base64.b64encode(x_img_file.read()).decode()
                    x_logo_html = f'<a href="https://x.com/TxLegeDOGE" target="_blank"><div class="x-logo-box"><img src="data:image/png;base64,{x_encoded}" class="x-logo-img" alt="X Logo"/></div></a>'
                st.markdown(
                    f'<div class="find-x-container">Find us on {x_logo_html}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown("### Texas Department of Government Efficiency")
                st.warning("Logo file (Texas DOGE_White.png) or SVG file (Texas_House_Logo.svg) not found.")
        except Exception as e:
            st.markdown("### Texas Department of Government Efficiency")
            st.error(f"Error loading logo: {str(e)}")
            logger.error(f"Error in logos section: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please try again later.")
        raise