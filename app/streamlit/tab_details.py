"""
Details Tab
Displays data from all tables in the data_schema
"""

import streamlit as st
from ui_utils import render_refresh_button, render_section_header, render_count_metric


def render_details_tab(session):
    """Render the Details tab showing all data_schema tables"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab5")
    with col_title:
        render_section_header("Application Data Inspector", "chart-icon")
    with col_refresh:
        if st.button("⟳", key="refresh_tab_details", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    st.markdown("""
    Explore all configuration data collected by the application. View warehouse configurations, 
    retention policies, active rules, and task execution details.
    """)
    
    st.markdown("---")
    
    # Table 1: Warehouse Details
    with st.expander("Warehouse Details", expanded=False):
        try:
            query = """
            SELECT 
                name, type, size, auto_suspend, statement_timeout_in_seconds,
                owner, min_cluster_count, max_cluster_count, scaling_policy,
                max_concurrency_level, statement_queued_timeout_in_seconds,
                created_on, updated_on, comment, capture_timestamp
            FROM data_schema.warehouse_details
            ORDER BY capture_timestamp DESC, name
            LIMIT 100
            """
            df = session.sql(query).to_pandas()
            
            if not df.empty:
                st.markdown(f"**Total Records:** {len(df)}")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No warehouse details data available. The warehouse_monitor_task will populate this table.")
        except Exception as e:
            st.error(f"Error loading warehouse details: {str(e)}")
    
    # Table 2: Database Retention Details
    with st.expander("Database Retention Details", expanded=False):
        try:
            query = """
            SELECT 
                object_type, database_name, schema_name, table_name, table_type,
                data_retention_time_in_days, owner, row_count, bytes,
                created_on, last_altered, comment, capture_timestamp
            FROM data_schema.database_retention_details
            ORDER BY capture_timestamp DESC, object_type,database_name, schema_name, table_name
            LIMIT 100
            """
            df = session.sql(query).to_pandas()
            
            if not df.empty:
                st.markdown(f"**Total Records:** {len(df)}")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No database retention data available. The db_retention_monitor_task will populate this table.")
        except Exception as e:
            st.error(f"Error loading database retention details: {str(e)}")
    
    # Table 3: Configuration Rules
    with st.expander("Configuration Rules", expanded=False):
        try:
            query = """
            SELECT 
                rule_id, rule_name, rule_description, rule_type,
                check_parameter, comparison_operator, unit,
                is_active, created_at, updated_at
            FROM data_schema.config_rules
            ORDER BY rule_type, rule_name
            """
            df = session.sql(query).to_pandas()
            
            if not df.empty:
                st.markdown(f"**Total Records:** {len(df)}")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No configuration rules found.")
        except Exception as e:
            st.error(f"Error loading configuration rules: {str(e)}")
    
    # Table 4: Applied Rules
    with st.expander("Applied Rules", expanded=False):
        try:
            query = """
            SELECT 
                ar.applied_rule_id, ar.rule_id, cr.rule_name, ar.threshold_value,
                cr.rule_type, cr.check_parameter, cr.comparison_operator, cr.unit,
                ar.applied_at, ar.applied_by, ar.is_active
            FROM data_schema.applied_rules ar
            JOIN data_schema.config_rules cr ON ar.rule_id = cr.rule_id
            ORDER BY ar.applied_at DESC
            """
            df = session.sql(query).to_pandas()
            
            if not df.empty:
                st.markdown(f"**Total Records:** {len(df)}")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No rules have been applied yet.")
        except Exception as e:
            st.error(f"Error loading applied rules: {str(e)}")
    
    # Table 5: Applied Tag Rules
    with st.expander("Applied Tag Rules", expanded=False):
        try:
            query = """
            SELECT 
                applied_tag_rule_id, tag_name, object_type,
                applied_at, applied_by, is_active
            FROM data_schema.applied_tag_rules
            ORDER BY applied_at DESC
            """
            df = session.sql(query).to_pandas()
            
            if not df.empty:
                st.markdown(f"**Total Records:** {len(df)}")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No tag rules have been applied yet.")
        except Exception as e:
            st.error(f"Error loading applied tag rules: {str(e)}")
    
    # Table 6: Tag Compliance Details
    with st.expander("Tag Compliance Details", expanded=False):
        try:
            query = """
            SELECT 
                object_type, object_database, object_schema, object_name,
                tag_name, tag_value, capture_timestamp
            FROM data_schema.tag_compliance_details
            ORDER BY capture_timestamp DESC, object_type, object_name, tag_name
            LIMIT 100
            """
            df = session.sql(query).to_pandas()
            
            if not df.empty:
                st.markdown(f"**Total Records:** {len(df)}")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No tag compliance data available. The tag_monitor_task will populate this table.")
        except Exception as e:
            st.error(f"Error loading tag compliance details: {str(e)}")
    
    # Table 7: Tasks Information
    with st.expander("Tasks", expanded=False):
        try:
            query = """
            SHOW TASKS IN DATABASE SNOWFLAKE_CONFIG_RULES_APP;
            """
            df = session.sql(query).to_pandas()
            
            if not df.empty:
                st.markdown(f"**Total Tasks:** {len(df)}")
                # Select relevant columns
                display_cols = ['name', 'state', 'warehouse', 'schedule', 'owner', 'created_on', 'last_committed_on']
                available_cols = [col for col in display_cols if col in df.columns or col.upper() in df.columns]
                
                if available_cols:
                    # Handle case sensitivity
                    display_df = df.copy()
                    for col in available_cols:
                        if col.upper() in display_df.columns and col not in display_df.columns:
                            display_df[col] = display_df[col.upper()]
                    
                    st.dataframe(display_df[available_cols], use_container_width=True, hide_index=True)
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No tasks found in data_schema.")
        except Exception as e:
            st.error(f"Error loading tasks: {str(e)}")
    
    # Summary Statistics
    st.markdown("---")
    render_section_header("Summary Statistics", "chart-icon")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_count_metric(session, "SELECT COUNT(*) as cnt FROM data_schema.warehouse_details", "Warehouse Records")
    
    with col2:
        render_count_metric(session, "SELECT COUNT(*) as cnt FROM data_schema.database_retention_details", "Database Retention Records")
    
    with col3:
        render_count_metric(session, "SELECT COUNT(*) as cnt FROM data_schema.config_rules WHERE is_active = TRUE", "Active Rules")
    
    with col4:
        render_count_metric(session, "SELECT COUNT(*) as cnt FROM data_schema.applied_rules WHERE is_active = TRUE", "Applied Rules")
    
    with col5:
        render_count_metric(session, "SELECT COUNT(*) as cnt FROM data_schema.applied_tag_rules WHERE is_active = TRUE", "Applied Tag Rules")

