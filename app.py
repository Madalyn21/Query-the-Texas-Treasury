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
from query_utils import get_filtered_data, check_table_accessibility
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
APP_VERSION = "1.1.3-DB-TEST-2024-05-16"

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
        # Convert DataFrame to CSV
        csv = df.to_csv(index=False)
        
        # Create download button
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="queried_data.csv",
            mime="text/csv",
            help="Click to download the queried data as a CSV file"
        )
        logger.info("CSV download button created successfully")
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

    # Add error boundary for the main content
    try:
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
        
        logger.info("Starting application main content")
        
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

        # Main content with error handling
        try:
            logger.info("Displaying main title")
            st.title("Query the Texas Treasury")
            st.subheader("Committee on the Delivery of Government Efficiency")

            # Create a container for the main content
            main_container = st.container()
            
            with main_container:
                # Create columns for the filter interface with adjusted widths
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
                    logger.info(f"Table choice selected: {table_choice}")
                    
                    # Add fiscal year and month sliders
                    st.subheader("Fiscal Year and Month")
                    
                    # Load fiscal years
                    try:
                        fiscal_years_df = pd.read_csv('Dropdown_Menu/fiscal_years_both.csv')
                        logger.info(f"Found columns in fiscal_years_both.csv: {fiscal_years_df.columns.tolist()}")
                        if 'fiscal_year' not in fiscal_years_df.columns:
                            raise Exception(f"Column 'fiscal_year' not found. Available columns: {fiscal_years_df.columns.tolist()}")
                        fiscal_years = fiscal_years_df['fiscal_year'].tolist()
                        fiscal_years.sort()
                        logger.info(f"Found fiscal years: {fiscal_years}")
                        logger.info(f"Setting fiscal year range from {fiscal_years[0]} to {fiscal_years[-1]}")
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
                    
                    # Fiscal Month Slider with month names
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
                    
                    # Convert month names to numbers for storage
                    month_to_number = {name: i+1 for i, name in enumerate(month_names)}
                    st.session_state.filters['fiscal_month_start'] = month_to_number[selected_fiscal_month[0]]
                    st.session_state.filters['fiscal_month_end'] = month_to_number[selected_fiscal_month[1]]
                    
                    # Add a separator
                    st.markdown("---")
                    
                    # Load filter options
                    filter_options = load_filter_options(table_choice)
                    if filter_options is None:
                        return

                    # Display dropdowns based on table choice
                    if table_choice == "Payment Information":
                        # Display Payment Information dropdowns
                        agency_options = ["All"] + [agency[0] for agency in filter_options['agencies']]
                        selected_agency = st.selectbox("Agency", agency_options)
                        
                        appropriation_options = ["All"] + [title[0] for title in filter_options['appropriation_titles']]
                        selected_appropriation = st.selectbox("Appropriation Title", appropriation_options)
                        
                        payment_source_options = ["All"] + [source[0] for source in filter_options['payment_sources']]
                        selected_payment_source = st.selectbox("Payment Source", payment_source_options)
                        
                        appropriation_object_options = ["All"] + [obj[0] for obj in filter_options['appropriation_objects']]
                        selected_appropriation_object = st.selectbox("Appropriation Object", appropriation_object_options)
                        
                        # Add vendor file path for payment information
                        vendor_file_path = 'Dropdown_Menu/payments_ven_namelist.csv'
                    else:
                        # Display Contract Information dropdowns
                        agency_options = ["All"] + [agency[0] for agency in filter_options['agencies']]
                        selected_agency = st.selectbox("Agency", agency_options)
                        
                        category_options = ["All"] + [category[0] for category in filter_options['categories']]
                        selected_category = st.selectbox("Category", category_options)
                        
                        procurement_method_options = ["All"] + [method[0] for method in filter_options['procurement_methods']]
                        selected_procurement_method = st.selectbox("Procurement Method", procurement_method_options)
                        
                        status_options = ["All"] + [status[0] for status in filter_options['statuses']]
                        selected_status = st.selectbox("Status", status_options)
                        
                        subject_options = ["All"] + [subject[0] for subject in filter_options['subjects']]
                        selected_subject = st.selectbox("Subject", subject_options)
                        
                        # Add vendor file path for contract information
                        vendor_file_path = 'Dropdown_Menu/contract_vendor_list.csv'
                    
                    # Add a searchable vendor selection
                    # Initialize debounce state
                    if 'last_search_time' not in st.session_state:
                        st.session_state.last_search_time = time.time()
                    if 'search_term' not in st.session_state:
                        st.session_state.search_term = ""
                    
                    # Get the current search input
                    current_search = st.text_input(
                        "Search Vendors",
                        help="Type at least 2 characters to search for vendors",
                        placeholder="Type at least 2 characters to search",
                        key="vendor_search"
                    )
                    
                    # Check if we should update the search
                    current_time = time.time()
                    if (current_search != st.session_state.search_term and 
                        len(current_search) >= 2 and 
                        current_time - st.session_state.last_search_time > 0.3):  # 300ms debounce
                        st.session_state.search_term = current_search
                        st.session_state.last_search_time = current_time
                        st.rerun()
                    
                    # Initialize vendor state
                    if 'selected_vendor' not in st.session_state:
                        st.session_state.selected_vendor = None
                    if 'vendor_limit' not in st.session_state:
                        st.session_state.vendor_limit = 50
                    
                    # Get matching vendors based on search input
                    matching_vendors = search_vendors(
                        st.session_state.search_term, 
                        vendor_file_path, 
                        limit=st.session_state.vendor_limit
                    )
                    
                    # Display matching vendors in a selectbox if there are results
                    if matching_vendors:
                        # Create a container for the vendor selection
                        vendor_container = st.container()
                        
                        with vendor_container:
                            # Create the selectbox with current vendors
                            selected_vendor = st.selectbox(
                                "Select Vendor",
                                options=[""] + matching_vendors,  # Add empty option at start
                                index=0 if st.session_state.selected_vendor not in matching_vendors else matching_vendors.index(st.session_state.selected_vendor) + 1,
                                key="vendor_select",
                                help="Select a vendor from the search results"
                            )
                            
                            # Add "Load More" button if there are enough results
                            if len(matching_vendors) >= st.session_state.vendor_limit:
                                if st.button("Load 50 More to the Search List", key="load_more_vendors", help="Load 50 more vendors to the search results"):
                                    # Store current selection before loading more
                                    st.session_state.selected_vendor = selected_vendor
                                    # Increase the limit
                                    st.session_state.vendor_limit += 50
                                    # Force a rerun to update the UI with more vendors
                                    st.rerun()
                            
                            # Update session state with selected vendor
                            if selected_vendor != st.session_state.selected_vendor:
                                st.session_state.selected_vendor = selected_vendor
                    
                    # Store the selected vendor in the filters
                    st.session_state.filters['vendor'] = [st.session_state.selected_vendor] if st.session_state.selected_vendor else []

                with col2:
                    # Create a fixed position container for query actions
                    st.markdown("""
                        <style>
                        .fixed-query-container {
                            position: sticky;
                            top: 2rem;
                            padding: 1rem;
                            border-radius: 0.5rem;
                            z-index: 100;
                        }
                        .query-content {
                            display: flex;
                            flex-direction: column;
                            gap: 1rem;
                        }
                        div[data-testid="stButton"] {
                            display: flex;
                            justify-content: center;
                            margin: 0.5rem 0;
                        }
                        </style>
                        <div class="fixed-query-container">
                            <div class="query-content">
                    """, unsafe_allow_html=True)
                    
                    logger.info("Setting up query actions")
                    st.subheader("Query Actions")
                    
                    submit_clicked = st.button("Submit Query", use_container_width=True)
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
                    
                    st.markdown("</div></div>", unsafe_allow_html=True)

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
                    # Create a container for the loading animation
                    loading_container = st.empty()
                    
                    # Get database connection with spinner
                    with loading_container.container():
                        with st.spinner('Connecting to database...'):
                            engine = get_db_connection()
                            logger.info("Database connection established")
                    
                    # Get filtered data using the query utilities with spinner
                    with loading_container.container():
                        with st.spinner('Executing query... This may take a few moments.'):
                            logger.info("Calling get_filtered_data with:")
                            logger.info(f"- filters: {filter_payload}")
                            logger.info(f"- table_choice: {table_choice}")
                            logger.info(f"- engine: {engine}")
                            
                            df = get_filtered_data(filter_payload, table_choice, engine)
                    
                    # Clear the loading container
                    loading_container.empty()
                    
                    logger.info(f"Query result type: {type(df)}")
                    logger.info(f"Query result shape: {df.shape if hasattr(df, 'shape') else 'No shape attribute'}")
                    
                    if not df.empty:
                        st.session_state['df'] = df
                        logger.info(f"Retrieved {len(df)} records")
                        
                        # Display results count with a nice animation
                        st.success(f"Found {len(df)} matching records")
                        
                        # Display the dataframe with a loading animation
                        with st.spinner('Loading data...'):
                            st.dataframe(df)
                        
                        # Add CSV download button
                        download_csv(df)
                        
                        # Download button for zip file
                        with st.spinner('Preparing download...'):
                            zip_file = df_to_zip(df)
                            logger.info("Generated zip file for download")
                            st.download_button(
                                label="Download ZIP",
                                data=zip_file,
                                file_name="queried_data.zip",
                                mime="application/zip",
                                help="Click to download the queried data as a ZIP file"
                            )
                    else:
                        logger.info("No data returned from query")
                        st.info("No data returned.")
                        
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"Error processing query: {str(e)}")
                    logger.error(f"Full error traceback:\n{error_details}")
                    
                    # Display detailed error information to the user
                    st.error(f"""
                    Error retrieving data:
                    
                    Error type: {type(e).__name__}
                    Error message: {str(e)}
                    
                    Full error details have been logged.
                    """)
                    
                    # If it's a database error, show more details
                    if hasattr(e, 'orig'):
                        st.error(f"""
                        Database error details:
                        {str(e.orig)}
                        """)

            # Add visualization section
            logger.info("Adding visualization section")
            st.markdown("---")  # Add a separator
            st.header("Visualizations")
            
            if 'df' in st.session_state and not st.session_state['df'].empty:
                try:
                    # Generate all visualizations
                    visualizations = generate_all_visualizations(st.session_state['df'])
                    
                    # Create two columns for visualizations
                    viz_col1, viz_col2 = st.columns(2)
                    
                    with viz_col1:
                        st.subheader("Payment Distribution")
                        st.altair_chart(visualizations['payment_distribution'], use_container_width=True)
                        
                        st.subheader("Top Vendors")
                        st.altair_chart(visualizations['vendor_analysis'], use_container_width=True)
                        
                    with viz_col2:
                        st.subheader("Trend Analysis")
                        st.altair_chart(visualizations['trend_analysis'], use_container_width=True)
                        
                        st.subheader("Category Distribution")
                        st.altair_chart(visualizations['category_analysis'], use_container_width=True)
                        
                except Exception as e:
                    logger.error(f"Error displaying visualizations: {str(e)}", exc_info=True)
                    st.error("Error generating visualizations. Please check the data format.")
            else:
                st.info("Submit a query to see visualizations of the data.")

            # Add AI Analysis section
            logger.info("Adding AI Analysis section")
            st.header("AI Analysis")
            st.info("AI-powered analysis and insights will appear here.")
            st.markdown("---")

            # Add logos section
            logger.info("Adding logos section")
            try:
                # Responsive side-by-side clickable logos with improved flexbox layout
                logo_path = os.path.join(os.path.dirname(__file__), "Texas DOGE_White.png")
                doge_img_html = ""
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as image_file:
                        encoded = base64.b64encode(image_file.read()).decode()
                    doge_img_html = (
                        f'<div class="logo-item">'
                        f'<a href="https://house.texas.gov/committees/committee/233" target="_blank">'
                        f'<img src="data:image/png;base64,{encoded}" alt="DOGE Logo"/></a></div>'
                    )
                svg_path = os.path.join(os.path.dirname(__file__), "Texas_House_Logo.svg")
                svg_img_html = ""
                if os.path.exists(svg_path):
                    with open(svg_path, "r") as svg_file:
                        svg_content = svg_file.read()
                    svg_img_html = (
                        f'<div class="logo-item">'
                        f'<a href="https://house.texas.gov/" target="_blank">{svg_content}</a></div>'
                    )
                if doge_img_html or svg_img_html:
                    st.markdown(
                        f"""
                        <style>
                        .logo-flex-container {{
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            gap: 2vw;
                            flex-wrap: wrap;
                            margin-top: 2em;
                        }}
                        .logo-item {{
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            min-width: 120px;
                            max-width: 25vw;
                        }}
                        .logo-item img, .logo-item svg {{
                            width: 100%;
                            height: auto;
                            max-width: 200px;
                        }}
                        @media (max-width: 600px) {{
                            .logo-flex-container {{
                                flex-direction: column;
                            }}
                            .logo-item {{
                                max-width: 60vw;
                            }}
                        }}
                        .find-x-container {{
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            gap: 0.5em;
                            margin-top: 2em;
                            font-size: 1.2em;
                        }}
                        .x-logo-img {{
                            width: 32px;
                            height: 32px;
                            vertical-align: middle;
                        }}
                        </style>
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
                        x_logo_html = f'<a href="https://x.com/TxLegeDOGE" target="_blank"><img src="data:image/png;base64,{x_encoded}" class="x-logo-img" alt="X Logo"/></a>'
                    st.markdown(
                        f'<div class="find-x-container">Find us on {x_logo_html}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("---")
                    st.markdown("### Texas Department of Government Efficiency")
                    st.warning("Logo file (Texas DOGE_White.png) or SVG file (Texas_House_Logo.svg) not found.")
            except Exception as e:
                st.markdown("---")
                st.markdown("### Texas Department of Government Efficiency")
                st.error(f"Error loading logo: {str(e)}")
                logger.error(f"Error in logos section: {str(e)}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error in main content: {str(e)}")
            st.error("Error displaying main content. Please refresh the page.")
            return
            
    except Exception as e:
        logger.critical(f"Critical error in main function: {str(e)}", exc_info=True)
        st.error("A critical error occurred. Please refresh the page or contact support.")
        return

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please try again later.")
        raise