"""
Database Compliance Tab
Handles the display of database, schema, and table compliance status and remediation
"""

import streamlit as st
from database import get_database_retention_details, get_applied_rules, execute_sql
from compliance import check_table_compliance, generate_table_fix_sql
from ui_utils import render_refresh_button, render_section_header, render_filter_button


def render_database_compliance_tab(session):
    """Render the Database Compliance tab"""
    # Initialize filter state
    if 'db_compliance_filter' not in st.session_state:
        st.session_state.db_compliance_filter = "All Objects"
    
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_db_compliance")
    with col_title:
        render_section_header("Database Compliance", "db-icon")
    with col_refresh:
        if st.button("⟳", key="refresh_tab_db_compliance", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    # Get applied database rules
    applied_rules_df = get_applied_rules(session)
    db_rules = applied_rules_df[applied_rules_df['RULE_TYPE'] == 'Database']
    
    if db_rules.empty:
        st.info("No database rules have been applied yet. Go to the Rule Configuration tab to apply database rules.")
        return
    
    # Get all retention details (databases, schemas, tables)
    retention_df = get_database_retention_details(session)
    
    if retention_df.empty:
        st.warning("No retention data available. Please execute the db_retention_monitor_task from the Task Management tab.")
        return
    
    # Check compliance
    compliance_data = check_table_compliance(retention_df, db_rules)
    
    # Calculate summary statistics by object type
    total_objects = len(compliance_data)
    non_compliant_objects = sum(1 for t in compliance_data if t['violations'])
    compliant_objects = total_objects - non_compliant_objects
    
    # Count by type
    databases = sum(1 for t in compliance_data if t['object_type'] == 'DATABASE')
    schemas = sum(1 for t in compliance_data if t['object_type'] == 'SCHEMA')
    tables = sum(1 for t in compliance_data if t['object_type'] == 'TABLE')
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_filter_button("Total Objects", total_objects, "filter_all_objects_btn", "All Objects", "db_compliance_filter")
    
    with col2:
        render_filter_button("Compliant", compliant_objects, "filter_compliant_objects_btn", "Compliant Only", "db_compliance_filter")
    
    with col3:
        render_filter_button("Non-Compliant", non_compliant_objects, "filter_non_compliant_objects_btn", "Non-Compliant Only", "db_compliance_filter")
    
    with col4:
        # Calculate compliance rate
        compliance_rate = (compliant_objects / total_objects * 100) if total_objects > 0 else 0
        render_filter_button("Compliance Rate", f"{compliance_rate:.1f}%", "filter_rate_objects_btn", "Non-Compliant First", "db_compliance_filter")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Object type filter and search in one row
    col1, col2 = st.columns([1, 3])
    with col1:
        object_type_filter = st.selectbox(
            "Filter by Object Type",
            ["All", "DATABASE", "SCHEMA", "TABLE"],
            key="db_object_type_filter"
        )
    with col2:
        search_text = st.text_input("Search by database, schema, table, or rule name", placeholder="Type to search...", key="db_search")
    
    st.markdown("---")
    
    # Filter compliance data by object type
    if object_type_filter != "All":
        filtered_data = [t for t in compliance_data if t['object_type'] == object_type_filter]
    else:
        filtered_data = compliance_data
    
    # Filter compliance data based on status selection (use session state)
    view_filter = st.session_state.db_compliance_filter
    
    # Sort if "Non-Compliant First" is selected
    if view_filter == "Non-Compliant First":
        filtered_data = sorted(filtered_data, key=lambda x: (len(x['violations']) == 0, str(x.get('database_name', ''))))
    elif view_filter == "Non-Compliant Only":
        filtered_data = [t for t in filtered_data if t['violations']]
    elif view_filter == "Compliant Only":
        filtered_data = [t for t in filtered_data if not t['violations']]
    
    # Apply search filter
    if search_text:
        search_lower = search_text.lower()
        filtered_data = [
            t for t in filtered_data 
            if (search_lower in str(t.get('database_name', '')).lower() 
                or search_lower in str(t.get('schema_name', '')).lower()
                or search_lower in str(t.get('table_name', '')).lower()
                or any(search_lower in v.get('rule_name', '').lower() for v in t.get('violations', [])))
        ]
    
    # Display results
    if not filtered_data:
        st.info("No objects match the selected filters.")
        return
    
    st.markdown(f"#### Showing {len(filtered_data)} Objects")
    
    # Display objects grouped by type
    for obj_comp in filtered_data:
        # Determine if compliant
        is_compliant = not obj_comp['violations']
        
        object_type = obj_comp['object_type']
        
        # Build object name and details based on type
        if object_type == 'DATABASE':
            object_name = f"{obj_comp['database_name']}"
            object_details = f"<strong>Type:</strong> DATABASE | <strong>Owner:</strong> {obj_comp['table_owner']}"
        elif object_type == 'SCHEMA':
            object_name = f"{obj_comp['database_name']}.{obj_comp['schema_name']}"
            object_details = f"<strong>Type:</strong> SCHEMA | <strong>Owner:</strong> {obj_comp['table_owner']}"
        else:  # TABLE
            object_name = f"{obj_comp['database_name']}.{obj_comp['schema_name']}.{obj_comp['table_name']}"
            object_details = f"<strong>Type:</strong> {obj_comp.get('table_type', 'TABLE')} | <strong>Owner:</strong> {obj_comp['table_owner']}"
        
        # Display object card - compact version (same style as warehouse cards)
        card_class = "warehouse-compact compliant" if is_compliant else "warehouse-compact non-compliant"
        
        with st.container():
            st.markdown(f"""
                <div class="{card_class}">
                    <div class="warehouse-name">{object_name}</div>
                    <div class="warehouse-info">{object_details}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Show violations if any
            if obj_comp['violations']:
                # Show violations in compact format
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    for violation in obj_comp['violations']:
                        st.markdown(f"""
                            <div class="warehouse-violations">
                                <strong>{violation['rule_name']}:</strong> 
                                Current = <code>{violation['current_value']} {violation['unit']}</code>, 
                                Required {violation['operator']} = <code>{violation['threshold_value']} {violation['unit']}</code>
                            </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    # Create unique key for buttons
                    obj_key = f"{obj_comp['database_name']}_{obj_comp.get('schema_name', '')}_{obj_comp.get('table_name', '')}_{object_type}"
                    
                    # Check if any violation has fix_button or fix_sql enabled
                    has_any_fix_button = any(v.get('has_fix_button', False) for v in obj_comp['violations'])
                    has_any_fix_sql = any(v.get('has_fix_sql', False) for v in obj_comp['violations'])
                    
                    if has_any_fix_button or has_any_fix_sql:
                        if has_any_fix_button:
                            if st.button("Fix", key=f"fix_{obj_key}", type="primary", use_container_width=True):
                                try:
                                    # Execute fix for all violations that have fix_button enabled
                                    for violation in obj_comp['violations']:
                                        if violation.get('has_fix_button', False):
                                            fix_sql = generate_table_fix_sql(
                                                obj_comp['database_name'],
                                                obj_comp.get('schema_name'),
                                                obj_comp.get('table_name'),
                                                violation['parameter'],
                                                violation['threshold_value'],
                                                object_type
                                            )
                                            execute_sql(session, fix_sql)
                                    
                                    st.success(f"{object_type.title()} configuration updated successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating {object_type.lower()}: {str(e)}")
                        
                        if has_any_fix_sql:
                            if st.button("Show SQL", key=f"sql_{obj_key}", use_container_width=True):
                                st.session_state[f'show_sql_{obj_key}'] = True
                
                # Show SQL if button was clicked
                if st.session_state.get(f'show_sql_{obj_key}', False):
                    sql_statements = []
                    for violation in obj_comp['violations']:
                        if violation.get('has_fix_sql', False):
                            sql = generate_table_fix_sql(
                                obj_comp['database_name'],
                                obj_comp.get('schema_name'),
                                obj_comp.get('table_name'),
                                violation['parameter'],
                                violation['threshold_value'],
                                object_type
                            )
                            sql_statements.append(sql)
                    
                    if sql_statements:
                        combined_sql = "\n\n".join(sql_statements)
                        st.code(combined_sql, language="sql")
                        
                        if st.button("Hide SQL", key=f"hide_sql_{obj_key}"):
                            st.session_state[f'show_sql_{obj_key}'] = False
                            st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Bulk fix option for all non-compliant objects
    if view_filter == "Non-Compliant Only" and filtered_data:
        st.markdown("---")
        st.markdown("#### Bulk Actions")
        
        # Check if any object has fix options enabled
        has_any_fix_button = any(
            any(v.get('has_fix_button', False) for v in obj['violations'])
            for obj in filtered_data if obj['violations']
        )
        has_any_fix_sql = any(
            any(v.get('has_fix_sql', False) for v in obj['violations'])
            for obj in filtered_data if obj['violations']
        )
        
        if has_any_fix_button or has_any_fix_sql:
            button_cols = []
            if has_any_fix_button:
                button_cols.append(1)
            if has_any_fix_sql:
                button_cols.append(1)
            button_cols.append(3 - sum(button_cols))
            
            cols = st.columns(button_cols)
            col_idx = 0
            
            if has_any_fix_button:
                with cols[col_idx]:
                    if st.button("Fix All Non-Compliant Objects", key="fix_all_objects", type="primary", use_container_width=True):
                        try:
                            fixed_count = 0
                            for obj_comp in filtered_data:
                                if obj_comp['violations']:
                                    for violation in obj_comp['violations']:
                                        if violation.get('has_fix_button', False):
                                            fix_sql = generate_table_fix_sql(
                                                obj_comp['database_name'],
                                                obj_comp.get('schema_name'),
                                                obj_comp.get('table_name'),
                                                violation['parameter'],
                                                violation['threshold_value'],
                                                obj_comp['object_type']
                                            )
                                            execute_sql(session, fix_sql)
                                            fixed_count += 1
                            
                            st.success(f"Fixed {fixed_count} violations across {len(filtered_data)} objects!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error during bulk fix: {str(e)}")
                col_idx += 1
            
            if has_any_fix_sql:
                with cols[col_idx]:
                    if st.button("Generate SQL for All", key="sql_all_objects", use_container_width=True):
                        st.session_state['show_bulk_sql'] = True
            
            # Show bulk SQL if requested
            if st.session_state.get('show_bulk_sql', False):
                st.markdown("##### SQL for All Non-Compliant Objects")
                all_sql = []
                for obj_comp in filtered_data:
                    if obj_comp['violations']:
                        for violation in obj_comp['violations']:
                            if violation.get('has_fix_sql', False):
                                sql = generate_table_fix_sql(
                                    obj_comp['database_name'],
                                    obj_comp.get('schema_name'),
                                    obj_comp.get('table_name'),
                                    violation['parameter'],
                                    violation['threshold_value'],
                                    obj_comp['object_type']
                                )
                                all_sql.append(sql)
                
                if all_sql:
                    combined_sql = "\n\n".join(all_sql)
                    st.code(combined_sql, language="sql")
                
                # Reset state
                if st.button("Hide SQL"):
                    st.session_state['show_bulk_sql'] = False
                    st.rerun()
        else:
            st.info("No fix options are available for the current non-compliant objects.")
