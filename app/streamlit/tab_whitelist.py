"""
Whitelist Management Tab
Displays all whitelisted violations and allows bulk management
"""

import streamlit as st
import pandas as pd
from database import get_whitelisted_violations, bulk_remove_from_whitelist
from ui_utils import render_refresh_button, render_section_header


def render_whitelist_tab(session):
    """Render the Whitelist Management tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_whitelist")
    with col_title:
        render_section_header("Whitelist Management", "settings-icon")
    with col_refresh:
        if st.button("↻", key="refresh_tab_whitelist", help="Refresh data", type="secondary"):
            st.rerun()
    st.markdown("---")
    
    # Get all whitelisted violations
    try:
        whitelist_df = get_whitelisted_violations(session)
    except Exception as e:
        st.error(f"Error loading whitelists: {str(e)}")
        return
    
    if whitelist_df.empty:
        st.info("No whitelisted violations found. Whitelist violations from the compliance tabs to manage them here.")
        return
    
    # Summary metrics
    total_whitelists = len(whitelist_df)
    by_type = whitelist_df.groupby('OBJECT_TYPE').size().to_dict()
    by_rule = whitelist_df.groupby('RULE_NAME').size().to_dict()
    
    # Display summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Whitelisted", total_whitelists)
    
    with col2:
        st.metric("Warehouses", by_type.get('WAREHOUSE', 0))
    
    with col3:
        st.metric("Databases", by_type.get('DATABASE', 0))
    
    with col4:
        st.metric("Tables", by_type.get('TABLE', 0))
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_type = st.selectbox(
            "Filter by Object Type",
            ["All"] + sorted(whitelist_df['OBJECT_TYPE'].unique().tolist()),
            key="whitelist_type_filter"
        )
    
    with col2:
        # Filter out None values before sorting
        rule_names = [r for r in whitelist_df['RULE_NAME'].unique().tolist() if r is not None]
        filter_rule = st.selectbox(
            "Filter by Rule",
            ["All"] + sorted(rule_names),
            key="whitelist_rule_filter"
        )
    
    with col3:
        search_term = st.text_input(
            "Search object name",
            placeholder="Type to search...",
            key="whitelist_search"
        )
    
    # Apply filters
    filtered_df = whitelist_df.copy()
    
    if filter_type != "All":
        filtered_df = filtered_df[filtered_df['OBJECT_TYPE'] == filter_type]
    
    if filter_rule != "All":
        filtered_df = filtered_df[filtered_df['RULE_NAME'] == filter_rule]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['OBJECT_NAME'].str.contains(search_term, case=False, na=False)
        ]
    
    st.markdown(f"**Showing {len(filtered_df)} of {total_whitelists} whitelisted violations**")
    st.markdown("---")
    
    if filtered_df.empty:
        st.info("No whitelisted violations match your filters.")
        return
    
    # Multi-select interface
    st.markdown("### Select Violations to Remove from Whitelist")
    st.caption("Select one or more violations below and click 'Remove Selected from Whitelist' to reactivate compliance checking.")
    
    # Initialize session state for selections
    if 'selected_whitelists' not in st.session_state:
        st.session_state.selected_whitelists = []
    
    # Select All / Deselect All buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("Select All", use_container_width=True):
            st.session_state.selected_whitelists = filtered_df['WHITELIST_ID'].tolist()
            st.rerun()
    
    with col2:
        if st.button("Deselect All", use_container_width=True):
            st.session_state.selected_whitelists = []
            st.rerun()
    
    st.markdown("---")
    
    # Display whitelisted violations with checkboxes
    for _, row in filtered_df.iterrows():
        whitelist_id = row['WHITELIST_ID']
        
        # Determine card color based on object type
        if row['OBJECT_TYPE'] == 'WAREHOUSE':
            card_class = "warehouse-card"
            icon = '<span class="wh-icon"></span>'
        elif row['OBJECT_TYPE'] == 'DATABASE':
            card_class = "database-card"
            icon = '<span class="db-icon"></span>'
        elif row['OBJECT_TYPE'] == 'SCHEMA':
            card_class = "schema-card"
            icon = '<span class="db-icon"></span>'
        else:  # TABLE
            card_class = "table-card"
            icon = '<span class="db-icon"></span>'
        
        # Create checkbox and details in columns
        col1, col2 = st.columns([0.5, 9.5])
        
        with col1:
            is_selected = whitelist_id in st.session_state.selected_whitelists
            if st.checkbox("", value=is_selected, key=f"cb_{whitelist_id}", label_visibility="collapsed"):
                if whitelist_id not in st.session_state.selected_whitelists:
                    st.session_state.selected_whitelists.append(whitelist_id)
            else:
                if whitelist_id in st.session_state.selected_whitelists:
                    st.session_state.selected_whitelists.remove(whitelist_id)
        
        with col2:
            # Format reason display
            reason = row['REASON'] if pd.notna(row['REASON']) else "No reason provided"
            whitelisted_by = row['WHITELISTED_BY'] if pd.notna(row['WHITELISTED_BY']) else "Unknown"
            whitelisted_at = row['WHITELISTED_AT'].strftime('%Y-%m-%d %H:%M') if pd.notna(row['WHITELISTED_AT']) else "Unknown"
            
            # Add tag name for tag compliance violations
            tag_info = ""
            if row['RULE_ID'] == 'MISSING_TAG_VALUE' and pd.notna(row.get('TAG_NAME')):
                tag_info = f"<strong>Missing Tag:</strong> {row['TAG_NAME']} | "
            
            # Determine rule name - use RULE_NAME if available, otherwise use RULE_ID for tag rules
            rule_display = row['RULE_NAME'] if pd.notna(row.get('RULE_NAME')) else row['RULE_ID']
            rule_type_display = row['RULE_TYPE'] if pd.notna(row.get('RULE_TYPE')) else 'TAG'
            
            st.html(f"""
                <div class="{card_class}" style="margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 0.5rem 0;">
                                {icon} {row['OBJECT_NAME']}
                                <span class="rule-type-label {row['OBJECT_TYPE'].lower()}">{row['OBJECT_TYPE']}</span>
                            </h4>
                            <p style="margin: 0.3rem 0;">
                                {tag_info}<strong>Rule:</strong> {rule_display} | 
                                <strong>Rule Type:</strong> {rule_type_display}
                            </p>
                            <p style="margin: 0.3rem 0; font-size: 0.85rem; color: #666;">
                                <strong>Reason:</strong> {reason}
                            </p>
                            <p style="margin: 0.3rem 0; font-size: 0.8rem; color: #888;">
                                <strong>Whitelisted by:</strong> {whitelisted_by} | 
                                <strong>Date:</strong> {whitelisted_at}
                            </p>
                        </div>
                    </div>
                </div>
            """)
    
    st.markdown("---")
    
    # Bulk actions
    if st.session_state.selected_whitelists:
        st.markdown(f"**{len(st.session_state.selected_whitelists)} violation(s) selected**")
        
        col1, col2, col3 = st.columns([2, 2, 6])
        
        with col1:
            if st.button("Remove Selected from Whitelist", type="primary", use_container_width=True, key="remove_selected_btn"):
                try:
                    bulk_remove_from_whitelist(session, st.session_state.selected_whitelists)
                    st.success(f"Successfully removed {len(st.session_state.selected_whitelists)} violation(s) from whitelist!")
                    st.session_state.selected_whitelists = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Error removing from whitelist: {str(e)}")
        
        with col2:
            if st.button("Cancel", use_container_width=True, key="cancel_selected_btn"):
                st.session_state.selected_whitelists = []
                st.rerun()
    else:
        st.info("Select one or more violations above to remove them from the whitelist")
