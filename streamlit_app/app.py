# dashboard.py
import streamlit as st
import requests
import pandas as pd
import io
import zipfile
from PIL import Image
import os
from dotenv import load_dotenv
from logger_config import get_logger
import secrets
from datetime import timedelta
import psutil
import platform

# Additional imports for advanced visualizations
import numpy as np
import altair as alt
import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import streamlit.components.v1 as components
import base64

# Initialize logger
logger = get_logger('app')

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Security configurations
def configure_security():
    """Configure security settings for the Streamlit app"""
    logger.info("Configuring security settings")
    
    # Configure session state with secure defaults
    if 'session_id' not in st.session_state:
        st.session_state.session_id = secrets.token_urlsafe(32)
    
    # Set session expiry (24 hours)
    if 'session_start' not in st.session_state:
        st.session_state.session_start = pd.Timestamp.now()
    
    # Check session expiry
    if pd.Timestamp.now() - st.session_state.session_start > timedelta(hours=24):
        logger.warning("Session expired, clearing session state")
        st.session_state.clear()
        st.session_state.session_id = secrets.token_urlsafe(32)
        st.session_state.session_start = pd.Timestamp.now()
    
    # Configure Streamlit security settings
    st.set_page_config(
        page_title="Texas Treasury Query",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Add security headers
    st.markdown("""
        <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';">
        <meta http-equiv="X-Content-Type-Options" content="nosniff">
        <meta http-equiv="X-Frame-Options" content="DENY">
        <meta http-equiv="X-XSS-Protection" content="1; mode=block">
    """, unsafe_allow_html=True)

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
        if api_key:
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
        raise

# Get API URL from environment variable with fallback
API_URL = os.getenv('API_URL', 'http://127.0.0.1:5000')
logger.info(f"Using API URL: {API_URL}")

# Mock data for testing
MOCK_FILTER_OPTIONS = {
    'departments': [
        'Department of Education',
        'Department of Health',
        'Department of Transportation',
        'Department of Public Safety',
        'Department of Administration'
    ],
    'agencies': [
        'Attorney General',
        'Office of the Governor',
        'Texas Education Agency',
        'Texas Health and Human Services',
        'Texas Department of Transportation'
    ],
    'vendors': [
        'Texas A&M University',
        'University of Texas',
        'Dell Medical School',
        'Texas Children\'s Hospital',
        'H-E-B',
        'Dell Inc.'
    ],
    'appropriation_titles': [
        'General Revenue Fund',
        'Education Trust Fund',
        'Highway Fund',
        'Health and Human Services Fund',
        'Public Safety Fund'
    ],
    'fiscal_years': ['2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023']
}

# Mock data for testing the filter endpoint
MOCK_DATA = pd.DataFrame({
    'DEPARTMENT': ['Department of Education', 'Department of Health', 'Department of Transportation', 'Department of Public Safety', 'Department of Administration'] * 20,
    'AGENCY': ['Attorney General', 'Office of the Governor', 'Texas Education Agency', 'Texas Health and Human Services', 'Texas Department of Transportation'] * 20,
    'VENDOR': ['Texas A&M University', 'University of Texas', 'Dell Medical School', 'Texas Children\'s Hospital', 'H-E-B'] * 20,
    'APPROPRIATION_TITLE': ['General Revenue Fund', 'Education Trust Fund', 'Highway Fund', 'Health and Human Services Fund', 'Public Safety Fund'] * 20,
    'FISCAL_YEAR': ['2022', '2022', '2021', '2021', '2023'] * 20,
    'DATE': pd.date_range(start='2021-01-01', periods=100, freq='D'),
    'PRICE': np.random.uniform(1000, 1000000, 100)
})

def get_filter_options():
    """Get filter options - using mock data for now"""
    logger.info("Retrieving filter options")
    return MOCK_FILTER_OPTIONS

def get_filtered_data(filters):
    """Get filtered data - using mock data for now"""
    logger.info(f"Filtering data with filters: {filters}")
    df = MOCK_DATA.copy()
    # Apply filters
    if filters.get('department'):
        df = df[df['DEPARTMENT'] == filters['department']]
    if filters.get('agency'):
        df = df[df['AGENCY'] == filters['agency']]
    if filters.get('vendor'):
        df = df[df['VENDOR'] == filters['vendor']]
    if filters.get('appropriation_title'):
        df = df[df['APPROPRIATION_TITLE'] == filters['appropriation_title']]
    if filters.get('fiscal_year'):
        df = df[df['FISCAL_YEAR'] == filters['fiscal_year']]
    if filters.get('date_start'):
        date_start = pd.to_datetime(filters['date_start'])
        df = df[df['DATE'] >= date_start]
    if filters.get('date_end'):
        date_end = pd.to_datetime(filters['date_end'])
        df = df[df['DATE'] <= date_end]
    if filters.get('min_price'):
        df = df[df['PRICE'] >= filters['min_price']]
    if filters.get('max_price'):
        df = df[df['PRICE'] <= filters['max_price']]
    logger.info(f"Filtered data contains {len(df)} records")
    return df.to_dict('records')

def df_to_zip(df):
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('data.csv', csv_bytes)
    buffer.seek(0)
    return buffer.getvalue()


def draw_network_plotly(df, filter_method="none"):
    # Create a bipartite graph
    B = nx.Graph()
    vendor_nodes = list(df['VENDOR'].unique())
    agency_nodes = list(df['AGENCY'].unique())
    B.add_nodes_from(vendor_nodes, bipartite=0, label='Vendor')
    B.add_nodes_from(agency_nodes, bipartite=1, label='Agency')

    # Add weighted edges between vendors and agencies
    edges_df = df.groupby(['VENDOR', 'AGENCY']).size().reset_index(name='COUNT')
    for _, row in edges_df.iterrows():
        B.add_edge(row['VENDOR'], row['AGENCY'], weight=row['COUNT'])

    # Compute layout using spring layout
    pos = nx.spring_layout(B, seed=42)

    # Apply filtering if desired
    if filter_method == "top_count_25":
        # Select top 25 vendors by degree (only considering vendor nodes)
        vendor_degrees = {v: B.degree(v) for v in vendor_nodes}
        sorted_vendors = sorted(vendor_degrees.items(), key=lambda x: x[1], reverse=True)
        top25_vendors = [v for v, d in sorted_vendors[:25]]
        # Filter edges: include edge if at least one endpoint (that is a vendor) is in top25_vendors
        filtered_edges = []
        for u, v, d in B.edges(data=True):
            if (B.nodes[u]['bipartite'] == 0 and u in top25_vendors) or (
                    B.nodes[v]['bipartite'] == 0 and v in top25_vendors):
                filtered_edges.append((u, v, d))
        # Collect nodes from these filtered edges
        filtered_vendors = set()
        filtered_agencies = set()
        for u, v, d in filtered_edges:
            if B.nodes[u]['bipartite'] == 0:
                filtered_vendors.add(u)
            if B.nodes[v]['bipartite'] == 0:
                filtered_vendors.add(v)
            if B.nodes[u]['bipartite'] == 1:
                filtered_agencies.add(u)
            if B.nodes[v]['bipartite'] == 1:
                filtered_agencies.add(v)
        B_filtered = nx.Graph()
        B_filtered.add_nodes_from(filtered_vendors, bipartite=0, label='Vendor')
        B_filtered.add_nodes_from(filtered_agencies, bipartite=1, label='Agency')
        for u, v, d in filtered_edges:
            B_filtered.add_edge(u, v, weight=d['weight'])
        B = B_filtered
        pos = nx.spring_layout(B, seed=42)

    # Create edge trace
    edge_x, edge_y = [], []
    for edge in B.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # Create node trace
    node_x, node_y, node_text, node_color = [], [], [], []
    for node in B.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{node} (Degree: {B.degree(node)})")
        # Differentiate vendors and agencies by color
        if B.nodes[node]['bipartite'] == 0:
            node_color.append('skyblue')
        else:
            node_color.append('lightgreen')

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=[node for node in B.nodes()],
        textposition="top center",
        hovertext=node_text,
        marker=dict(
            showscale=False,
            color=node_color,
            size=10,
            line_width=2
        )
    )

    # Create the figure
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title={
                            'text': '<b>Top 25 Most Connected Vendors</b>',
                            'font': {'size': 16}
                        },
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                    )
                    )
    return fig

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

def main():
    # Configure security settings
    configure_security()
    
    logger.info("Starting application")
    
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
        st.stop()

    st.title("Query the Texas Treasury")
    st.subheader("Committee on the Delivery of Government Efficiency")

    # Create columns for the filter interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Filter Criteria")
        
        # Initialize session state for filters if not exists
        if 'filters' not in st.session_state:
            st.session_state.filters = {
                'department': None,
                'agency': None,
                'vendor': None,
                'appropriation_title': None,
                'fiscal_year': None,
                'date_start': None,
                'date_end': None,
                'min_price': None,
                'max_price': None
            }
        
        try:
            # Get filter options using mock data
            filter_options = get_filter_options()
            
            # Department Filter
            departments = filter_options.get('departments', [])
            st.session_state.filters['department'] = st.selectbox(
                "Department",
                options=['All'] + departments,
                index=0
            )
            # Agency Filter
            agencies = filter_options.get('agencies', [])
            st.session_state.filters['agency'] = st.selectbox(
                "Agency",
                options=['All'] + agencies,
                index=0
            )
            # Vendor Filter
            vendors = filter_options.get('vendors', [])
            st.session_state.filters['vendor'] = st.selectbox(
                "Vendor",
                options=['All'] + vendors,
                index=0
            )
            # Appropriation Title Filter
            appropriation_titles = filter_options.get('appropriation_titles', [])
            st.session_state.filters['appropriation_title'] = st.selectbox(
                "Appropriation Title",
                options=['All'] + appropriation_titles,
                index=0
            )
            # Fiscal Year Filter
            fiscal_years = filter_options.get('fiscal_years', [])
            st.session_state.filters['fiscal_year'] = st.selectbox(
                "Fiscal Year",
                options=['All'] + fiscal_years,
                index=0
            )
            # Date Range Filter
            date_range = st.date_input(
                "Date Range",
                value=(MOCK_DATA['DATE'].min(), MOCK_DATA['DATE'].max())
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                st.session_state.filters['date_start'] = date_range[0]
                st.session_state.filters['date_end'] = date_range[1]
            # Price Range Filter
            col_price1, col_price2 = st.columns(2)
            with col_price1:
                st.session_state.filters['min_price'] = st.number_input(
                    "Minimum Price",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0
                )
            with col_price2:
                st.session_state.filters['max_price'] = st.number_input(
                    "Maximum Price",
                    min_value=0.0,
                    value=1000000.0,
                    step=1000.0
                )
        except Exception as e:
            st.error(f"Error loading filter options: {e}")
            return

    with col2:
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
                3. Set minimum and maximum amounts to filter by payment size
                4. Click 'Submit Query' to view the results
                5. Download the results using the download button
                
                ### Data Fields
                - **Fiscal Year**: The fiscal year of the payment
                - **Agency**: The government agency making the payment
                - **Payee**: The recipient of the payment
                - **Expenditure Category**: The category of expenditure
                - **Appropriated Fund**: The fund from which the payment was made
                - **Comptroller Object**: The comptroller object code
                - **Payment Month**: The month of the payment
                - **Amount Range**: Filter payments by amount
                
                Note: This is currently using mock data for demonstration purposes.
                """)

    if submit_clicked:
        logger.info("Query submitted")
        # Prepare and validate the filter payload
        filter_payload = {
            k: validate_input(v) 
            for k, v in st.session_state.filters.items() 
            if v != 'All' and v is not None
        }
        logger.info(f"Filter payload: {filter_payload}")
        
        try:
            # Get filtered data using mock data (to be replaced with API call)
            data = get_filtered_data(filter_payload)
            
            if data:
                df = pd.DataFrame(data)
                # Sanitize column names
                df.columns = [validate_input(col) for col in df.columns]
                st.session_state['df'] = df
                logger.info(f"Retrieved {len(df)} records")
                
                # Display results count
                st.success(f"Found {len(df)} matching records")
                
                # Display the dataframe
                st.dataframe(df)
                
                # Download button
                zip_file = df_to_zip(df)
                logger.info("Generated zip file for download")
                st.download_button(
                    label="Download Results",
                    data=zip_file,
                    file_name="queried_data.zip",
                    mime="application/zip"
                )
                
                # Continue with visualizations
                try:
                    logger.info("Generating visualizations")
                    st.write("Debug - Available columns:", df.columns.tolist())
                    
                    if 'DATE' in df.columns:
                        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
                        st.write("Debug - DATE column processed")
                    else:
                        st.error("DATE column not found in data")

                    if 'PRICE' in df.columns:
                        df['PRICE'] = pd.to_numeric(df['PRICE'], errors='coerce')
                        st.write("Debug - PRICE column processed")
                    else:
                        st.error("PRICE column not found in data")

                    st.header("Visualizations")

                    #######################################
                    # 1. Temporal Trend & Anomaly Detection
                    #######################################
                    st.subheader("Payment Trends")
                    df_time = df.groupby('DATE')['PRICE'].sum().reset_index()
                    mean_amount = df_time['PRICE'].mean()
                    std_amount = df_time['PRICE'].std()
                    threshold = mean_amount + 2 * std_amount
                    df_time['anomaly'] = df_time['PRICE'] > threshold

                    line_chart = alt.Chart(df_time).mark_line().encode(
                        x=alt.X('DATE:T', title='Payment Date'),
                        y=alt.Y('PRICE:Q', title='Total Payment Amount')
                    ).properties(width=700, height=300)

                    anomaly_points = alt.Chart(df_time[df_time['anomaly']]).mark_point(color='red', size=100).encode(
                        x='DATE:T',
                        y='PRICE:Q'
                    )

                    st.altair_chart(line_chart + anomaly_points, use_container_width=True)
                    st.markdown(
                        f"**Mean:** {mean_amount:.2f} | **Standard Deviation:** {std_amount:.2f} | **Anomaly Threshold:** {threshold:.2f}")

                    #################################################
                    # 2. Network Graph: Relationships between Vendors and Agencies
                    #################################################
                    if 'df' in st.session_state:
                        df = st.session_state['df']
                        st.subheader("Relationship between Agencies and Vendors")

                        fig_network = draw_network_plotly(df, filter_method="top_count_25")
                        st.plotly_chart(fig_network, use_container_width=True)

                    #################################################
                    # 3. Payment Amount Distribution (Box Plot)
                    #################################################
                    st.subheader("Payment Amount Distribution")
                    fig = px.box(df, x="VENDOR", y="PRICE",
                                points="all",
                                title="",
                                labels={"VENDOR": "Vendor", "PRICE": "Payment Amount"})
                    fig.update_xaxes(showticklabels=False, title_text="")
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as viz_error:
                    logger.error(f"Error creating visualizations: {str(viz_error)}", exc_info=True)
                    st.error(f"Error creating visualizations: {str(viz_error)}")
                    st.info("Please check that your data contains the required columns: DATE, PRICE, VENDOR, and AGENCY")

            elif isinstance(data, list) and not data:
                logger.info("No data returned from query")
                st.info("No data returned.")
            else:
                logger.warning(f"Unexpected data type returned: {type(data)}")
                st.write(data)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            st.error(f"Error calling API: {e}")

    # Add AI Analysis placeholder section
    st.header("AI Analysis")
    st.info("AI-powered analysis and insights will appear here.")
    st.markdown("---")

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
            x_logo_path = os.path.join(os.path.dirname(__file__), "X_logo.png")
            x_logo_html = ""
            if os.path.exists(x_logo_path):
                with open(x_logo_path, "rb") as x_img_file:
                    x_encoded = base64.b64encode(x_img_file.read()).decode()
                x_logo_html = f'<a href="https://x.com/TxLegeDOGE" target="_blank"><img src="data:image/png;base64,{x_encoded}" class="x-logo-img" alt="X Logo"/></a>'
            st.markdown(
                f'<div class="find-x-container">Find us on X {x_logo_html}</div>',
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


if __name__ == "__main__":
    try:
        # Add psutil to requirements if not already present
        main()
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please try again later.")
        raise