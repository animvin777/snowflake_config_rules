"""
Database Compliance Tab
Handles the display of database, schema, and table compliance status and remediation
"""

import streamlit as st
import pandas as pd
from database import (get_database_retention_details, get_applied_rules, execute_sql, 
                      get_tag_compliance_details, get_whitelisted_violations, add_to_whitelist, 
                      get_db_compliance_results_paginated, get_db_compliance_metrics)
from compliance import generate_table_fix_sql
from ui_utils import render_refresh_button, render_section_header, render_filter_button, render_pagination_controls


def render_database_compliance_tab(session):
    """Render the Database Compliance tab"""
    # Initialize filter state
    if 'db_compliance_filter' not in st.session_state:
        st.session_state.db_compliance_filter = "All Objects"
    
    # Initialize pagination state
    if 'db_page_size' not in st.session_state:
        st.session_state.db_page_size = 10
    if 'db_current_page' not in st.session_state:
        st.session_state.db_current_page = 0
    if 'db_search_term' not in st.session_state:
        st.session_state.db_search_term = ""
    if 'db_object_type_filter' not in st.session_state:
        st.session_state.db_object_type_filter = "All"
    
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_db_compliance")
    with col_title:
        render_section_header("Database Compliance", "db-icon")
    with col_refresh:
        if st.button("↻", key="refresh_tab_db_compliance", help="Refresh data", type="secondary"):
            st.rerun()
    st.markdown("---")
    
    # Get applied database rules
    applied_rules_df = get_applied_rules(session)
    db_rules = applied_rules_df[applied_rules_df['RULE_TYPE'] == 'Database']
    
    if db_rules.empty:
        st.info("No database rules have been applied yet. Go to the Rule Configuration tab to apply database rules.")
        return
    
    # Get metrics from database
    object_type_for_query = None if st.session_state.db_object_type_filter == "All" else st.session_state.db_object_type_filter
    try:
        metrics = get_db_compliance_metrics(session, object_type_for_query, st.session_state.db_compliance_filter.lower())
    except:
        metrics = {'total': 0, 'violations': 0, 'compliant': 0, 'whitelisted': 0, 'compliance_rate': 0}
    
    if metrics['total'] == 0:
        st.warning("No compliance data available. Click 'Run Rules' in the Rule Configuration tab to generate compliance results.")
        return
    
    # Display summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_filter_button("Total Objects", metrics['total'], "filter_all_objects_btn", "All Objects", "db_compliance_filter")
    
    with col2:
        render_filter_button("Compliant", metrics['compliant'], "filter_compliant_objects_btn", "Compliant Only", "db_compliance_filter")
    
    with col3:
        render_filter_button("Non-Compliant", metrics['violations'], "filter_non_compliant_objects_btn", "Non-Compliant Only", "db_compliance_filter")
    
    with col4:
        render_filter_button("Compliance Rate", f"{metrics['compliance_rate']:.1f}%", "filter_rate_objects_btn", "Non-Compliant First", "db_compliance_filter")
    
    with col5:
        render_filter_button("Whitelisted", metrics['whitelisted'], "filter_whitelist_objects_btn", "Whitelisted Only", "db_compliance_filter")
    
    st.html("<br>")
    
    # Object type filter and search in one row
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        object_type_input = st.selectbox(
            "Filter by Object Type",
            ["All", "DATABASE", "SCHEMA", "TABLE"],
            index=["All", "DATABASE", "SCHEMA", "TABLE"].index(st.session_state.db_object_type_filter),
            key="db_object_type_input"
        )
    with col2:
        search_input = st.text_input("Search by name", placeholder="Type database, schema, or table name...", key="db_search_input", label_visibility="collapsed")
    with col3:
        if st.button("Search", key="db_search_btn", type="primary", use_container_width=True):
            st.session_state.db_search_term = search_input
            st.session_state.db_object_type_filter = object_type_input
            st.session_state.db_current_page = 0  # Reset to first page on new search
    
    # Pagination controls
    st.markdown("---")
    offset = st.session_state.db_current_page * st.session_state.db_page_size
    object_type_for_query = None if st.session_state.db_object_type_filter == "All" else st.session_state.db_object_type_filter
    
    try:
        compliance_data, total_count = get_db_compliance_results_paginated(
            session,
            object_type=object_type_for_query,
            search_term=st.session_state.db_search_term if st.session_state.db_search_term else None,
            limit=st.session_state.db_page_size,
            offset=offset
        )
    except Exception as e:
        st.error(f"Error loading compliance data: {str(e)}")
        compliance_data, total_count = [], 0
    
    # Render pagination controls
    new_page_size, new_page = render_pagination_controls(
        total_count,
        st.session_state.db_page_size,
        st.session_state.db_current_page,
        "db_compliance"
    )
    
    # Update session state if pagination changed
    if new_page_size != st.session_state.db_page_size or new_page != st.session_state.db_current_page:
        st.session_state.db_page_size = new_page_size
        st.session_state.db_current_page = new_page
        st.rerun()
    
    st.markdown("---")
    
    # Filter by view filter
    
    # Filter compliance data based on status selection
    view_filter = st.session_state.db_compliance_filter
    filtered_data = compliance_data
    
    # Sort if "Non-Compliant First" is selected
    if view_filter == "Non-Compliant First":
        filtered_data = sorted(filtered_data, key=lambda x: (len(x['violations']) == 0, str(x.get('database_name', ''))))
    elif view_filter == "Whitelisted Only":
        filtered_data = [t for t in filtered_data if any(v.get('is_whitelisted', False) for v in t['violations'])]
    elif view_filter == "Non-Compliant Only":
        filtered_data = [t for t in filtered_data if any(not v.get('is_whitelisted', False) for v in t['violations'])]
    elif view_filter == "Compliant Only":
        filtered_data = [t for t in filtered_data if not any(not v.get('is_whitelisted', False) for v in t['violations'])]
    
    # Display results
    if not filtered_data:
        st.info("No objects match the selected filters.")
        return
    
    st.markdown(f"#### Showing {len(filtered_data)} Objects")
    
    # Display objects grouped by type
    for obj_comp in filtered_data:
        # Separate whitelisted and non-whitelisted violations
        all_violations = obj_comp['violations']
        whitelisted_violations = [v for v in all_violations if v.get('is_whitelisted', False)]
        non_whitelisted_violations = [v for v in all_violations if not v.get('is_whitelisted', False)]
        
        # Determine if compliant (based on non-whitelisted violations)
        is_compliant = not non_whitelisted_violations
        
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
        
        # Count violations and compliant rules
        violation_count = len(non_whitelisted_violations)
        whitelisted_count_obj = len(whitelisted_violations)
        
        # Get all applicable rules for this object (considering tags and object type)
        applicable_rules_count = len(obj_comp.get('applicable_rules', []))
        compliant_rules_count = applicable_rules_count - (violation_count + whitelisted_count_obj)
        
        # Build counts display
        counts_parts = []
        if applicable_rules_count == 0:
            # No rules applicable to this object
            counts_html = '<span class="count-badge count-no-rules">No rules applicable</span>'
        else:
            if violation_count > 0:
                counts_parts.append(f'<span class="count-badge count-violations">{violation_count} Violation{"s" if violation_count != 1 else ""}</span>')
            if whitelisted_count_obj > 0:
                counts_parts.append(f'<span class="count-badge count-whitelisted">{whitelisted_count_obj} Whitelisted</span>')
            if compliant_rules_count > 0:
                counts_parts.append(f'<span class="count-badge count-compliant">{compliant_rules_count} Compliant</span>')
            
            counts_html = " ".join(counts_parts) if counts_parts else '<span class="count-badge count-compliant">All Rules Compliant</span>'
        
        # Determine which violations to show based on filter
        if view_filter == "Whitelisted Only":
            if not whitelisted_violations:
                continue
            violations_to_show = whitelisted_violations
        else:
            violations_to_show = non_whitelisted_violations
        
        # Display object card - compact version (same style as warehouse cards)
        card_class = "warehouse-compact compliant" if is_compliant else "warehouse-compact non-compliant"
        
        with st.container():
            st.html(f"""
                <div class="{card_class}">
                    <div class="warehouse-name">{object_name}</div>
                    <div class="warehouse-info">{object_details}</div>
                    <div class="counts-container" style="margin-top: 6px;">{counts_html}</div>
                </div>
            """)
            
            # Show violations if any
            if violations_to_show:
                # Show violations in compact format
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    for idx, violation in enumerate(violations_to_show):
                        is_whitelisted = violation.get('is_whitelisted', False)
                        
                        # Create columns for violation and whitelist button
                        vcol1, vcol2 = st.columns([5, 1])
                        
                        with vcol1:
                            whitelisted_badge = '<span class="whitelisted-badge">Whitelisted</span>' if is_whitelisted else ''
                            st.html(f"""
                                <div class="violation-item">
                                    <div>
                                        <div class="violation-rule-name">{violation['rule_name']} {whitelisted_badge}</div>
                                        <div class="violation-details">
                                            <div class="violation-value">
                                                <span class="violation-label">Current:</span>
                                                <span class="violation-code">{violation['current_value']} {violation['unit']}</span>
                                            </div>
                                            <div class="violation-value">
                                                <span class="violation-operator">{violation['operator']}</span>
                                            </div>
                                            <div class="violation-value">
                                                <span class="violation-label">Required:</span>
                                                <span class="violation-code">{violation['threshold_value']} {violation['unit']}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            """)
                        
                        with vcol2:
                            # Add whitelist button only for non-whitelisted violations
                            if not is_whitelisted:
                                # Build object name based on type
                                if object_type == 'DATABASE':
                                    obj_name = obj_comp['database_name']
                                elif object_type == 'SCHEMA':
                                    obj_name = f"{obj_comp['database_name']}.{obj_comp['schema_name']}"
                                else:  # TABLE
                                    obj_name = f"{obj_comp['database_name']}.{obj_comp['schema_name']}.{obj_comp['table_name']}"
                                
                                st.html('<div class="whitelist-button-wrapper">')
                                # Add whitelist button for each violation
                                if st.button("Whitelist", key=f"whitelist_{obj_name}_{idx}", 
                                           help="Whitelist this violation",
                                           type="secondary"):
                                    try:
                                        add_to_whitelist(
                                            session,
                                            rule_id=violation['rule_id'],
                                            applied_rule_id=violation.get('applied_rule_id'),
                                            object_type=object_type,
                                            object_name=obj_name,
                                            database_name=obj_comp['database_name'],
                                            schema_name=obj_comp.get('schema_name'),
                                            table_name=obj_comp.get('table_name'),
                                            reason=f"Whitelisted from UI"
                                        )
                                        st.success(f"Violation whitelisted for {obj_name}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error whitelisting: {str(e)}")
                                st.html('</div>')
                
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
            
            # Show compliant rules if there are any
            if obj_comp.get('compliant_rules'):
                compliant_rules = obj_comp['compliant_rules']
                rule_badges = ''.join([
                    f'<span class="compliant-rule-badge">{rule["rule_name"]}</span>'
                    for rule in compliant_rules
                ])
                st.html(f"""
                    <div class="compliant-rules-section">
                        <div class="compliant-rules-header">Compliant with {len(compliant_rules)} rule(s)</div>
                        <div class="compliant-rules-list">
                            {rule_badges}
                        </div>
                    </div>
                """)
            
            st.html("<br>")
    
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
