import warnings
import os

# Configure pandas to not use timezone features
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

# Set environment variables
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':/home/ubuntu/Query-the-Texas-Treasury/venv/lib/python3.8/site-packages'

# Import pandas after configuration
import pandas as pd

# Configure pandas options
pd.options.mode.chained_assignment = None  # default='warn'
pd.options.display.max_rows = 100
pd.options.display.max_columns = 100 