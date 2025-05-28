# Texas Treasury Query Application

A robust Streamlit-based web application for querying and analyzing Texas Treasury payment and contract information, deployed on AWS infrastructure with PostgreSQL database backend.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Structure](#data-structure)
- [API Reference](#api-reference)
- [Performance Optimizations](#performance-optimizations)
- [Security](#security)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)

## 🎯 Overview

This application provides an interactive interface to query and analyze data from Texas Treasury operations. It connects to a PostgreSQL database hosted on AWS RDS and provides real-time querying capabilities for payment and contract information with advanced filtering and export functionality.

### Key Benefits
- **Real-time Data Access**: Query live treasury data with instant results
- **Advanced Filtering**: Multi-dimensional filtering across fiscal years, agencies, vendors, and more
- **Scalable Performance**: Optimized for large datasets with efficient pagination
- **Export Capabilities**: Download filtered results in CSV format
- **User-friendly Interface**: Intuitive Streamlit interface for non-technical users
- **Integrated Ai: Ai used for natural language processing and analysis

## ✨ Features

### Data Querying
- **Dual Table Support**: Query both Payment Information and Contract Information tables
- **Dynamic Filtering**:
  - Fiscal Year Range (slider-based selection)
  - Fiscal Month Range (1-12)
  - Agency Name (case-insensitive search)
  - Vendor Name (case-insensitive search)
  - Table-specific filters:
    - **Payment Information**: Appropriation Object filtering
    - **Contract Information**: Category, Procurement Method, Status, and Subject filtering

### Data Display & Export
- **Paginated Results**: Display 150 records per page for optimal performance
- **Sortable Columns**: Click column headers to sort data
- **CSV Export**: Download complete filtered datasets
- **Record Counting**: Approximate counts for large datasets using PostgreSQL statistics
- **Responsive Design**: Mobile-friendly interface

### Performance Features
- **Query Optimization**: Efficient SQL query generation with proper indexing
- **Chunked Processing**: Large datasets processed in manageable chunks
- **Approximate Counting**: Fast record counts using PostgreSQL's `pg_class.reltuples`
- **Connection Pooling**: Efficient database connection management
- **Caching**: Streamlit caching for improved response times

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Browser  │◄──►│  Streamlit App  │◄──►│   PostgreSQL    │
│                 │    │   (EC2 Ubuntu)  │    │   (AWS RDS)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Application    │
                       │  Logs & Config  │
                       └─────────────────┘
```

### Components
- **Frontend**: Streamlit web application
- **Backend**: Python with SQLAlchemy ORM
- **Database**: PostgreSQL on AWS RDS
- **Infrastructure**: AWS EC2 (Ubuntu) for application hosting
- **Environment**: Production deployment with environment variables

## 🔧 Prerequisites

### System Requirements
- **Operating System**: Ubuntu 18.04+ (or compatible Linux distribution)
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended for large datasets)
- **Storage**: 10GB available disk space
- **Network**: Stable internet connection for AWS RDS access

### AWS Requirements
- **EC2 Instance**: t3.medium or larger recommended
- **RDS Instance**: PostgreSQL 12+ with sufficient storage
- **Security Groups**: Properly configured for database access
- **IAM Permissions**: EC2 instance access to RDS if using IAM authentication

## 📦 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd texas-treasury-query-app
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Ubuntu/Linux
# or
venv\Scripts\activate     # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy version:', sqlalchemy.__version__)"
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root directory:

```env
# Database Configuration
DB_HOST=your-rds-endpoint.amazonaws.com
DB_PORT=5432
DB_NAME=treasury_database
DB_USER=your_username
DB_PASSWORD=your_secure_password

# Application Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Performance Tuning
MAX_RECORDS_PER_PAGE=150
QUERY_TIMEOUT=300
CONNECTION_POOL_SIZE=10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=application.log
```

### Database Setup

Ensure your PostgreSQL database contains the required tables:

```sql
-- Verify tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('paymentinformation', 'contractinfo');

-- Check table structure
\d paymentinformation
\d contractinfo
```

### Security Configuration

#### Database Security
- Use strong passwords for database connections
- Enable SSL connections to RDS
- Restrict database access to specific IP ranges
- Regular password rotation policy

#### Application Security
- Keep `.env` file out of version control
- Use IAM roles instead of hardcoded credentials when possible
- Enable AWS CloudTrail for audit logging
- Regular security updates for dependencies

## 🚀 Usage

### Starting the Application

#### Development Mode
```bash
streamlit run app.py
```

#### Production Mode
```bash
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > app.log 2>&1 &
```

### Basic Usage Workflow

1. **Access the Application**
   - Open web browser and navigate to `http://your-server-ip:8501`
   - The application loads with default settings

2. **Select Data Source**
   - Choose between "Payment Information" or "Contract Information" from the dropdown

3. **Apply Filters**
   - **Fiscal Year**: Use the slider to select year range
   - **Fiscal Month**: Select specific months (1-12)
   - **Agency**: Enter full or partial agency name
   - **Vendor**: Enter full or partial vendor name
   - **Additional Filters**: Use table-specific filters as needed

4. **View Results**
   - Results display in paginated format (150 records per page)
   - Use pagination controls to navigate through results
   - Click column headers to sort data

5. **Export Data**
   - Click "Download CSV" button to export filtered results
   - Large datasets are processed in chunks for reliable downloads

### Advanced Usage

#### Complex Filtering Examples

**Example 1: Specific Agency and Year Range**
```
Table: Payment Information
Fiscal Year: 2020-2023
Agency: "Department of Transportation"
```

**Example 2: Contract Analysis**
```
Table: Contract Information
Fiscal Year: 2022-2024
Category: "Professional Services"
Status: "Active"
Procurement Method: "Competitive Sealed Bidding"
```

#### Performance Tips
- Start with broader filters and narrow down results
- Use fiscal year ranges to limit data scope
- Export large datasets during off-peak hours
- Clear browser cache if experiencing slow performance

## 📊 Data Structure

### Payment Information Table (`paymentinformation`)

| Column Name | Data Type | Description | Example |
|-------------|-----------|-------------|---------|
| fiscal_year | INTEGER | Fiscal year of payment | 2023 |
| fiscal_month | INTEGER | Fiscal month (1-12) | 6 |
| agency_title | VARCHAR | Full agency name | "Department of Health Services" |
| vendor_name | VARCHAR | Vendor/contractor name | "ABC Construction Co." |
| object_title | VARCHAR | Appropriation object description | "Professional Services" |
| payment_amount | DECIMAL | Payment amount in USD | 15000.00 |
| payment_date | DATE | Date of payment | 2023-06-15 |

### Contract Information Table (`contractinfo`)

| Column Name | Data Type | Description | Example |
|-------------|-----------|-------------|---------|
| fiscal_year | INTEGER | Contract fiscal year | 2023 |
| fm | INTEGER | Fiscal month | 6 |
| agency | VARCHAR | Agency name | "Department of Transportation" |
| vendor | VARCHAR | Contractor name | "XYZ Engineering LLC" |
| category | VARCHAR | Contract category | "Construction" |
| procurement_method | VARCHAR | Method of procurement | "Competitive Sealed Bidding" |
| status | VARCHAR | Contract status | "Active" |
| subject | VARCHAR | Contract subject/description | "Highway Maintenance Services" |
| contract_value | DECIMAL | Total contract value | 500000.00 |
| start_date | DATE | Contract start date | 2023-01-01 |
| end_date | DATE | Contract end date | 2023-12-31 |

## 🔧 API Reference

### Database Connection Functions

```python
def get_database_connection():
    """
    Establishes connection to PostgreSQL database
    Returns: SQLAlchemy engine object
    """

def execute_query(query, params=None):
    """
    Executes SQL query with optional parameters
    Args:
        query (str): SQL query string
        params (dict): Query parameters
    Returns: pandas.DataFrame
    """

def get_approximate_count(table_name):
    """
    Gets approximate row count for large tables
    Args:
        table_name (str): Name of the table
    Returns: int (approximate count)
    """
```

### Filter Functions

```python
def apply_fiscal_year_filter(query, year_range):
    """
    Applies fiscal year filter to query
    Args:
        query (str): Base SQL query
        year_range (tuple): (start_year, end_year)
    Returns: str (modified query)
    """

def apply_text_filter(query, column, value):
    """
    Applies case-insensitive text filter
    Args:
        query (str): Base SQL query
        column (str): Column name to filter
        value (str): Filter value
    Returns: str (modified query)
    """
```

## ⚡ Performance Optimizations

### Database Optimizations

#### Indexing Strategy
```sql
-- Recommended indexes for optimal performance
CREATE INDEX idx_payment_fiscal_year ON paymentinformation(fiscal_year);
CREATE INDEX idx_payment_agency ON paymentinformation(agency_title);
CREATE INDEX idx_payment_vendor ON paymentinformation(vendor_name);
CREATE INDEX idx_contract_fiscal_year ON contractinfo(fiscal_year);
CREATE INDEX idx_contract_agency ON contractinfo(agency);
CREATE INDEX idx_contract_vendor ON contractinfo(vendor);
```

#### Query Optimization Techniques
- **Limit and Offset**: Pagination implemented with `LIMIT` and `OFFSET`
- **Prepared Statements**: Using parameterized queries to prevent SQL injection
- **Connection Pooling**: Reusing database connections to reduce overhead
- **Selective Columns**: Only fetching required columns to reduce data transfer

### Application Optimizations

#### Caching Strategy
```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_filtered_data(table, filters):
    """Cached function for filtered data retrieval"""
    pass

@st.cache_resource
def init_database_connection():
    """Cached database connection initialization"""
    pass
```

#### Memory Management
- **Chunked Processing**: Large datasets processed in 10,000-record chunks
- **Lazy Loading**: Data loaded only when requested
- **Garbage Collection**: Explicit cleanup of large objects

### Monitoring Performance

#### Key Metrics to Monitor
- **Query Execution Time**: Average time per query
- **Memory Usage**: Application memory consumption
- **Database Connections**: Active connection count
- **Error Rates**: Failed queries and connection errors

#### Performance Benchmarks
- **Small Queries** (< 1,000 records): < 2 seconds
- **Medium Queries** (1,000-10,000 records): < 10 seconds
- **Large Queries** (> 10,000 records): < 30 seconds
- **CSV Export**: < 60 seconds for datasets up to 100,000 records

## 🔒 Security

### Authentication & Authorization
- Currently implements basic access (expand based on requirements)
- Recommended: Integrate with enterprise SSO systems
- Role-based access control for different user types

### Data Protection
- **In Transit**: SSL/TLS encryption for all database connections
- **At Rest**: RDS encryption enabled
- **Application**: Environment variables for sensitive configuration

### Security Best Practices
- Regular security updates for all dependencies
- Input validation and sanitization
- SQL injection prevention through parameterized queries
- Audit logging for all data access

### Compliance Considerations
- Data retention policies
- Access logging and audit trails
- GDPR/privacy compliance for sensitive data
- Regular security assessments

## 📊 Monitoring & Logging

### Application Logging

#### Log Levels and Categories
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('application.log'),
        logging.StreamHandler()
    ]
)

# Usage examples
logger.info("Query executed successfully")
logger.warning("Large dataset detected, using chunked processing")
logger.error("Database connection failed")
```

#### Key Logging Events
- **User Actions**: Query submissions, filter applications, data exports
- **System Events**: Database connections, errors, performance metrics
- **Security Events**: Failed connections, unusual query patterns

### Monitoring Setup

#### System Monitoring
```bash
# Monitor application process
ps aux | grep streamlit

# Monitor memory usage
free -h

# Monitor disk usage
df -h

# Monitor network connections
netstat -an | grep 8501
```

#### Database Monitoring
```sql
-- Monitor active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Monitor slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

### Health Checks

#### Application Health Check
```bash
# Create health check script
curl -f http://localhost:8501 || exit 1
```

#### Database Health Check
```python
def database_health_check():
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Database Connection Issues

**Problem**: Cannot connect to PostgreSQL database
```
Error: could not connect to server: Connection refused
```

**Solutions**:
1. Verify RDS instance is running and accessible
2. Check security group settings
3. Verify database credentials in `.env` file
4. Test connection using `psql` command line tool

```bash
# Test database connection
psql -h your-rds-endpoint.amazonaws.com -U username -d database_name
```

#### Performance Issues

**Problem**: Slow query performance
**Solutions**:
1. Check database indexes are properly created
2. Analyze slow query logs
3. Reduce query scope with more specific filters
4. Monitor system resources (CPU, memory)

**Problem**: Application crashes with large datasets
**Solutions**:
1. Increase EC2 instance memory
2. Adjust `MAX_RECORDS_PER_PAGE` setting
3. Implement more aggressive caching
4. Use chunked processing for exports

#### Streamlit-Specific Issues

**Problem**: Page not loading or showing errors
```bash
# Check Streamlit logs
tail -f app.log

# Restart application
pkill -f streamlit
nohup streamlit run app.py > app.log 2>&1 &
```

**Problem**: Session state issues
- Clear browser cache and cookies
- Restart the Streamlit application
- Check for conflicting browser extensions

### Debug Mode

Enable debug mode for detailed error information:

```python
# Add to app.py for development
import streamlit as st
st.set_page_config(
    page_title="Texas Treasury Query",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enable debug logging
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Log Analysis

#### Common Log Patterns to Monitor
```bash
# Database connection errors
grep "connection" application.log | tail -20

# Query performance issues
grep "slow query" application.log | tail -20

# User activity patterns
grep "filter applied" application.log | tail -20
```

## 🚀 Deployment

### Production Deployment Checklist

#### Pre-deployment
- [ ] All dependencies installed and tested
- [ ] Environment variables configured
- [ ] Database connectivity verified
- [ ] Security groups properly configured
- [ ] SSL certificates installed (if using HTTPS)
- [ ] Backup and recovery procedures tested

#### Deployment Steps

1. **Prepare Production Environment**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv -y

# Create application user
sudo useradd -m -s /bin/bash streamlit-app
sudo su - streamlit-app
```

2. **Deploy Application**
```bash
# Clone repository
git clone <repository-url>
cd texas-treasury-query-app

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure Service**
```bash
# Create systemd service file
sudo nano /etc/systemd/system/treasury-app.service
```

```ini
[Unit]
Description=Texas Treasury Query Application
After=network.target

[Service]
Type=simple
User=streamlit-app
WorkingDirectory=/home/streamlit-app/texas-treasury-query-app
Environment=PATH=/home/streamlit-app/texas-treasury-query-app/venv/bin
ExecStart=/home/streamlit-app/texas-treasury-query-app/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

4. **Start and Enable Service**
```bash
sudo systemctl daemon-reload
sudo systemctl enable treasury-app
sudo systemctl start treasury-app
sudo systemctl status treasury-app
```

### Load Balancing and Scaling

For high-traffic deployments:

1. **Application Load Balancer (ALB)**
   - Configure ALB to distribute traffic across multiple EC2 instances
   - Health checks on `/` endpoint
   - SSL termination at load balancer

2. **Auto Scaling Group**
   - Configure ASG for automatic scaling based on CPU/memory usage
   - Launch template with application pre-installed
   - CloudWatch alarms for scaling triggers

3. **Database Scaling**
   - Read replicas for improved query performance
   - Connection pooling with PgBouncer
   - Monitoring and alerting for database performance

### Backup and Recovery

#### Database Backups
```bash
# Automated RDS snapshots (configured in AWS console)
# Manual backup command
pg_dump -h your-rds-endpoint.amazonaws.com -U username database_name > backup.sql
```

#### Application Backups
```bash
# Backup application files and configuration
tar -czf treasury-app-backup-$(date +%Y%m%d).tar.gz \
  /home/streamlit-app/texas-treasury-query-app \
  --exclude=venv \
  --exclude=__pycache__ \
  --exclude=*.log
```

## 🤝 Contributing

### Development Workflow

1. **Fork the Repository**
```bash
git clone https://github.com/your-username/texas-treasury-query-app.git
cd texas-treasury-query-app
```

2. **Create Development Environment**
```bash
python3 -m venv dev-env
source dev-env/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

3. **Create Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

4. **Development Standards**
   - Follow PEP 8 style guidelines
   - Add docstrings to all functions
   - Include unit tests for new functionality
   - Update documentation as needed

5. **Testing**
```bash
# Run unit tests
python -m pytest tests/

# Run linting
flake8 app.py

# Run type checking
mypy app.py
```

6. **Submit Pull Request**
   - Ensure all tests pass
   - Update CHANGELOG.md
   - Provide clear description of changes

### Code Style Guidelines

#### Python Code Standards
```python
# Good example
def get_filtered_data(table_name: str, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Retrieve filtered data from specified table.
    
    Args:
        table_name: Name of the database table
        filters: Dictionary of filter criteria
        
    Returns:
        pandas.DataFrame: Filtered data results
        
    Raises:
        DatabaseError: If query execution fails
    """
    try:
        # Implementation here
        pass
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise DatabaseError("Failed to retrieve data")
```

#### SQL Query Standards
```sql
-- Use clear, readable formatting
SELECT 
    fiscal_year,
    agency_title,
    vendor_name,
    SUM(payment_amount) as total_amount
FROM paymentinformation 
WHERE fiscal_year BETWEEN %(start_year)s AND %(end_year)s
    AND agency_title ILIKE %(agency_filter)s
GROUP BY fiscal_year, agency_title, vendor_name
ORDER BY total_amount DESC;
```

### Bug Reporting

When reporting bugs, please include:

1. **Environment Information**
   - Operating system and version
   - Python version
   - Streamlit version
   - Database version

2. **Steps to Reproduce**
   - Detailed steps that trigger the issue
   - Expected vs. actual behavior
   - Screenshots if applicable

3. **Error Information**
   - Complete error messages
   - Relevant log entries
   - Stack traces

4. **Additional Context**
   - Data size and complexity
   - Network conditions
   - Recent changes or updates


### Third-Party Licenses

This application uses several open-source libraries:

- **Streamlit**: Apache License 2.0
- **SQLAlchemy**: MIT License
- **Pandas**: BSD 3-Clause License
- **psycopg2**: GNU Lesser General Public License
- **python-dotenv**: BSD 3-Clause License

