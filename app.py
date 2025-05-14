# dashboard.py
import streamlit as st
import requests
import pandas as pd
import io
import zipfile
from PIL import Image
import os

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

API_URL = "http://127.0.0.1:5000"  # Adjust if your Flask runs elsewhere

# Mock data for testing
MOCK_FILTER_OPTIONS = {
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
    'AGENCY': ['Attorney General', 'Office of the Governor', 'Texas Education Agency', 'Texas Health and Human Services', 'Texas Department of Transportation'] * 20,
    'VENDOR': ['Texas A&M University', 'University of Texas', 'Dell Medical School', 'Texas Children\'s Hospital', 'H-E-B'] * 20,
    'APPROPRIATION_TITLE': ['General Revenue Fund', 'Education Trust Fund', 'Highway Fund', 'Health and Human Services Fund', 'Public Safety Fund'] * 20,
    'FISCAL_YEAR': ['2022', '2022', '2021', '2021', '2023'] * 20,
    'DATE': pd.date_range(start='2021-01-01', periods=100, freq='D'),
    'PRICE': np.random.uniform(1000, 1000000, 100)
})

def get_filter_options():
    """Get filter options - using mock data for now"""
    return MOCK_FILTER_OPTIONS

def get_filtered_data(filters):
    """Get filtered data - using mock data for now"""
    df = MOCK_DATA.copy()
    # Apply filters
    if filters.get('agency'):
        df = df[df['AGENCY'] == filters['agency']]
    if filters.get('vendor'):
        df = df[df['VENDOR'] == filters['vendor']]
    if filters.get('appropriation_title'):
        df = df[df['APPROPRIATION_TITLE'] == filters['appropriation_title']]
    if filters.get('fiscal_year'):
        df = df[df['FISCAL_YEAR'] == filters['fiscal_year']]
    if filters.get('date_start'):
        df = df[df['DATE'] >= pd.to_datetime(filters['date_start'])]
    if filters.get('date_end'):
        df = df[df['DATE'] <= pd.to_datetime(filters['date_end'])]
    if filters.get('min_price'):
        df = df[df['PRICE'] >= filters['min_price']]
    if filters.get('max_price'):
        df = df[df['PRICE'] <= filters['max_price']]
    return df.to_dict('records')

def df_to_zip(df: pd.DataFrame) -> bytes:
    """Return a ZIP-in-memory containing the dataframe as CSV."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("results.csv", df.to_csv(index=False))
    buffer.seek(0)
    return buffer.read()


def draw_network_plotly(df, filter_method="none"):
    # Create a bipartite graph
    B = nx.Graph()
    payee_nodes = list(df['PAYEE'].unique())
    agency_nodes = list(df['AGENCY'].unique())
    B.add_nodes_from(payee_nodes, bipartite=0, label='Payee')
    B.add_nodes_from(agency_nodes, bipartite=1, label='Agency')

    # Add weighted edges between payees and agencies
    edges_df = df.groupby(['PAYEE', 'AGENCY']).size().reset_index(name='COUNT')
    for _, row in edges_df.iterrows():
        B.add_edge(row['PAYEE'], row['AGENCY'], weight=row['COUNT'])

    # Compute layout using spring layout
    pos = nx.spring_layout(B, seed=42)

    # Apply filtering if desired
    if filter_method == "top_count_25":
        # Select top 25 payees by degree (only considering payee nodes)
        payee_degrees = {p: B.degree(p) for p in payee_nodes}
        sorted_payees = sorted(payee_degrees.items(), key=lambda x: x[1], reverse=True)
        top25_payees = [p for p, d in sorted_payees[:25]]
        # Filter edges: include edge if at least one endpoint (that is a payee) is in top25_payees.
        filtered_edges = []
        for u, v, d in B.edges(data=True):
            if (B.nodes[u]['bipartite'] == 0 and u in top25_payees) or (
                    B.nodes[v]['bipartite'] == 0 and v in top25_payees):
                filtered_edges.append((u, v, d))
        # Collect nodes from these filtered edges
        filtered_payees = set()
        filtered_agencies = set()
        for u, v, d in filtered_edges:
            if B.nodes[u]['bipartite'] == 0:
                filtered_payees.add(u)
            if B.nodes[v]['bipartite'] == 0:
                filtered_payees.add(v)
            if B.nodes[u]['bipartite'] == 1:
                filtered_agencies.add(u)
            if B.nodes[v]['bipartite'] == 1:
                filtered_agencies.add(v)
        B_filtered = nx.Graph()
        B_filtered.add_nodes_from(filtered_payees, bipartite=0, label='Payee')
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
        # Differentiate payees and agencies by color
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
                            'text': '<b>Top 25 Most Connected Payees</b>',
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


def main():
    # Privacy statement modal/checkbox
    if 'privacy_accepted' not in st.session_state:
        st.session_state['privacy_accepted'] = False

    if not st.session_state['privacy_accepted']:
        st.markdown("""
        ## Privacy Statement
        By using this application, you acknowledge and accept that the queries you make may be recorded for research, quality assurance, or improvement purposes.
        """)
        if st.button("I Accept the Privacy Statement"):
            st.session_state['privacy_accepted'] = True
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
        # Prepare the filter payload
        filter_payload = {k: v for k, v in st.session_state.filters.items() if v != 'All' and v is not None}
        
        try:
            # Get filtered data using mock data
            data = get_filtered_data(filter_payload)
            
            if data:
                df = pd.DataFrame(data)
                st.session_state['df'] = df
                
                # Display results count
                st.success(f"Found {len(df)} matching records")
                
                # Display the dataframe
                st.dataframe(df)
                
                # Download CSV button
                st.download_button(
                    "Download CSV",
                    data=df_to_zip(df),
                    file_name="treasury_results.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
                
                # Placeholder for graphs and visualizations
                st.markdown("---")
                st.header("Visualizations & Graphs")
                if not df.empty:
                    st.subheader("Create a Graph")
                    graph_type = st.selectbox("Select graph type", ["Bar", "Histogram", "Line"])
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    all_cols = df.columns.tolist()
                    x_col = st.selectbox("X-axis", all_cols, index=0)
                    y_col = None
                    if graph_type in ["Bar", "Line"]:
                        y_col = st.selectbox("Y-axis", numeric_cols, index=0 if numeric_cols else None)
                    if graph_type == "Bar" and y_col:
                        fig = px.bar(df, x=x_col, y=y_col, title=f"Bar Graph of {y_col} by {x_col}")
                        st.plotly_chart(fig, use_container_width=True)
                    elif graph_type == "Histogram":
                        hist_col = st.selectbox("Column for Histogram", numeric_cols, index=0 if numeric_cols else None)
                        fig = px.histogram(df, x=hist_col, title=f"Histogram of {hist_col}")
                        st.plotly_chart(fig, use_container_width=True)
                    elif graph_type == "Line" and y_col:
                        fig = px.line(df, x=x_col, y=y_col, title=f"Line Graph of {y_col} by {x_col}")
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Graphs and visualizations will appear here.")
                st.markdown("---")
                
                # Continue with visualizations as before...
                if 'PAYMENT_DATE' in df.columns:
                    df['PAYMENT_DATE'] = pd.to_datetime(df['PAYMENT_DATE'], errors='coerce')

                if 'PAYMENT_AMOUNT' in df.columns:
                    df['PAYMENT_AMOUNT'] = pd.to_numeric(df['PAYMENT_AMOUNT'], errors='coerce')

                st.header("Visualizations")

                #######################################
                # 1. Temporal Trend & Anomaly Detection
                #######################################
                st.subheader("Payment Trends")
                df_time = df.groupby('PAYMENT_DATE')['PAYMENT_AMOUNT'].sum().reset_index()
                mean_amount = df_time['PAYMENT_AMOUNT'].mean()
                std_amount = df_time['PAYMENT_AMOUNT'].std()
                threshold = mean_amount + 2 * std_amount
                df_time['anomaly'] = df_time['PAYMENT_AMOUNT'] > threshold

                line_chart = alt.Chart(df_time).mark_line().encode(
                    x=alt.X('PAYMENT_DATE:T', title='Payment Date'),
                    y=alt.Y('PAYMENT_AMOUNT:Q', title='Total Payment Amount')
                ).properties(width=700, height=300)

                anomaly_points = alt.Chart(df_time[df_time['anomaly']]).mark_point(color='red', size=100).encode(
                    x='PAYMENT_DATE:T',
                    y='PAYMENT_AMOUNT:Q'
                )

                st.altair_chart(line_chart + anomaly_points, use_container_width=True)
                st.markdown(
                    f"**Mean:** {mean_amount:.2f} | **Standard Deviation:** {std_amount:.2f} | **Anomaly Threshold:** {threshold:.2f}")

                #################################################
                # 2. Network Graph: Relationships between Payees and Agencies
                #################################################
                if 'df' in st.session_state:
                    df = st.session_state['df']
                    st.subheader("Relationship between Agencies and Payees")

                    fig_network = draw_network_plotly(df, filter_method="top_count_25")
                    st.plotly_chart(fig_network, use_container_width=True)

                #################################################
                # 3. Payment Amount Distribution (Box Plot)
                #################################################
                st.subheader("Payment Amount Distribution")
                fig = px.box(df, x="PAYEE", y="PAYMENT_AMOUNT",
                             points="all",
                             title="",
                             labels={"PAYEE": "Payee", "PAYMENT_AMOUNT": "Payment Amount"})
                fig.update_xaxes(showticklabels=False, title_text="")
                st.plotly_chart(fig, use_container_width=True)

            elif isinstance(data, list) and not data:
                st.info("No data returned.")
            else:
                st.write(data)
        except Exception as e:
            st.error(f"Error calling API: {e}")

    # Always show the Visualizations & Graphs placeholder above the logos
    st.markdown("---")
    st.header("Visualizations & Graphs")
    st.info("Graphs and visualizations will appear here.")
    st.markdown("---")

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
        svg_path = "/Users/madalyn_nguyen/streamlit_app/Texas_House_Logo.svg"
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


if __name__ == "__main__":
    main()