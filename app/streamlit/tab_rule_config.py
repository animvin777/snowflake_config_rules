"""
Rule Configuration Tab
Handles the display and management of configuration rules
"""

import streamlit as st
from database import get_config_rules, get_applied_rules, apply_rule, deactivate_applied_rule, get_warehouse_details, get_database_retention_details
from compliance import check_compliance, generate_fix_sql, check_table_compliance, generate_table_fix_sql
from ui_utils import render_refresh_button


def render_rule_configuration_tab(session):
    """Render the Rule Configuration tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab1")
    with col_title:
        st.markdown("### 🎯 Define Your Configuration Standards")
    with col_refresh:
        if st.button("🔄", key="refresh_tab1", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    # Display available rules in a nicer format
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📋 Available Compliance Rules")
    with col2:
        st.markdown("")
    
    rules_df = get_config_rules(session)
    
    if not rules_df.empty:
        # Group rules by type
        warehouse_rules = rules_df[rules_df['RULE_TYPE'] == 'Warehouse']
        database_rules = rules_df[rules_df['RULE_TYPE'] == 'Database']
        
        # Display Warehouse rules
        if not warehouse_rules.empty:
            st.markdown("##### 🏭 Warehouse Rules")
            for _, rule in warehouse_rules.iterrows():
                with st.expander(f"{rule['RULE_NAME']}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Parameter:** `{rule['WAREHOUSE_PARAMETER']}`")
                    with col2:
                        st.markdown(f"**Operator:** `{rule['COMPARISON_OPERATOR']}`")
                    with col3:
                        st.markdown(f"**Unit:** `{rule['UNIT']}`")
                    st.markdown(f"**Description:** {rule['RULE_DESCRIPTION']}")
        
        # Display Database rules
        if not database_rules.empty:
            st.markdown("##### 🗄️ Database Rules")
            for _, rule in database_rules.iterrows():
                with st.expander(f"{rule['RULE_NAME']}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Parameter:** `{rule['WAREHOUSE_PARAMETER']}`")
                    with col2:
                        st.markdown(f"**Operator:** `{rule['COMPARISON_OPERATOR']}`")
                    with col3:
                        st.markdown(f"**Unit:** `{rule['UNIT']}`")
                    st.markdown(f"**Description:** {rule['RULE_DESCRIPTION']}")
        
        st.markdown("---")
        
        # Apply new rule in a prominent card
        st.markdown("#### ⚡ Apply Configuration Rules")
        
        # Add "Apply Default Rules" button
        col_manual, col_default = st.columns([3, 1])
        
        with col_default:
            if st.button("🎯 Apply Default Rules", type="secondary", use_container_width=True, help="Apply recommended default values for all rules"):
                try:
                    # Default rule values
                    default_rules = {
                        'MAX_STATEMENT_TIMEOUT': 300,     # 300 seconds
                        'MAX_AUTO_SUSPEND': 30,           # 30 seconds
                        'MAX_TABLE_RETENTION_TIME': 1,    # 1 day
                        'MAX_SCHEMA_RETENTION_TIME': 1,   # 1 day
                        'MAX_DATABASE_RETENTION_TIME': 1, # 1 day
                    }
                    
                    success_count = 0
                    for rule_id, threshold in default_rules.items():
                        try:
                            apply_rule(session, rule_id, threshold)
                            success_count += 1
                        except Exception as e:
                            st.warning(f"Could not apply {rule_id}: {str(e)}")
                    
                    if success_count > 0:
                        st.success(f"✅ Successfully applied {success_count} default rules!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error applying default rules: {str(e)}")
        
        with col_manual:
            st.markdown("**Or manually configure a rule below:**")
        
        with st.container():
            col1, col2 = st.columns([2, 1])
            
            with col1:
                selected_rule = st.selectbox(
                    "Select Rule to Apply",
                    rules_df['RULE_ID'].tolist(),
                    format_func=lambda x: rules_df[rules_df['RULE_ID'] == x]['RULE_NAME'].iloc[0],
                    key="rule_selector"
                )
            
            with col2:
                if selected_rule:
                    rule_info = rules_df[rules_df['RULE_ID'] == selected_rule].iloc[0]
                    threshold_value = st.number_input(
                        f"Threshold ({rule_info['UNIT']})",
                        min_value=0,
                        value=300,
                        step=10,
                        help=f"Set the {rule_info['COMPARISON_OPERATOR']} value"
                    )
            
            if selected_rule:
                rule_info = rules_df[rules_df['RULE_ID'] == selected_rule].iloc[0]
                st.info(f"💡 **{rule_info['RULE_NAME']}**: {rule_info['RULE_DESCRIPTION']}")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("Apply Rule", type="primary", use_container_width=True):
                        try:
                            apply_rule(session, selected_rule, threshold_value)
                            st.success(f"Rule '{rule_info['RULE_NAME']}' applied with threshold: {threshold_value} {rule_info['UNIT']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error applying rule: {str(e)}")
    else:
        st.warning("No configuration rules available")
    
    st.markdown("---")
    
    # Display applied rules
    st.markdown("#### Currently Applied Rules")
    applied_rules_df = get_applied_rules(session)
    
    if not applied_rules_df.empty:
        for _, rule in applied_rules_df.iterrows():
            rule_type_icon = "🏭" if rule['RULE_TYPE'] == 'Warehouse' else "🗄️"
            st.markdown(f"""
                <div class="rule-card">
                    <h4 style="margin-top:0;">{rule_type_icon} {rule['RULE_NAME']} ({rule['RULE_TYPE']})</h4>
                    <p style="margin-bottom:0.5rem;"><strong>Threshold:</strong> {int(rule['THRESHOLD_VALUE'])} {rule['UNIT']} | <strong>Applied:</strong> {rule['APPLIED_AT'].strftime('%Y-%m-%d %H:%M')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Determine column layout based on has_fix_sql
            has_fix_sql = rule.get('HAS_FIX_SQL', False)
            
            if has_fix_sql:
                col1, col2, col3 = st.columns([3, 1, 1])
            else:
                col1, col2 = st.columns([4, 1])
            
            # Show Generate SQL button only if has_fix_sql is True
            if has_fix_sql:
                with col2:
                    if st.button("Generate SQL", key=f"btn_sql_{rule['APPLIED_RULE_ID']}", help="Generate SQL for all non-compliant objects", use_container_width=True):
                        st.session_state[f'show_sql_{rule["APPLIED_RULE_ID"]}'] = True
            
            # Deactivate button position depends on whether SQL button exists
            with col3 if has_fix_sql else col2:
                if st.button("Deactivate", key=f"deact_{rule['APPLIED_RULE_ID']}", type="secondary", use_container_width=True):
                    try:
                        deactivate_applied_rule(session, rule['APPLIED_RULE_ID'])
                        st.success("Rule deactivated")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            # Show SQL if button was clicked
            if st.session_state.get(f'show_sql_{rule["APPLIED_RULE_ID"]}', False):
                if rule['RULE_TYPE'] == 'Warehouse':
                    # Generate SQL for warehouse rules
                    warehouse_df = get_warehouse_details(session)
                    compliance_data = check_compliance(warehouse_df, applied_rules_df[applied_rules_df['RULE_ID'] == rule['RULE_ID']])
                    
                    sql_statements = []
                    for wh_comp in compliance_data:
                        for violation in wh_comp['violations']:
                            if violation['rule_id'] == rule['RULE_ID']:
                                sql = generate_fix_sql(
                                    wh_comp['warehouse_name'],
                                    violation['parameter'],
                                    violation['threshold_value']
                                )
                                sql_statements.append(sql)
                    
                    if sql_statements:
                        combined_sql = "\n\n".join(sql_statements)
                        st.code(combined_sql, language="sql")
                    else:
                        st.success("All warehouses are compliant with this rule")
                
                else:  # Database rules
                    # Generate SQL for database/schema/table rules
                    retention_df = get_database_retention_details(session)
                    compliance_data = check_table_compliance(retention_df, applied_rules_df[applied_rules_df['RULE_ID'] == rule['RULE_ID']])
                    
                    sql_statements = []
                    for obj_comp in compliance_data:
                        for violation in obj_comp['violations']:
                            if violation['rule_id'] == rule['RULE_ID']:
                                sql = generate_table_fix_sql(
                                    obj_comp['database_name'],
                                    obj_comp.get('schema_name'),
                                    obj_comp.get('table_name'),
                                    violation['parameter'],
                                    violation['threshold_value'],
                                    obj_comp['object_type']
                                )
                                sql_statements.append(sql)
                    
                    if sql_statements:
                        combined_sql = "\n\n".join(sql_statements)
                        st.code(combined_sql, language="sql")
                    else:
                        st.success("All objects are compliant with this rule")
            
            st.markdown("---")
    else:
        st.info("No rules have been applied yet. Apply a rule above to start monitoring compliance.")
