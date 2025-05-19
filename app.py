# Standard library imports
import io
import json
import os
import platform
import secrets
import sys
import time
import zipfile
from datetime import timedelta

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
from query_utils import get_filtered_data

# Additional imports for visualizations
import numpy as np
import altair as alt
from datetime import datetime
import streamlit.components.v1 as components
import base64

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
        from db_config import get_db_connection
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

def get_filtered_data(filters, table_choice):
    """Get filtered data from database"""
    logger.info(f"Filtering data with filters: {filters} from table: {table_choice}")
    try:
        from db_config import get_db_connection
        engine = get_db_connection()
        
        # Determine which table to query based on selection
        main_table = "paymentinformation" if table_choice == "Payment Information" else "contractinfo"
        
        # Build the base query
        query = text(f"""
            SELECT p.*, c.*, m.*
            FROM {main_table} p
            LEFT JOIN contractinfo c ON p.payment_id = c.payment_id
            LEFT JOIN mergedinfo m ON p.payment_id = m.payment_id
            WHERE 1=1
        """)
        
        params = {}
        
        # Add filters to query
        if filters.get('Agency'):
            query = text(str(query) + " AND p.agency_name = :agency")
            params['agency'] = filters['agency']
        
        if filters.get('vendor'):
            query = text(str(query) + " AND p.vendor_name = :vendor")
            params['vendor'] = filters['vendor']
        
        if filters.get('appropriation_title'):
            query = text(str(query) + " AND p.appropriation_title = :appropriation_title")
            params['appropriation_title'] = filters['appropriation_title']
        
        if filters.get('fiscal_year'):
            query = text(str(query) + " AND p.fiscal_year = :fiscal_year")
            params['fiscal_year'] = filters['fiscal_year']
        
        if filters.get('date_start'):
            query = text(str(query) + " AND p.payment_date >= :date_start")
            params['date_start'] = filters['date_start']
        
        if filters.get('date_end'):
            query = text(str(query) + " AND p.payment_date <= :date_end")
            params['date_end'] = filters['date_end']
        
        if filters.get('min_price'):
            query = text(str(query) + " AND p.amount >= :min_price")
            params['min_price'] = filters['min_price']
        
        if filters.get('max_price'):
            query = text(str(query) + " AND p.amount <= :max_price")
            params['max_price'] = filters['max_price']
        
        # Execute query with chunking
        all_data = []
        chunk_size = 100
        offset = 0
        
        with engine.connect() as connection:
            while True:
                # Add LIMIT and OFFSET to the query
                chunk_query = text(str(query) + f" LIMIT {chunk_size} OFFSET {offset}")
                result = connection.execute(chunk_query, params)
                chunk_data = [dict(row) for row in result]
                
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
        logger.error(f"Error getting filtered data: {str(e)}", exc_info=True)
        st.error(f"Error retrieving data: {str(e)}")
        return []

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
            'timestamp': pd.Timestamp.now().isoformat(),
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
            'timestamp': pd.Timestamp.now().isoformat()
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
            'timestamp': pd.Timestamp.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': pd.Timestamp.now().isoformat()
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
        engine = get_db_connection()
        print("Database connection established successfully!")
        
        # Test query
        query = "SELECT current_timestamp;"
        print(f"Executing test query: {query}")
        with engine.connect() as connection:
            result = connection.execute(text(query))
            timestamp = result.scalar()
            print(f"Query successful! Current timestamp: {timestamp}")
            st.success(f"Database connection successful! Current timestamp: {timestamp}")
            
            # Get and display table columns
            table_columns = get_table_columns()
            st.subheader("Database Table Structure")
            for table, columns in table_columns.items():
                st.write(f"**{table}**")
                df = pd.DataFrame(columns, columns=['Column Name', 'Data Type'])
                st.dataframe(df)
            
    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        print(f"ERROR: {error_msg}")
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

# Add these new functions after the existing imports
from concurrent.futures import ThreadPoolExecutor
import threading

# Add a lock for thread-safe operations
data_lock = threading.Lock()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_csv_data_parallel(file_paths):
    """Load multiple CSV files in parallel"""
    def load_single_file(file_path):
        try:
            return load_csv_data(file_path)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {str(e)}")
            return None

    with ThreadPoolExecutor(max_workers=min(len(file_paths), 4)) as executor:
        results = list(executor.map(load_single_file, file_paths))
    return {path: df for path, df in zip(file_paths, results) if df is not None}

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
                
                # Load all files in parallel
                data_dict = load_csv_data_parallel(file_paths)
                progress_bar.progress(50)
                
                # Process the data
                agencies = process_dropdown_data(data_dict[file_paths[0]], 'AGY_TITLE')
                appropriation_titles = process_dropdown_data(data_dict[file_paths[1]], 'APRO_TITLE')
                payment_sources = process_dropdown_data(data_dict[file_paths[2]], 'FUND_TITLE')
                appropriation_objects = process_dropdown_data(data_dict[file_paths[3]], 'OBJ_TITLE')
                vendors = process_dropdown_data(data_dict[file_paths[4]], 'Ven_NAME')
                
                progress_bar.progress(100)
                
                result = {
                    'agencies': agencies,
                    'appropriation_titles': appropriation_titles,
                    'payment_sources': payment_sources,
                    'appropriation_objects': appropriation_objects,
                    'vendors': vendors
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
                
                # Load all files in parallel
                data_dict = load_csv_data_parallel(file_paths)
                progress_bar.progress(50)
                
                # Process the data
                agencies = process_dropdown_data(data_dict[file_paths[0]], 'Agency')
                categories = process_dropdown_data(data_dict[file_paths[1]], 'Category')
                vendors = process_dropdown_data(data_dict[file_paths[2]], 'Vendor')
                procurement_methods = process_dropdown_data(data_dict[file_paths[3]], 'Procurement Method')
                statuses = process_dropdown_data(data_dict[file_paths[4]], 'Status')
                subjects = process_dropdown_data(data_dict[file_paths[5]], 'Subject')
                
                progress_bar.progress(100)
                
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
        logger.error(f"Error loading filter options: {str(e)}", exc_info=True)
        st.error(f"Error loading filter options: {str(e)}")
        return None

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
    
    # Add loading delay
    with st.spinner('Loading application...'):
        time.sleep(1)  # Wait for 1 second
    logger.info("Loading spinner completed")
    
    # Configure other security settings
    if 'session_id' not in st.session_state:
        st.session_state.session_id = secrets.token_urlsafe(32)
        logger.info("New session ID generated")
    
    # Set session expiry (24 hours)
    if 'session_start' not in st.session_state:
        st.session_state.session_start = pd.Timestamp.now()
        logger.info("Session start time set")
    
    # Check session expiry
    if pd.Timestamp.now() - st.session_state.session_start > timedelta(hours=24):
        logger.warning("Session expired, clearing session state")
        st.session_state.clear()
        st.session_state.session_id = secrets.token_urlsafe(32)
        st.session_state.session_start = pd.Timestamp.now()
    
    # Add security headers
    logger.info("Adding security headers")
    st.markdown("""
        <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';">
        <meta http-equiv="X-Content-Type-Options" content="nosniff">
        <meta http-equiv="X-Frame-Options" content="DENY">
        <meta http-equiv="X-XSS-Protection" content="1; mode=block">
    """, unsafe_allow_html=True)
    
    # Display version in sidebar
    logger.info("Setting up sidebar")
    st.sidebar.title("Database Status")
    st.sidebar.info(f"App Version: {APP_VERSION}")
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

    # Privacy statement modal/checkbox
    logger.info("Checking privacy statement")
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

    logger.info("Displaying main title")
    st.title("Query the Texas Treasury")
    st.subheader("Committee on the Delivery of Government Efficiency")

    # Create columns for the filter interface
    logger.info("Creating filter interface columns")
    col1, col2 = st.columns([1, 1])
    
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
        
        # Fiscal Year Slider
        try:
            logger.info("Attempting to load fiscal years from Dropdown_Menu/fiscal_years_both.csv")
            fiscal_years_df = load_csv_data('Dropdown_Menu/fiscal_years_both.csv')
            
            # Log the columns we found
            logger.info(f"Found columns in fiscal_years_both.csv: {fiscal_years_df.columns.tolist()}")
            
            # Get fiscal years - using the same column for both payment and contract information
            if 'fiscal_year' not in fiscal_years_df.columns:
                raise Exception(f"Column 'fiscal_year' not found. Available columns: {fiscal_years_df.columns.tolist()}")
            
            fiscal_years = sorted([int(year) for year in fiscal_years_df['fiscal_year'].unique()])
            
            if not fiscal_years:
                raise Exception("No fiscal years found in the data")
            
            min_year = min(fiscal_years)
            max_year = max(fiscal_years)
            
            selected_fiscal_year = st.slider(
                "Fiscal Year",
                min_value=min_year,
                max_value=max_year,
                value=(min_year, max_year),
                help="Select a range of fiscal years"
            )
            
            # Store the selected fiscal year range
            st.session_state.filters['fiscal_year_start'] = selected_fiscal_year[0]
            st.session_state.filters['fiscal_year_end'] = selected_fiscal_year[1]
            
        except Exception as e:
            error_msg = f"Error loading fiscal years: {str(e)}"
            logger.error(error_msg, exc_info=True)
            st.error(error_msg)
            st.info("Please check that the file 'Dropdown_Menu/fiscal_years_both.csv' exists and contains the column 'fiscal_year'")
            selected_fiscal_year = (2021, 2023)  # Default range
        
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
            
            vendor_options = ["All"] + [vendor[0] for vendor in filter_options['vendors']]
            selected_vendor = st.selectbox("Vendor", vendor_options)
            
            # Store Payment Information filters
            st.session_state.filters.update({
                'agency': next((agency[1] for agency in filter_options['agencies'] if agency[0] == selected_agency), None) if selected_agency != "All" else None,
                'appropriation_title': next((title[1] for title in filter_options['appropriation_titles'] if title[0] == selected_appropriation), None) if selected_appropriation != "All" else None,
                'payment_source': next((source[1] for source in filter_options['payment_sources'] if source[0] == selected_payment_source), None) if selected_payment_source != "All" else None,
                'appropriation_object': next((obj[1] for obj in filter_options['appropriation_objects'] if obj[0] == selected_appropriation_object), None) if selected_appropriation_object != "All" else None,
                'vendor': next((vendor[1] for vendor in filter_options['vendors'] if vendor[0] == selected_vendor), None) if selected_vendor != "All" else None
            })
        else:
            # Display Contract Information dropdowns
            agency_options = ["All"] + [agency[0] for agency in filter_options['agencies']]
            selected_agency = st.selectbox("Agency", agency_options)
            
            category_options = ["All"] + [category[0] for category in filter_options['categories']]
            selected_category = st.selectbox("Category", category_options)
            
            vendor_options = ["All"] + [vendor[0] for vendor in filter_options['vendors']]
            selected_vendor = st.selectbox("Vendor", vendor_options)
            
            procurement_options = ["All"] + [method[0] for method in filter_options['procurement_methods']]
            selected_procurement = st.selectbox("Procurement Method", procurement_options)
            
            status_options = ["All"] + [status[0] for status in filter_options['statuses']]
            selected_status = st.selectbox("Status", status_options)
            
            subject_options = ["All"] + [subject[0] for subject in filter_options['subjects']]
            selected_subject = st.selectbox("Subject", subject_options)
            
            # Store Contract Information filters
            st.session_state.filters.update({
                'agency': next((agency[1] for agency in filter_options['agencies'] if agency[0] == selected_agency), None) if selected_agency != "All" else None,
                'category': next((category[1] for category in filter_options['categories'] if category[0] == selected_category), None) if selected_category != "All" else None,
                'vendor': next((vendor[1] for vendor in filter_options['vendors'] if vendor[0] == selected_vendor), None) if selected_vendor != "All" else None,
                'procurement_method': next((method[1] for method in filter_options['procurement_methods'] if method[0] == selected_procurement), None) if selected_procurement != "All" else None,
                'status': next((status[1] for status in filter_options['statuses'] if status[0] == selected_status), None) if selected_status != "All" else None,
                'subject': next((subject[1] for subject in filter_options['subjects'] if subject[0] == selected_subject), None) if selected_subject != "All" else None
            })

    with col2:
        logger.info("Setting up query actions")
        st.subheader("Query Actions")
        submit_clicked = st.button("Submit Query")
        readme_clicked = st.button("About")
        
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
                - **Appropriation Title**: The official name of a pot of money that the legislature has set aside for a specific purpose in the budget (e.g., "Highway Maintenance" or "School Nutrition Program"). Think of it as the label on a line in the government's spending plan.
                - **Payment Source (Fund Title)**: The name of the account that actually holds the money. Different funds keep different revenue sources separate, like a "General Fund" for tax revenues or a "Highway Trust Fund" for fuel-tax money, so officials can track where dollars come from and where they should go.
                - **Appropriation Object**: A more detailed category within an appropriation that describes what the money will buy, that is, salaries, office supplies, construction services, travel reimbursements, etc. It's the budget's "line-item" level.
                
                #### Contract Information Categories
                - **Agency**: The government agency managing the contract
                - **Vendor**: The company or entity providing the goods or services
                - **Category**: The general type or classification of the contract
                - **Procurement Method**: How the government chose the vendor for a contract, such as competitive bidding, non-competitive, and whether it is a contract between state agencies. It tells you how the deal was struck.
                - **Status**: The current state of the contract (e.g., active, completed, terminated)
                - **Subject**: A short description of what the contract covers: e.g., repairing a bridge, providing IT support, supplying textbooks, etc. It's the plain-language summary of the job the vendor has been hired to do.
                
                ### Data Fields
                - **Fiscal Year**: The fiscal year of the payment or contract
                - **Fiscal Month**: The month within the fiscal year
                """)

    if submit_clicked:
        logger.info("Query submitted")
        # Prepare and validate the filter payload
        filter_payload = {
            k: validate_input(v) 
            for k, v in st.session_state.filters.items() 
            if v != 'All' and v is not None
        }
        
        # Add test query for WPI agency
        if table_choice == "Payment Information":
            filter_payload['agency'] = "WPI"
            logger.info("Added test query for WPI agency")
        
        logger.info(f"Filter payload: {filter_payload}")
        
        try:
            # Get database connection
            from db_config import get_db_connection
            engine = get_db_connection()
            
            # Get filtered data using the new query utilities
            df = get_filtered_data(filter_payload, table_choice, engine)
            
            if not df.empty:
                st.session_state['df'] = df
                logger.info(f"Retrieved {len(df)} records")
                
                # Display results count
                st.success(f"Found {len(df)} matching records")
                
                # Display the dataframe
                st.dataframe(df)
                
                # Add CSV download button
                download_csv(df)
                
                # Download button for zip file
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
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            st.error(f"Error retrieving data: {str(e)}")

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
    
    logger.info("Main function completed successfully")

if __name__ == "__main__":
    try:
        # Add psutil to requirements if not already present
        main()
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please try again later.")
        raise