"""
Rule Configuration Tab
Handles the display and management of configuration rules
"""

import streamlit as st
from database import get_config_rules, get_applied_rules, apply_rule, deactivate_applied_rule, get_warehouse_details
from compliance import check_compliance, generate_fix_sql
from ui_utils import render_refresh_button


def render_rule_configuration_tab(session):
    """Render the Rule Configuration tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab1")
    with col_title:
        st.markdown("### Rule Configuration")
    with col_refresh:
        if st.button("🔄", key="refresh_tab1", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    # Display available rules in a nicer format
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Available Configuration Rules")
    with col2:
        st.markdown("")
    
    rules_df = get_config_rules(session)
    
    if not rules_df.empty:
        # Display rules in expandable cards
        for _, rule in rules_df.iterrows():
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
        st.markdown("#### ⚡ Apply New Configuration Rule")
        
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
            st.markdown(f"""
                <div class="rule-card">
                    <h4 style="margin-top:0;">{rule['RULE_NAME']}</h4>
                    <p style="margin-bottom:0.5rem;"><strong>Threshold:</strong> {int(rule['THRESHOLD_VALUE'])} {rule['UNIT']} | <strong>Applied:</strong> {rule['APPLIED_AT'].strftime('%Y-%m-%d %H:%M')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col2:
                if st.button("Generate SQL", key=f"sql_{rule['APPLIED_RULE_ID']}", help="Generate SQL for all non-compliant warehouses", use_container_width=True):
                    st.session_state[f'show_sql_{rule["APPLIED_RULE_ID"]}'] = True
            
            with col3:
                if st.button("Deactivate", key=f"deact_{rule['APPLIED_RULE_ID']}", type="secondary", use_container_width=True):
                    try:
                        deactivate_applied_rule(session, rule['APPLIED_RULE_ID'])
                        st.success("Rule deactivated")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            # Show SQL if button was clicked
            if st.session_state.get(f'show_sql_{rule["APPLIED_RULE_ID"]}', False):
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
            
            st.markdown("---")
    else:
        st.info("No rules have been applied yet. Apply a rule above to start monitoring compliance.")
