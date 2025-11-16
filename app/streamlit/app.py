"""
Snowflake Config Rules App - Main Application
Manage and enforce configuration rules across Snowflake warehouses
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

# Import modules
from ui_utils import load_css, render_header, render_footer
from tab_rule_config import render_rule_configuration_tab
from tab_tag_compliance import render_tag_compliance_tab
from tab_wh_compliance import render_wh_compliance_view_tab
from tab_task_management import render_task_management_tab
from tab_database_compliance import render_database_compliance_tab
from tab_details import render_details_tab
from tab_query_data import render_query_data_tab

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

# Create tabs with user-friendly names
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Configure Rules", 
    "Tag Compliance",
    "Warehouse Compliance", 
    "Database Compliance",
    "Schedule & Tasks",
    "Query Data",
    "App Data Inspector"
])

# Render each tab
with tab1:
    render_rule_configuration_tab(session)

with tab2:
    render_tag_compliance_tab(session)

with tab3:
    render_wh_compliance_view_tab(session)

with tab4:
    render_database_compliance_tab(session)

with tab5:
    render_task_management_tab(session)

with tab6:
    render_query_data_tab(session)

with tab7:
    render_details_tab(session)

# Render footer
render_footer()
