"""
Snowflake Config Rules App - Main Application
Manage and enforce configuration rules across Snowflake warehouses
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

# Import modules
from ui_utils import load_css, render_header, render_footer
from tab_rule_config import render_rule_configuration_tab
from tab_compliance import render_compliance_view_tab
from tab_warehouse_overview import render_warehouse_overview_tab

# Get the active Snowflake session
session = get_active_session()

# Set page configuration
st.set_page_config(
    page_title="Snowflake Config Rules",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
load_css()

# Render header
render_header()

# Create tabs
tab1, tab2, tab3 = st.tabs(["Rule Configuration", "Compliance View", "Warehouse Overview"])

# Render each tab
with tab1:
    render_rule_configuration_tab(session)

with tab2:
    render_compliance_view_tab(session)

with tab3:
    render_warehouse_overview_tab(session)

# Render footer
render_footer()
