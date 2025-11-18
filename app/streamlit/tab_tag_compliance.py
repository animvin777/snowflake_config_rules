"""
Tag Compliance Tab
Handles the display of tag compliance status for warehouses, databases, and tables
"""

import streamlit as st
import pandas as pd
from database import (get_applied_tag_rules, get_tag_compliance_details, get_all_objects_by_type, 
                      get_whitelisted_violations, add_to_whitelist, 
                      get_tag_compliance_results_paginated, get_tag_compliance_metrics)
from compliance import generate_tag_fix_sql
from ui_utils import render_refresh_button, render_section_header, render_filter_button, render_pagination_controls


def render_tag_compliance_tab(session):
    """Render the Tag Compliance tab"""
    # Initialize filter state
    if 'tag_compliance_filter' not in st.session_state:
        st.session_state.tag_compliance_filter = "All Objects"
    
    # Initialize pagination state
    if 'tag_page_size' not in st.session_state:
        st.session_state.tag_page_size = 10
    if 'tag_current_page' not in st.session_state:
        st.session_state.tag_current_page = 0
    if 'tag_search_term' not in st.session_state:
        st.session_state.tag_search_term = ""
    if 'tag_object_type_filter' not in st.session_state:
        st.session_state.tag_object_type_filter = "WAREHOUSE"
    
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_tag_compliance")
    with col_title:
        render_section_header("Tag Compliance", "tag-icon")
    with col_refresh:
        if st.button("↻", key="refresh_tab_tag_compliance", help="Refresh data", type="secondary"):
            st.rerun()
    st.markdown("---")
    
    # Get applied tag rules
    tag_rules_df = get_applied_tag_rules(session)
    
    if tag_rules_df.empty:
        st.info("No tag rules have been applied yet. Go to the Rule Configuration tab to apply tag rules.")
        return
    
    # Object type selection and search
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        object_type_input = st.selectbox(
            "Select Object Type",
            ["WAREHOUSE", "DATABASE", "TABLE"],
            index=["WAREHOUSE", "DATABASE", "TABLE"].index(st.session_state.tag_object_type_filter),
            key="tag_object_type_input"
        )
    with col2:
        search_input = st.text_input("Search by object name", placeholder="Type object name...", key="tag_search_input", label_visibility="collapsed")
    with col3:
        if st.button("Search", key="tag_search_btn", type="primary", use_container_width=True):
            st.session_state.tag_search_term = search_input
            st.session_state.tag_object_type_filter = object_type_input
            st.session_state.tag_current_page = 0  # Reset to first page on new search
    
    # Get tag rules for selected object type
    object_tag_rules = tag_rules_df[tag_rules_df['OBJECT_TYPE'] == st.session_state.tag_object_type_filter]
    
    if object_tag_rules.empty:
        st.info(f"No tag rules have been applied for {st.session_state.tag_object_type_filter}s yet.")
        return
    
    # Get metrics from database
    try:
        metrics = get_tag_compliance_metrics(session, st.session_state.tag_object_type_filter, st.session_state.tag_compliance_filter.lower())
    except:
        metrics = {'total': 0, 'violations': 0, 'compliant': 0, 'whitelisted': 0, 'compliance_rate': 0}
    
    if metrics['total'] == 0:
        st.warning(f"No compliance data available for {st.session_state.tag_object_type_filter}s. Click 'Run Rules' in the Rule Configuration tab to generate compliance results.")
        return
    
    # Display summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_filter_button("Total Objects", metrics['total'], "filter_all_tag_objects_btn", "All Objects", "tag_compliance_filter")
    
    with col2:
        render_filter_button("Compliant", metrics['compliant'], "filter_compliant_tag_objects_btn", "Compliant Only", "tag_compliance_filter")
    
    with col3:
        render_filter_button("Non-Compliant", metrics['violations'], "filter_non_compliant_tag_objects_btn", "Non-Compliant Only", "tag_compliance_filter")
    
    with col4:
        render_filter_button("Compliance Rate", f"{metrics['compliance_rate']:.1f}%", "filter_rate_tag_objects_btn", "Non-Compliant First", "tag_compliance_filter")
    
    with col5:
        render_filter_button("Whitelisted", metrics['whitelisted'], "filter_whitelist_tag_objects_btn", "Whitelisted Only", "tag_compliance_filter")
    
    st.html("<br>")
    st.markdown("---")
    
    # Pagination controls
    offset = st.session_state.tag_current_page * st.session_state.tag_page_size
    
    try:
        compliance_data, total_count = get_tag_compliance_results_paginated(
            session,
            object_type=st.session_state.tag_object_type_filter,
            search_term=st.session_state.tag_search_term if st.session_state.tag_search_term else None,
            limit=st.session_state.tag_page_size,
            offset=offset
        )
    except Exception as e:
        st.error(f"Error loading compliance data: {str(e)}")
        compliance_data, total_count = [], 0
    
    # Render pagination controls
    new_page_size, new_page = render_pagination_controls(
        total_count,
        st.session_state.tag_page_size,
        st.session_state.tag_current_page,
        "tag_compliance"
    )
    
    # Update session state if pagination changed
    if new_page_size != st.session_state.tag_page_size or new_page != st.session_state.tag_current_page:
        st.session_state.tag_page_size = new_page_size
        st.session_state.tag_current_page = new_page
        st.rerun()
    
    st.markdown("---")
    
    # Filter compliance data based on status selection
    view_filter = st.session_state.tag_compliance_filter
    filtered_data = compliance_data
    
    # Sort if "Non-Compliant First" is selected
    if view_filter == "Non-Compliant First":
        filtered_data = sorted(filtered_data, key=lambda x: (len([v for v in x['violations'] if not v.get('is_whitelisted', False)]) == 0, x['object_name']))
    elif view_filter == "Whitelisted Only":
        filtered_data = [obj for obj in filtered_data if any(v.get('is_whitelisted', False) for v in obj['violations'])]
    elif view_filter == "Non-Compliant Only":
        filtered_data = [obj for obj in filtered_data if any(not v.get('is_whitelisted', False) for v in obj['violations'])]
    elif view_filter == "Compliant Only":
        filtered_data = [obj for obj in filtered_data if not any(not v.get('is_whitelisted', False) for v in obj['violations'])]
    
    # Display results
    if not filtered_data:
        st.info("No objects match the selected filters.")
        return
    
    st.markdown(f"#### Showing {len(filtered_data)} {st.session_state.tag_object_type_filter}s")
    
    # Determine color scheme based on object type
    if st.session_state.tag_object_type_filter == "WAREHOUSE":
        card_theme = "warehouse"
    elif st.session_state.tag_object_type_filter == "DATABASE":
        card_theme = "database"
    else:  # TABLE
        card_theme = "tag"
    
    # Display objects
    for obj_comp in filtered_data:
        # Separate whitelisted and non-whitelisted violations
        all_violations = obj_comp['violations']
        whitelisted_violations = [v for v in all_violations if v.get('is_whitelisted', False)]
        non_whitelisted_violations = [v for v in all_violations if not v.get('is_whitelisted', False)]
        
        # Determine if compliant (based on non-whitelisted violations)
        is_compliant = not non_whitelisted_violations
        
        object_name = obj_comp['object_name']
        object_type = obj_comp['object_type']
        
        # Determine which violations to show based on filter
        if view_filter == "Whitelisted Only":
            violations_to_show = whitelisted_violations
        else:
            violations_to_show = non_whitelisted_violations
        
        # Build object details
        object_details_parts = [f"<strong>Type:</strong> {object_type}"]
        if obj_comp.get('table_type'):
            object_details_parts[0] = f"<strong>Type:</strong> {obj_comp['table_type']}"
        if obj_comp.get('owner'):
            object_details_parts.append(f"<strong>Owner:</strong> {obj_comp['owner']}")
        
        object_details = " | ".join(object_details_parts)
        
        # Count violations and compliant rules
        violation_count = len(non_whitelisted_violations)
        whitelisted_count_obj = len(whitelisted_violations)
        
        # For tag compliance, all tag rules for this object type apply to all objects
        applicable_rules_count = len(object_tag_rules)
        compliant_rules_count = applicable_rules_count - (violation_count + whitelisted_count_obj)
        
        # Build counts display
        counts_parts = []
        if violation_count > 0:
            counts_parts.append(f'<span class="count-badge count-violations">{violation_count} Violation{"s" if violation_count != 1 else ""}</span>')
        if whitelisted_count_obj > 0:
            counts_parts.append(f'<span class="count-badge count-whitelisted">{whitelisted_count_obj} Whitelisted</span>')
        if compliant_rules_count > 0:
            counts_parts.append(f'<span class="count-badge count-compliant">{compliant_rules_count} Compliant</span>')
        
        counts_html = " ".join(counts_parts) if counts_parts else '<span class="count-badge count-compliant">All Rules Compliant</span>'
        
        # Display object card
        card_class = f"{card_theme}-compact compliant" if is_compliant else f"{card_theme}-compact non-compliant"
        
        with st.container():
            st.html(f"""
                <div class="{card_class}">
                    <div class="warehouse-name">{object_name}</div>
                    <div class="warehouse-info">{object_details}</div>
                    <div class="counts-container" style="margin-top: 6px;">{counts_html}</div>
                </div>
            """)
            
            # Show assigned tags
            if obj_comp['assigned_tags']:
                tags_html = " ".join([f'<span class="tag-badge">{tag}</span>' for tag in obj_comp['assigned_tags']])
                st.html(f"""
                    <div class="tag-container">
                        <strong>Assigned Tags:</strong> {tags_html}
                    </div>
                """)
            else:
                st.html(f"""
                    <div class="tag-container">
                        <em>No tags assigned</em>
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
                                        <div class="violation-rule-name">Missing Tag {whitelisted_badge}</div>
                                        <div class="violation-details">
                                            <div class="violation-value">
                                                <span class="violation-label">Tag:</span>
                                                <span class="violation-code">{violation['tag_name']}</span>
                                            </div>
                                            <div class="violation-value">
                                                <span class="violation-label">-</span>
                                                <span style="color: #757575; font-size: 0.85rem;">{violation['rule_description']}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            """)
                        
                        with vcol2:
                            # Add whitelist button only for non-whitelisted violations
                            if not is_whitelisted:
                                st.html('<div class="whitelist-button-wrapper">')
                                if st.button("Whitelist", key=f"whitelist_tag_{object_name.replace('.', '_')}_{idx}", 
                                           help="Whitelist this violation",
                                           type="secondary"):
                                    try:
                                        # Extract database, schema, table names from obj_comp
                                        db_name = obj_comp.get('object_database')
                                        schema_name = obj_comp.get('object_schema')
                                        table_name = None
                                        
                                        # For tables, extract table name from object_name
                                        if object_type == 'TABLE' and '.' in object_name:
                                            parts = object_name.split('.')
                                            if len(parts) == 3:
                                                table_name = parts[2]
                                        
                                        add_to_whitelist(
                                            session,
                                            rule_id='MISSING_TAG_VALUE',
                                            applied_rule_id=violation.get('applied_tag_rule_id'),
                                            object_type=object_type,
                                            object_name=object_name,
                                            database_name=db_name,
                                            schema_name=schema_name,
                                            table_name=table_name,
                                            tag_name=violation['tag_name'],
                                            reason=f"Whitelisted from UI"
                                        )
                                        st.success(f"Violation whitelisted for {object_name}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error whitelisting: {str(e)}")
                                st.html('</div>')
                
                with col2:
                    # Create unique key for buttons
                    obj_key = object_name.replace('.', '_').replace(' ', '_')
                    
                    # Only show SQL button (no fix button for tags)
                    if st.button("Show SQL", key=f"sql_{obj_key}", use_container_width=True):
                        st.session_state[f'show_sql_{obj_key}'] = True
                
                # Show SQL if button was clicked
                if st.session_state.get(f'show_sql_{obj_key}', False):
                    with st.expander("SQL Statement", expanded=True):
                        # Generate SQL for each missing tag
                        for violation in obj_comp['violations']:
                            fix_sql = generate_tag_fix_sql(
                                object_name,
                                object_type,
                                violation['tag_name']
                            )
                            st.code(fix_sql, language="sql")
                        
                        # Add close button
                        if st.button("Close", key=f"close_sql_{obj_key}"):
                            st.session_state[f'show_sql_{obj_key}'] = False
                            st.rerun()
            
            st.html("<br>")
