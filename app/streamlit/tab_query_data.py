"""
Query Data Tab
Allows users to execute custom SQL queries and view results
"""

import streamlit as st
import pandas as pd
from ui_utils import render_refresh_button, render_section_header


def render_query_data_tab(session):
    """Render the Query Data tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_query")
    with col_title:
        render_section_header("Query Data", "chart-icon")
    with col_refresh:
        if st.button("↻", key="refresh_tab_query", help="Refresh data", type="secondary"):
            st.rerun()
    st.markdown("---")
    
    st.markdown("""
    Execute custom SQL queries against your Snowflake account. 
    View results in a table format or see error messages if the query fails.
    """)
    
    # Initialize session state for query results
    if 'query_result' not in st.session_state:
        st.session_state.query_result = None
    if 'query_error' not in st.session_state:
        st.session_state.query_error = None
    
    # SQL Query input
    query = st.text_area(
        "Enter your SQL query:",
        placeholder="SELECT * FROM INFORMATION_SCHEMA.DATABASES LIMIT 10;",
        height=150,
        key="sql_query_input"
    )
    
    # Execute button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("Execute Query", key="execute_query_btn", type="primary"):
            if query.strip():
                try:
                    # Execute the query
                    result = session.sql(query).collect()
                    
                    # Convert to pandas DataFrame for display
                    if result:
                        st.session_state.query_result = pd.DataFrame(result)
                        st.session_state.query_error = None
                    else:
                        st.session_state.query_result = pd.DataFrame()
                        st.session_state.query_error = None
                        
                except Exception as e:
                    st.session_state.query_error = str(e)
                    st.session_state.query_result = None
            else:
                st.session_state.query_error = "Please enter a query to execute."
                st.session_state.query_result = None
    
    with col2:
        if st.button("Clear Results", key="clear_results_btn", type="secondary"):
            st.session_state.query_result = None
            st.session_state.query_error = None
            st.rerun()
    
    st.markdown("---")
    
    # Display results or errors
    if st.session_state.query_error:
        st.error(f"**Query Error:**\n\n{st.session_state.query_error}")
    
    if st.session_state.query_result is not None:
        if not st.session_state.query_result.empty:
            st.success(f"Query returned {len(st.session_state.query_result)} rows")
            
            # Display dataframe with scrolling
            st.dataframe(
                st.session_state.query_result,
                use_container_width=True,
                hide_index=True
            )
            
            # Add download button
            csv = st.session_state.query_result.to_csv(index=False)
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv",
                key="download_csv_btn"
            )
        else:
            st.info("Query executed successfully but returned no results.")
    
    # Add helpful examples
    with st.expander("📚 Example Queries"):
        st.markdown("""
        **List all databases:**
        ```sql
        SHOW DATABASES;
        ```
        
        **List all warehouses:**
        ```sql
        SHOW WAREHOUSES;
        ```
        
        **View warehouse configurations:**
        ```sql
        SELECT * FROM CONFIG_SCHEMA.WH_CONFIGURATIONS LIMIT 10;
        ```
        
        **View applied rules:**
        ```sql
        SELECT * FROM CONFIG_SCHEMA.APPLIED_RULES;
        ```
        
        **View database retention policies:**
        ```sql
        SELECT * FROM CONFIG_SCHEMA.DB_RETENTION_DETAILS LIMIT 10;
        ```
        """)
