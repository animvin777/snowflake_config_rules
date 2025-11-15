"""
Compliance View Tab
Displays warehouse compliance status against applied rules
"""

import streamlit as st
import pandas as pd
from database import get_applied_rules, get_warehouse_details, execute_sql
from compliance import check_compliance, generate_fix_sql, generate_post_fix_update_sql
from ui_utils import render_refresh_button


def render_wh_compliance_view_tab(session):
    """Render the Compliance View tab"""
    # Initialize session state for fixed warehouses
    if 'fixed_warehouses' not in st.session_state:
        st.session_state.fixed_warehouses = {}
    
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab2")
    with col_title:
        st.markdown("### 🏭 Warehouse Configuration Health")
    with col_refresh:
        if st.button("🔄", key="refresh_tab2", help="Refresh data"):
            # Clear fixed warehouses on refresh
            st.session_state.fixed_warehouses = {}
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
            compliance_data = check_compliance(warehouse_df, applied_rules_df)
            
            # Summary metrics
            total_warehouses = len(compliance_data)
            non_compliant_warehouses = len([wh for wh in compliance_data if wh['violations']])
            compliant_warehouses = total_warehouses - non_compliant_warehouses
            compliance_rate = (compliant_warehouses / total_warehouses * 100) if total_warehouses > 0 else 0
            
            # Metrics in styled cards
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                    <div class="metric-card">
                        <h3>{total_warehouses}</h3>
                        <p>Total Warehouses</p>
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                    <div class="metric-card success">
                        <h3>{compliant_warehouses}</h3>
                        <p>Compliant</p>
                    </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                    <div class="metric-card error">
                        <h3>{non_compliant_warehouses}</h3>
                        <p>Non-Compliant</p>
                    </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                    <div class="metric-card warning">
                        <h3>{compliance_rate:.1f}%</h3>
                        <p>Compliance Rate</p>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Filter and view options
            col1, col2 = st.columns([2, 1])
            with col1:
                view_filter = st.radio(
                    "Filter",
                    ["All Warehouses", "Non-Compliant Only", "Compliant Only"],
                    horizontal=True,
                    key="compliance_filter"
                )
            with col2:
                # Add view toggle (Tile or List)
                view_mode = st.radio(
                    "View Mode",
                    ["🔲 Tile View", "📋 List View"],
                    horizontal=True,
                    key="view_mode",
                    index=0  # Default to Tile View
                )
            
            st.markdown("---")
            
            # Display warehouse compliance based on view mode
            if view_mode == "📋 List View":
                _render_list_view(compliance_data, view_filter)
            else:
                _render_tile_view(session, compliance_data, view_filter)


def _render_list_view(compliance_data, view_filter):
    """Render list view of warehouse compliance"""
    list_data = []
    for wh_comp in compliance_data:
        has_violations = len(wh_comp['violations']) > 0
        
        # Apply filter
        if view_filter == "Non-Compliant Only" and not has_violations:
            continue
        elif view_filter == "Compliant Only" and has_violations:
            continue
        
        status = "Non-Compliant" if has_violations else "Compliant"
        violations_text = ", ".join([v['rule_name'] for v in wh_comp['violations']]) if has_violations else "-"
        
        list_data.append({
            'Status': status,
            'Warehouse': wh_comp['warehouse_name'],
            'Type': wh_comp['warehouse_type'],
            'Size': wh_comp['warehouse_size'],
            'Owner': wh_comp['warehouse_owner'],
            'Violations': violations_text
        })
    
    if list_data:
        df_display = pd.DataFrame(list_data)
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Warehouse": st.column_config.TextColumn("Warehouse", width="medium"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Size": st.column_config.TextColumn("Size", width="small"),
                "Owner": st.column_config.TextColumn("Owner", width="medium"),
                "Violations": st.column_config.TextColumn("Violations", width="large"),
            }
        )
    else:
        st.info("No warehouses match the selected filter.")


def _render_tile_view(session, compliance_data, view_filter):
    """Render tile view of warehouse compliance"""
    for wh_comp in compliance_data:
        has_violations = len(wh_comp['violations']) > 0
        
        # Apply filter
        if view_filter == "Non-Compliant Only" and not has_violations:
            continue
        elif view_filter == "Compliant Only" and has_violations:
            continue
        
        warehouse_name = wh_comp['warehouse_name']
        
        # Check if this warehouse was recently fixed
        if warehouse_name in st.session_state.fixed_warehouses:
            fix_status = st.session_state.fixed_warehouses[warehouse_name]
            
            # Display success or error card
            if fix_status['success']:
                st.markdown(f"""
                    <div class="warehouse-compact compliant">
                        <div class="warehouse-name">{warehouse_name}</div>
                        <div class="warehouse-info" style="color: #2E7D32; font-weight: 500;">
                            ✓ Configuration Updated
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="warehouse-compact non-compliant">
                        <div class="warehouse-name">{warehouse_name}</div>
                        <div class="warehouse-info" style="color: #C62828;">
                            ✗ Fix Failed: {fix_status['error']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
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
                        st.markdown(f"""
                            <div class="warehouse-violations">
                                <strong>{violation['rule_name']}:</strong> 
                                Current = <code>{current_val}</code>, 
                                Required {violation['operator']} = <code>{int(violation['threshold_value'])} {violation['unit']}</code>
                            </div>
                        """, unsafe_allow_html=True)
                
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
                                            sql = generate_fix_sql(
                                                warehouse_name,
                                                violation['parameter'],
                                                violation['threshold_value']
                                            )
                                            execute_sql(session, sql)
                                            update_sql = generate_post_fix_update_sql(
                                                warehouse_name,
                                                violation['parameter'],
                                                violation['threshold_value']
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
                                    sql = generate_fix_sql(
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
            
            st.markdown("<br>", unsafe_allow_html=True)
