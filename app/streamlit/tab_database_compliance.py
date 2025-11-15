"""
Database Compliance Tab
Handles the display of database, schema, and table compliance status and remediation
"""

import streamlit as st
from database import get_database_retention_details, get_applied_rules, execute_sql
from compliance import check_table_compliance, generate_table_fix_sql
from ui_utils import render_refresh_button


def render_database_compliance_tab(session):
    """Render the Database Compliance tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_db_compliance")
    with col_title:
        st.markdown("### 🗄️ Database Retention Compliance")
    with col_refresh:
        if st.button("🔄", key="refresh_tab_db_compliance", help="Refresh data"):
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
        st.metric("Total Objects", total_objects)
    with col2:
        st.metric("Compliant", compliant_objects, delta=None)
    with col3:
        st.metric("Non-Compliant", non_compliant_objects, delta=None)
    with col4:
        st.markdown(f"**DB:** {databases} | **Schema:** {schemas} | **Table:** {tables}")
    
    st.markdown("---")
    
    # Filter options
    st.markdown("#### Filter Options")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        object_type_filter = st.selectbox(
            "Object Type",
            ["All", "DATABASE", "SCHEMA", "TABLE"],
            key="db_object_type_filter"
        )
    with col2:
        view_option = st.selectbox(
            "Status",
            ["All Objects", "Non-Compliant Only", "Compliant Only"],
            key="db_view_filter"
        )
    with col3:
        search_text = st.text_input("Search by database, schema, or table name", key="db_search")
    
    st.markdown("---")
    
    # Filter compliance data by object type
    if object_type_filter != "All":
        filtered_data = [t for t in compliance_data if t['object_type'] == object_type_filter]
    else:
        filtered_data = compliance_data
    
    # Filter compliance data based on status selection
    if view_option == "Non-Compliant Only":
        filtered_data = [t for t in filtered_data if t['violations']]
    elif view_option == "Compliant Only":
        filtered_data = [t for t in filtered_data if not t['violations']]
    
    # Apply search filter
    if search_text:
        search_lower = search_text.lower()
        filtered_data = [
            t for t in filtered_data 
            if search_lower in str(t.get('database_name', '')).lower() 
            or search_lower in str(t.get('schema_name', '')).lower()
            or search_lower in str(t.get('table_name', '')).lower()
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
        status_text = "✅ Compliant" if is_compliant else "❌ Non-Compliant"
        
        object_type = obj_comp['object_type']
        
        # Build object name based on type
        if object_type == 'DATABASE':
            object_name = f"🗄️ {obj_comp['database_name']}"
            object_icon = "DATABASE"
        elif object_type == 'SCHEMA':
            object_name = f"📁 {obj_comp['database_name']}.{obj_comp['schema_name']}"
            object_icon = "SCHEMA"
        else:  # TABLE
            object_name = f"📊 {obj_comp['database_name']}.{obj_comp['schema_name']}.{obj_comp['table_name']}"
            object_icon = "TABLE"
        
        with st.expander(f"{status_text} - {object_name}", expanded=not is_compliant):
            # Display metadata based on object type
            if object_type == 'DATABASE':
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Database:** {obj_comp['database_name']}")
                    st.markdown(f"**Type:** DATABASE")
                with col2:
                    st.markdown(f"**Owner:** {obj_comp['table_owner']}")
            elif object_type == 'SCHEMA':
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Database:** {obj_comp['database_name']}")
                    st.markdown(f"**Schema:** {obj_comp['schema_name']}")
                with col2:
                    st.markdown(f"**Type:** SCHEMA")
                    st.markdown(f"**Owner:** {obj_comp['table_owner']}")
            else:  # TABLE
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Database:** {obj_comp['database_name']}")
                    st.markdown(f"**Schema:** {obj_comp['schema_name']}")
                with col2:
                    st.markdown(f"**Table:** {obj_comp['table_name']}")
                    st.markdown(f"**Type:** {obj_comp.get('table_type', 'N/A')}")
                with col3:
                    st.markdown(f"**Owner:** {obj_comp['table_owner']}")
            
            # Show violations if any
            if obj_comp['violations']:
                st.markdown("##### Violations")
                for violation in obj_comp['violations']:
                    st.markdown(f"""
                        <div style="padding: 10px; margin: 5px 0; background-color: #fff3cd; border-left: 3px solid orange;">
                            <strong>{violation['rule_name']}</strong><br>
                            Current: {violation['current_value']} {violation['unit']} | 
                            Threshold: {violation['operator']} {violation['threshold_value']} {violation['unit']}
                        </div>
                    """, unsafe_allow_html=True)
                
                # Check if any violation has fix_button or fix_sql enabled
                has_any_fix_button = any(v.get('has_fix_button', False) for v in obj_comp['violations'])
                has_any_fix_sql = any(v.get('has_fix_sql', False) for v in obj_comp['violations'])
                
                # Only show remediation section if at least one option is available
                if has_any_fix_button or has_any_fix_sql:
                    # Generate fix SQL
                    st.markdown("##### Remediation")
                    
                    button_cols = []
                    if has_any_fix_button:
                        button_cols.append(1)
                    if has_any_fix_sql:
                        button_cols.append(1)
                    
                    # Add remaining space
                    button_cols.append(3 - sum(button_cols))
                    
                    cols = st.columns(button_cols)
                    col_idx = 0
                    
                    # Create unique key for buttons
                    obj_key = f"{obj_comp['database_name']}_{obj_comp.get('schema_name', '')}_{obj_comp.get('table_name', '')}_{object_type}"
                    
                    if has_any_fix_button:
                        with cols[col_idx]:
                            button_label = f"🔧 Fix {object_type.title()}"
                            if st.button(button_label, key=f"fix_{obj_key}", use_container_width=True):
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
                                    
                                    st.success(f"✅ {object_type.title()} configuration updated successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error updating {object_type.lower()}: {str(e)}")
                        col_idx += 1
                    
                    if has_any_fix_sql:
                        with cols[col_idx]:
                            if st.button("📋 Show SQL", key=f"sql_{obj_key}", use_container_width=True):
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
    
    # Bulk fix option for all non-compliant objects
    if view_option == "Non-Compliant Only" and filtered_data:
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
                    if st.button("🔧 Fix All Non-Compliant Objects", type="primary", use_container_width=True):
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
                            
                            st.success(f"✅ Fixed {fixed_count} violations across {len(filtered_data)} objects!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error during bulk fix: {str(e)}")
                col_idx += 1
            
            if has_any_fix_sql:
                with cols[col_idx]:
                    if st.button("📋 Generate SQL for All", use_container_width=True):
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
