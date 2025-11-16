"""
Compliance View Tab
Displays warehouse compliance status against applied rules
"""

import streamlit as st
import pandas as pd
from database import get_applied_rules, get_warehouse_details, execute_sql, get_wh_statement_timeout_default
from compliance import check_wh_compliance, generate_wh_fix_sql, generate_wh_post_fix_update_sql
from ui_utils import render_refresh_button, render_section_header, render_filter_button, filter_by_search


def render_wh_compliance_view_tab(session):
    """Render the Compliance View tab"""
    # Initialize session state for fixed warehouses
    if 'fixed_warehouses' not in st.session_state:
        st.session_state.fixed_warehouses = {}
    
    # Initialize filter state
    if 'wh_compliance_filter' not in st.session_state:
        st.session_state.wh_compliance_filter = "All Warehouses"
    
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab2")
    with col_title:
        render_section_header("Warehouse Compliance", "wh-icon")
    with col_refresh:
        if st.button("⟳", key="refresh_tab2", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    applied_rules_df = get_applied_rules(session)
    
    if applied_rules_df.empty:
        st.info("No rules applied yet. Go to 'Rule Configuration' tab to apply rules.")
    else:
        warehouse_df = get_warehouse_details(session)
        
        if warehouse_df.empty:
            st.warning("No warehouse data available. The monitoring task may not have run yet.")
        else:
            compliance_data = check_wh_compliance(warehouse_df, applied_rules_df)
            
            # Summary metrics
            total_warehouses = len(compliance_data)
            non_compliant_warehouses = len([wh for wh in compliance_data if wh['violations']])
            compliant_warehouses = total_warehouses - non_compliant_warehouses
            compliance_rate = (compliant_warehouses / total_warehouses * 100) if total_warehouses > 0 else 0
            
            # Metrics as clickable styled buttons
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                render_filter_button("Total Warehouses", total_warehouses, "filter_all_btn", "All Warehouses", "wh_compliance_filter")
            
            with col2:
                render_filter_button("Compliant", compliant_warehouses, "filter_compliant_btn", "Compliant Only", "wh_compliance_filter")
            
            with col3:
                render_filter_button("Non-Compliant", non_compliant_warehouses, "filter_non_compliant_btn", "Non-Compliant Only", "wh_compliance_filter")
            
            with col4:
                render_filter_button("Compliance Rate", f"{compliance_rate:.1f}%", "filter_rate_btn", "Non-Compliant First", "wh_compliance_filter")
            
            st.html("<br>")
            
            # Search box
            search_term = st.text_input("Search warehouses or rules", placeholder="Type warehouse name or rule name...", key="wh_search")
            
            st.markdown("---")
            
            # Display warehouse compliance in tile view
            _render_tile_view(session, compliance_data, st.session_state.wh_compliance_filter, search_term)




def _render_tile_view(session, compliance_data, view_filter, search_term=""):
    """Render tile view of warehouse compliance"""
    # Sort data if "Non-Compliant First" is selected
    if view_filter == "Non-Compliant First":
        compliance_data = sorted(compliance_data, key=lambda x: (len(x['violations']) == 0, x['warehouse_name']))
    
    for wh_comp in compliance_data:
        has_violations = len(wh_comp['violations']) > 0
        warehouse_name = wh_comp['warehouse_name']
        
        # Apply search filter
        if search_term:
            search_lower = search_term.lower()
            # Search in warehouse name and rule names
            rule_names = [v['rule_name'].lower() for v in wh_comp['violations']]
            if (search_lower not in warehouse_name.lower() and 
                not any(search_lower in rule for rule in rule_names)):
                continue
        
        # Apply status filter (skip for "Non-Compliant First" which shows all)
        if view_filter == "Non-Compliant Only" and not has_violations:
            continue
        elif view_filter == "Compliant Only" and has_violations:
            continue
        
        # Check if this warehouse was recently fixed
        if warehouse_name in st.session_state.fixed_warehouses:
            fix_status = st.session_state.fixed_warehouses[warehouse_name]
            
            # Display success or error card
            if fix_status['success']:
                st.html(f"""
                    <div class="warehouse-compact compliant">
                        <div class="warehouse-name">{warehouse_name}</div>
                        <div class="warehouse-info" style="color: #2E7D32; font-weight: 500;">
                            ✓ Configuration Updated
                        </div>
                    </div>
                """)
            else:
                st.html(f"""
                    <div class="warehouse-compact non-compliant">
                        <div class="warehouse-name">{warehouse_name}</div>
                        <div class="warehouse-info" style="color: #C62828;">
                            ✗ Fix Failed: {fix_status['error']}
                        </div>
                    </div>
                """)
            
            st.html("<br>")
            continue
        
        # Display warehouse card - compact version
        card_class = "warehouse-compact non-compliant" if has_violations else "warehouse-compact compliant"
        
        with st.container():
            st.markdown(f"""
                <div class="{card_class}">
                    <div class="warehouse-name">{warehouse_name}</div>
                    <div class="warehouse-info">
                        <strong>Type:</strong> {wh_comp['warehouse_type']} | 
                        <strong>Size:</strong> {wh_comp['warehouse_size']} | 
                        <strong>Owner:</strong> {wh_comp['warehouse_owner']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if has_violations:
                # Show violations in compact format
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    for violation in wh_comp['violations']:
                        current_val = violation['current_value'] if violation['current_value'] is not None else "Not Set"
                        st.html(f"""
                            <div class="violation-item">
                                <div>
                                    <div class="violation-rule-name">{violation['rule_name']}</div>
                                    <div class="violation-details">
                                        <div class="violation-value">
                                            <span class="violation-label">Current:</span>
                                            <span class="violation-code">{current_val}</span>
                                        </div>
                                        <div class="violation-value">
                                            <span class="violation-operator">{violation['operator']}</span>
                                        </div>
                                        <div class="violation-value">
                                            <span class="violation-label">Required:</span>
                                            <span class="violation-code">{int(violation['threshold_value'])} {violation['unit']}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        """)
                
                with col2:
                    # Check if any violation has fix_button or fix_sql enabled
                    has_any_fix_button = any(v.get('has_fix_button', False) for v in wh_comp['violations'])
                    has_any_fix_sql = any(v.get('has_fix_sql', False) for v in wh_comp['violations'])
                    
                    if has_any_fix_button or has_any_fix_sql:
                        if has_any_fix_button:
                            if st.button("Fix", key=f"fix_{warehouse_name}", type="primary", use_container_width=True):
                                # Execute the fix SQL
                                try:
                                    # Step 1: Run the fix SQL
                                    for violation in wh_comp['violations']:
                                        if violation.get('has_fix_button', False):
                                            sql = generate_wh_fix_sql(
                                                warehouse_name,
                                                violation['parameter'],
                                                violation['threshold_value'] if violation['rule_id'] != 'ZERO_STATEMENT_TIMEOUT' else st.session_state.wh_default_timeout
                                            )
                                            execute_sql(session, sql)
                                            update_sql = generate_wh_post_fix_update_sql(
                                                warehouse_name,
                                                violation['parameter'],
                                                violation['threshold_value'] if violation['rule_id'] != 'ZERO_STATEMENT_TIMEOUT' else st.session_state.wh_default_timeout
                                            )
                                            execute_sql(session, update_sql)
                                    
                                    # Step 2: Mark as successfully fixed in session state
                                    st.session_state.fixed_warehouses[warehouse_name] = {
                                        'success': True,
                                        'error': None
                                    }
                                    st.rerun()
                                    
                                except Exception as e:
                                    # Step 3: Mark as failed with error message
                                    st.session_state.fixed_warehouses[warehouse_name] = {
                                        'success': False,
                                        'error': str(e)
                                    }
                                    st.rerun()
                        
                        if has_any_fix_sql:
                            if st.button("Show SQL", key=f"btn_show_sql_{warehouse_name}", use_container_width=True):
                                st.session_state[f'show_sql_{warehouse_name}'] = True
                        
                        # Display SQL if requested
                        if st.session_state.get(f'show_sql_{warehouse_name}', False):
                            sql_statements = []
                            for violation in wh_comp['violations']:
                                if violation.get('has_fix_sql', False):
                                    sql = generate_wh_fix_sql(
                                        warehouse_name,
                                        violation['parameter'],
                                        violation['threshold_value']
                                    )
                                    sql_statements.append(sql)
                            
                            if sql_statements:
                                combined_sql = "\n\n".join(sql_statements)
                                st.code(combined_sql, language="sql")
                                
                                if st.button("Hide SQL", key=f"btn_hide_sql_{warehouse_name}"):
                                    st.session_state[f'show_sql_{warehouse_name}'] = False
                                    st.rerun()
            
            st.html("<br>")
