# Texas Treasury Query Application

A robust Streamlit-based web application for querying and analyzing Texas Treasury payment and contract information, deployed on AWS infrastructure with PostgreSQL database backend.

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

Jackson's Part

Most of the database stuff is pretty simple, in theory there won't be any issues which crop up due to it.
Here's the thing I can think of.
For anything using a SQL query, I'd recommend loading up pgAdmin4, connecting to the server with the Query Tool tab and running your queries there.

### Modifying the Security Group
You need to do this before connecting to the database any time as otherwise you'll get blocked.
Go to the RDS tab on AWS and open the instance dashboard. 
On Connectivity and Security, there is a section called "VPC security groups".
Under that is a link rds-access-group, click that.
Click on the security group ID.
Click edit inbound rules.
Click Add Rule.
Click where it says custom TCP and type in PostgreSQL.
Under source, click Custom. 
Select in the dropdown My IP. 
Click save rules.
Make sure to come back and remove the rule when your done.

### Adding new tables
If you want to add a new table, simply
CREATE TABLE tableName(
columnName datatype,
columnName datatype
);

### Adding columns to existing tables
ALTER TABLE tableName
ADD COLUMN columnName datatype;

### Adding more data
Make sure that the data has columns which line up with the columns in the table.
\copy tableName
FROM 'file\path'
with delimiter ',' 
CSV HEADER;
