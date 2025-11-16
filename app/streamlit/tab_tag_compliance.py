"""
Tag Compliance Tab
Handles the display of tag compliance status for warehouses, databases, and tables
"""

import streamlit as st
from database import get_applied_tag_rules, get_tag_compliance_details, get_all_objects_by_type
from compliance import check_tag_compliance, generate_tag_fix_sql
from ui_utils import render_refresh_button, render_section_header, render_filter_button


def render_tag_compliance_tab(session):
    """Render the Tag Compliance tab"""
    # Initialize filter state
    if 'tag_compliance_filter' not in st.session_state:
        st.session_state.tag_compliance_filter = "All Objects"
    
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_tag_compliance")
    with col_title:
        render_section_header("Tag Compliance", "tag-icon")
    with col_refresh:
        if st.button("⟳", key="refresh_tab_tag_compliance", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    # Get applied tag rules
    tag_rules_df = get_applied_tag_rules(session)
    
    if tag_rules_df.empty:
        st.info("No tag rules have been applied yet. Go to the Rule Configuration tab to apply tag rules.")
        return
    
    # Object type selection
    col1, col2 = st.columns([1, 3])
    with col1:
        object_type_filter = st.selectbox(
            "Select Object Type",
            ["WAREHOUSE", "DATABASE", "TABLE"],
            key="tag_object_type_filter"
        )
    with col2:
        search_text = st.text_input("Search by object name or tag name", placeholder="Type to search...", key="tag_search")
    
    # Get tag rules for selected object type
    object_tag_rules = tag_rules_df[tag_rules_df['OBJECT_TYPE'] == object_type_filter]
    
    if object_tag_rules.empty:
        st.info(f"No tag rules have been applied for {object_type_filter}s yet.")
        return
    
    # Get all objects of the selected type
    all_objects_df = get_all_objects_by_type(session, object_type_filter)
    
    if all_objects_df.empty:
        st.warning(f"No {object_type_filter.lower()}s found in the account.")
        return
    
    # Get tag assignments for the selected object type
    tag_assignments_df = get_tag_compliance_details(session, object_type_filter)
    
    # Check compliance
    compliance_data = check_tag_compliance(all_objects_df, tag_assignments_df, object_tag_rules)
    
    # Calculate summary statistics
    total_objects = len(compliance_data)
    non_compliant_objects = sum(1 for obj in compliance_data if obj['violations'])
    compliant_objects = total_objects - non_compliant_objects
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_filter_button("Total Objects", total_objects, "filter_all_tag_objects_btn", "All Objects", "tag_compliance_filter")
    
    with col2:
        render_filter_button("Compliant", compliant_objects, "filter_compliant_tag_objects_btn", "Compliant Only", "tag_compliance_filter")
    
    with col3:
        render_filter_button("Non-Compliant", non_compliant_objects, "filter_non_compliant_tag_objects_btn", "Non-Compliant Only", "tag_compliance_filter")
    
    with col4:
        # Calculate compliance rate
        compliance_rate = (compliant_objects / total_objects * 100) if total_objects > 0 else 0
        render_filter_button("Compliance Rate", f"{compliance_rate:.1f}%", "filter_rate_tag_objects_btn", "Non-Compliant First", "tag_compliance_filter")
    
    st.html("<br>")
    st.markdown("---")
    
    # Filter compliance data based on status selection
    view_filter = st.session_state.tag_compliance_filter
    filtered_data = compliance_data.copy()
    
    # Sort if "Non-Compliant First" is selected
    if view_filter == "Non-Compliant First":
        filtered_data = sorted(filtered_data, key=lambda x: (len(x['violations']) == 0, x['object_name']))
    elif view_filter == "Non-Compliant Only":
        filtered_data = [obj for obj in filtered_data if obj['violations']]
    elif view_filter == "Compliant Only":
        filtered_data = [obj for obj in filtered_data if not obj['violations']]
    
    # Apply search filter
    if search_text:
        search_lower = search_text.lower()
        filtered_data = [
            obj for obj in filtered_data 
            if (search_lower in obj['object_name'].lower() 
                or any(search_lower in tag.lower() for tag in obj.get('assigned_tags', []))
                or any(search_lower in v.get('tag_name', '').lower() for v in obj.get('violations', [])))
        ]
    
    # Display results
    if not filtered_data:
        st.info("No objects match the selected filters.")
        return
    
    st.markdown(f"#### Showing {len(filtered_data)} {object_type_filter}s")
    
    # Determine color scheme based on object type
    if object_type_filter == "WAREHOUSE":
        card_theme = "warehouse"
    elif object_type_filter == "DATABASE":
        card_theme = "database"
    else:  # TABLE
        card_theme = "tag"
    
    # Display objects
    for obj_comp in filtered_data:
        # Determine if compliant
        is_compliant = not obj_comp['violations']
        
        object_name = obj_comp['object_name']
        object_type = obj_comp['object_type']
        
        # Build object details
        object_details_parts = [f"<strong>Type:</strong> {object_type}"]
        if obj_comp.get('table_type'):
            object_details_parts[0] = f"<strong>Type:</strong> {obj_comp['table_type']}"
        if obj_comp.get('owner'):
            object_details_parts.append(f"<strong>Owner:</strong> {obj_comp['owner']}")
        
        object_details = " | ".join(object_details_parts)
        
        # Display object card
        card_class = f"{card_theme}-compact compliant" if is_compliant else f"{card_theme}-compact non-compliant"
        
        with st.container():
            st.markdown(f"""
                <div class="{card_class}">
                    <div class="warehouse-name">{object_name}</div>
                    <div class="warehouse-info">{object_details}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Show assigned tags
            if obj_comp['assigned_tags']:
                tags_html = " ".join([f'<span class="tag-badge">{tag}</span>' for tag in obj_comp['assigned_tags']])
                st.markdown(f"""
                    <div class="tag-container">
                        <strong>Assigned Tags:</strong> {tags_html}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="tag-container">
                        <em>No tags assigned</em>
                    </div>
                """, unsafe_allow_html=True)
            
            # Show violations if any
            if obj_comp['violations']:
                # Show violations in compact format
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    for violation in obj_comp['violations']:
                        st.html(f"""
                            <div class="violation-item">
                                <div>
                                    <div class="violation-rule-name">Missing Tag</div>
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
