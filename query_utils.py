from sqlalchemy import text
from sqlalchemy import select
from logger_config import get_logger
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from db_config import check_table_accessibility, execute_safe_query

# Initialize logger
logger = get_logger('query_utils')

def build_base_query(table_choice: str) -> Tuple[str, Dict]:
    """
    Build the base query based on the selected table.
    
    Args:
        table_choice (str): Either "Payment Information" or "Contract Information"
        
    Returns:
        Tuple[str, Dict]: The base query and parameters dictionary
    """
    logger.info(f"Building base query for {table_choice}")
    
    # Determine table alias and name
    table_info = {
        "Payment Information": ("p", "paymentinformation", "p.vendor, p.vendor_number, p.agency, p.agency_number, p.dollar_value, p.fund_title, \
        p.fund_number, p.appropriation_year, p.fiscal_year, p.fiscal_month, p.appropriation_title, p.object_title, p.object_number, p.revision_indicator, \
        p.confidential, p.program_cost_account, p.mail_code"),
        "Contract Information": ("c", "contractinfo", "c.contract_id, c.vendor, c.vendorid_num, c.agency, c.dollar_value, c.subject, c.status, c.award_date, \
        c.completion_date, c.fiscal_year, c.fiscal_month, c.procurement_method, c.category, c.ngip_cnc")
    }
    
    thing = table_info.get(table_choice)
    return thing

def add_filters_to_query(queryArgs, filters):
    newArgs = "WHERE 1=1"
    # FY
    if filters.get('fiscal_year_start') and filters.get('fiscal_year_end'):
        newArgs = newArgs +" AND " + queryArgs[0] + ".fiscal_year BETWEEN " + str(filters.get('fiscal_year_start')).replace("20", '', 1) \
            + " AND " + str(filters.get('fiscal_year_end')).replace("20", '', 1)
    # FM
    if filters.get('fiscal_month_start') and filters.get('fiscal_month_end'):
        newArgs = newArgs + " AND " + queryArgs[0] + ".fiscal_month BETWEEN " + str(filters.get('fiscal_month_start')).replace("20", '', 1) \
            + " AND " + str(filters.get('fiscal_month_end')).replace("20", '', 1)
    # Agency
    if filters.get('agency'):
        newArgs = newArgs + " AND " + queryArgs[0] + ".agency = '" + filters.get('agency') + "'"
        #Vendor
    if filters.get('vendor'):
        for i in filters.get('vendor'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".vendor = '" + i + "'"
    #by table basis
    if queryArgs[0] == 'p':
        #Aprop Title
        if filters.get('appropriation_title'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".appropriation_title = '" + filters.get('appropriation_title') + "'"
        #Payment Source
        if filters.get('payment_source'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".fund_title = '" + filters.get('payment_source') + "'"
        #Aprop Object
        if filters.get('appropriation_object'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".object_title = '" + filters.get('appropriation_object') + "'"
    else:
        #Category
        if filters.get('category'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".category = '" + filters.get('category') + "'"
        #Procurement Method
        if filters.get('procurement_method'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".procurement_method = '" + filters.get('procurement_method') + "'"
        #Status
        if filters.get('status'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".status = '" + filters.get('status') + "'"
        #Subject
        if filters.get('subject'):
            newArgs = newArgs + " AND " + queryArgs[0] + ".subject = '" + filters.get('subject') + "'"
    return newArgs

def execute_query(query, params, engine) -> List[Dict]:
    """
    Execute a query and return results as a list of dictionaries.
    """
    try:
        logger.info(f"Executing query: {str(query)}")
        logger.info(f"Parameters: {params}")
        
        # Convert parameters to a list of tuples for SQLAlchemy
        #statement = select(text(query[1]).label(query[0])).where(text(params))
        statement = "select " + query[2] + " FROM " + query[1] + " as " + query[0] + "\n" + params + " LIMIT 100"
        logger.info(statement)
        with engine.connect() as connection:
            # Execute query with parameters as a list of tuples
            result = connection.execute(text(statement)).mappings()
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        return []

def get_filtered_data(filters: Dict, table_choice: str, engine) -> pd.DataFrame:
    """
    Main function to get filtered data from the database.
    """
    logger.info(f"Getting filtered data for {table_choice}")
    logger.info(f"Filters received: {filters}")
    
    try:
        # Build and execute query
        queryBase = build_base_query(table_choice)
        
        queryArgs = add_filters_to_query(queryBase, filters)
        
        results = execute_query(queryBase, queryArgs, engine)
        
        # Convert to DataFrame
        if results:
            df = pd.DataFrame(results)
            logger.info(f"DataFrame created with {len(df)} rows and columns: {df.columns.tolist()}")
            return df
        logger.info("No results found, returning empty DataFrame")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting filtered data: {str(e)}")
        return pd.DataFrame() 