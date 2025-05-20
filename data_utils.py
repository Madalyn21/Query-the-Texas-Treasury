import pandas as pd
import streamlit as st
from typing import List, Tuple, Any
from logger_config import get_logger

# Initialize logger
logger = get_logger('data_utils')

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_csv_data(file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """Load CSV data with caching and multiple encoding attempts"""
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
def process_dropdown_data(df: pd.DataFrame, column_name: str) -> List[Tuple[str, str]]:
    """Process dropdown data with caching"""
    values = df[column_name].unique()
    return sorted([(str(val), str(val)) for val in values])

def validate_input(data: Any) -> str:
    """Validate and sanitize user input"""
    if isinstance(data, str):
        # Remove any potentially dangerous characters
        return ''.join(c for c in data if c.isalnum() or c in ' -_.,')
    return str(data)

def format_currency(value: float) -> str:
    """Format a number as currency"""
    return f"${value:,.2f}"

def format_percentage(value: float) -> str:
    """Format a number as percentage"""
    return f"{value:.2f}%"

def safe_divide(numerator: float, denominator: float) -> float:
    """Safely divide two numbers, returning 0 if denominator is 0"""
    try:
        return numerator / denominator if denominator != 0 else 0
    except Exception:
        return 0

def get_summary_statistics(df: pd.DataFrame, numeric_columns: List[str]) -> dict:
    """Calculate summary statistics for numeric columns"""
    stats = {}
    for col in numeric_columns:
        if col in df.columns:
            stats[col] = {
                'mean': df[col].mean(),
                'median': df[col].median(),
                'min': df[col].min(),
                'max': df[col].max(),
                'std': df[col].std()
            }
    return stats 