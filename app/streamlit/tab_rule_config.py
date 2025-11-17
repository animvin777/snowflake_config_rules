"""
Rule Configuration Tab
Handles the display and management of configuration rules
"""

import streamlit as st
import pandas as pd
from database import (get_config_rules, get_applied_rules, apply_rule, deactivate_applied_rule, 
                      get_warehouse_details, get_database_retention_details, get_wh_statement_timeout_default,
                      get_available_tag_names,get_available_tags, get_applied_tag_rules, apply_tag_rule, deactivate_tag_rule,
                      get_tag_compliance_details, get_all_objects_by_type, get_whitelisted_violations)
from compliance import check_wh_compliance, generate_wh_fix_sql, check_table_compliance, generate_table_fix_sql, check_tag_compliance, generate_tag_fix_sql
from ui_utils import render_refresh_button, render_section_header, render_rule_card


def render_rule_configuration_tab(session):
    """Render the Rule Configuration tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab1")
    with col_title:
        render_section_header("Rule Configuration", "settings-icon")
    with col_refresh:
        if st.button("↻", key="refresh_tab1", help="Refresh data", type="secondary"):
            st.rerun()
    st.markdown("---")
    
    # Display available rules in a nicer format
    st.markdown("#### Available Configuration Rules")
    
    rules_df = get_config_rules(session)
    st.session_state.wh_default_timeout = get_wh_statement_timeout_default(session)
    
    if not rules_df.empty:
        # Create tabs for different rule types
        tab1, tab2, tab3 = st.tabs(["Database Rules", "Warehouse Rules", "Tag Rules"])
        
        # Group rules by type
        warehouse_rules = rules_df[rules_df['RULE_TYPE'] == 'Warehouse']
        database_rules = rules_df[rules_df['RULE_TYPE'] == 'Database']
        
        # Tab 1: Database Rules
        with tab1:
            if not database_rules.empty:
                for _, rule in database_rules.iterrows():
                    with st.expander(f"{rule['RULE_NAME']}", expanded=False):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.markdown(f"**Parameter:** `{rule['CHECK_PARAMETER']}`")
                        with col2:
                            st.markdown(f"**Operator:** `{rule['COMPARISON_OPERATOR']}`")
                        with col3:
                            st.markdown(f"**Unit:** `{rule['UNIT']}`")
                        with col4:
                            default_val = rule.get('DEFAULT_THRESHOLD', 'N/A')
                            st.markdown(f"**Default:** `{default_val}`")
                        st.markdown(f"**Description:** {rule['RULE_DESCRIPTION']}")
                        st.html('<span class="db-icon"></span> **Type:** Database')
                        override_allowed = rule.get('ALLOW_THRESHOLD_OVERRIDE', True)
                        if not override_allowed:
                            st.html('<span class="warning-icon"></span> Threshold cannot be changed for this rule')
            else:
                st.info("No database rules available")
        
        # Tab 2: Warehouse Rules
        with tab2:
            if not warehouse_rules.empty:
                for _, rule in warehouse_rules.iterrows():
                    with st.expander(f"{rule['RULE_NAME']}", expanded=False):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.markdown(f"**Parameter:** `{rule['CHECK_PARAMETER']}`")
                        with col2:
                            st.markdown(f"**Operator:** `{rule['COMPARISON_OPERATOR']}`")
                        with col3:
                            st.markdown(f"**Unit:** `{rule['UNIT']}`")
                        with col4:
                            default_val = rule.get('DEFAULT_THRESHOLD', 'N/A')
                            st.markdown(f"**Default:** `{default_val}`")
                        st.markdown(f"**Description:** {rule['RULE_DESCRIPTION']}")
                        st.html('<span class="wh-icon"></span> **Type:** Warehouse')
                        override_allowed = rule.get('ALLOW_THRESHOLD_OVERRIDE', True)
                        if not override_allowed:
                            st.html('<span class="warning-icon"></span> Threshold cannot be changed for this rule')
            else:
                st.info("No warehouse rules available")
        
        # Tab 3: Tag Rules
        with tab3:
            st.markdown("**Tag Compliance Rules**")
            st.markdown("Tag rules check whether required tags are present on objects (warehouses, databases, or tables).")
            st.markdown("These rules identify missing tags but cannot be automatically fixed - SQL generation is provided for manual execution.")
            st.markdown("---")
            
            # Get available tags from Snowflake
            try:
                available_tags_df = get_available_tags(session)
                if not available_tags_df.empty:
                    st.markdown(f"**{len(available_tags_df)} tags available in the account**")
                    with st.expander("View Available Tags"):
                        for _, tag in available_tags_df.iterrows():
                            st.markdown(f"- `{tag['TAG_DATABASE']}.{tag['TAG_SCHEMA']}.{tag['TAG_NAME']}`")
                else:
                    st.warning("No tags found in SNOWFLAKE.ACCOUNT_USAGE.TAGS")
            except Exception as e:
                st.error(f"Error fetching available tags: {str(e)}")
        
        st.markdown("---")
        
        # Apply new rule in a prominent card
        st.html('<h4><span class="wh-icon"></span> Apply Configuration Rules</h4>')
        
        # Add rule type selector first
        rule_type = st.radio(
            "Select Rule Type",
            ["Database/Warehouse Rules", "Tag Rules"],
            horizontal=True,
            key="rule_type_selector"
        )
        
        st.markdown("---")
        
        if rule_type == "Database/Warehouse Rules":
            # Existing database/warehouse rule application UI
            # Add "Apply Default Rules" button
            col_manual, col_default = st.columns([3, 1])
            
            with col_default:
                if st.button("Apply Default Rules", type="secondary", use_container_width=True, help="Apply recommended default values for all rules"):
                    try:
                        # Get default values from config_rules table
                        success_count = 0
                        for _, rule in rules_df.iterrows():
                            default_threshold = rule.get('DEFAULT_THRESHOLD')
                            if default_threshold is not None and not pd.isna(default_threshold):
                                try:
                                    apply_rule(session, rule['RULE_ID'], default_threshold, scope='ALL')
                                    success_count += 1
                                except Exception as e:
                                    st.warning(f"Could not apply {rule['RULE_NAME']}: {str(e)}")
                        
                        if success_count > 0:
                            st.success(f"Successfully applied {success_count} default rules!")
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
                        format_func=lambda x: f"{rules_df[rules_df['RULE_ID'] == x]['RULE_NAME'].iloc[0]}",
                        key="rule_selector"
                    )
                
                with col2:
                    if selected_rule:
                        rule_info = rules_df[rules_df['RULE_ID'] == selected_rule].iloc[0]
                        allow_override = rule_info.get('ALLOW_THRESHOLD_OVERRIDE', True)
                        default_threshold = rule_info.get('DEFAULT_THRESHOLD', 0)
                        
                        # Use default threshold as value, and disable if override not allowed
                        threshold_value = st.number_input(
                            f"Threshold ({rule_info['UNIT']})",
                            min_value=0,
                            value=int(default_threshold) if default_threshold is not None else 0,
                            step=10,
                            help=f"Set the {rule_info['COMPARISON_OPERATOR']} value" if allow_override else "This threshold cannot be changed",
                            disabled=not allow_override
                        )
                
                if selected_rule:
                    rule_info = rules_df[rules_df['RULE_ID'] == selected_rule].iloc[0]
                    st.info(f"**{rule_info['RULE_NAME']}**: {rule_info['RULE_DESCRIPTION']}")
                    
                    # Add scope selection
                    st.markdown("##### Rule Scope")
                    scope = st.radio(
                        "Apply this rule to:",
                        ["All Objects", "Objects with Specific Tag"],
                        horizontal=True,
                        key="rule_scope_selector",
                        help="Choose whether this rule applies to all objects or only objects with a specific tag"
                    )
                    
                    # Tag selection (only if TAG_BASED scope)
                    tag_name = None
                    tag_value = None
                    if scope == "Objects with Specific Tag":
                        try:
                            available_tags_df = get_available_tag_names(session)
                            if not available_tags_df.empty:
                                col_tag1, col_tag2 = st.columns([1, 1])
                                with col_tag1:
                                    tag_name = st.selectbox(
                                        "Tag Name",
                                        available_tags_df['TAG_NAME'].tolist(),
                                        key="tag_name_selector",
                                        help="Select the tag that objects must have for this rule to apply"
                                    )
                                with col_tag2:
                                    tag_value = st.text_input(
                                        "Tag Value (optional)",
                                        key="tag_value_input",
                                        help="Optionally specify a tag value. Leave blank to apply to any value of this tag.",
                                        placeholder="e.g., Production"
                                    )
                                    if tag_value == "":
                                        tag_value = None
                            else:
                                st.warning("No tags available in the account. Create tags first to use tag-based rules.")
                        except Exception as e:
                            st.error(f"Error loading tags: {str(e)}")
                    
                    # Convert scope to internal format
                    scope_internal = 'ALL' if scope == "All Objects" else 'TAG_BASED'
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("Apply Rule", type="primary", use_container_width=True):
                            try:
                                apply_rule(session, selected_rule, threshold_value, scope_internal, tag_name, tag_value)
                                
                                # Generate success message based on scope
                                if scope_internal == 'TAG_BASED':
                                    tag_desc = f"Tag: {tag_name}={tag_value}" if tag_value else f"Tag: {tag_name}"
                                    st.success(f"Rule '{rule_info['RULE_NAME']}' applied with threshold: {threshold_value} {rule_info['UNIT']} [{tag_desc}]")
                                else:
                                    st.success(f"Rule '{rule_info['RULE_NAME']}' applied with threshold: {threshold_value} {rule_info['UNIT']} [All Objects]")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error applying rule: {str(e)}")
        
        else:  # Tag Rules
            st.markdown("**Configure Tag Compliance Rule**")
            st.info("Tag rules check whether required tags are present on objects. Select a tag and object type to enforce tag compliance.")
            
            # Get available tag names
            try:
                available_tags_df = get_available_tags(session)
                if available_tags_df.empty:
                    st.warning("No tags available. Please create tags in your Snowflake account first.")
                else:
                    # Tag selection and object type selection
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Create list of full tag names
                        tag_options = [f"{row['TAG_DATABASE']}.{row['TAG_SCHEMA']}.{row['TAG_NAME']}" 
                                       for _, row in available_tags_df.iterrows()]
                        selected_tag = st.selectbox(
                            "Select Tag",
                            tag_options,
                            key="tag_selector"
                        )
                    
                    with col2:
                        selected_object_type = st.selectbox(
                            "Select Object Type",
                            ["WAREHOUSE", "DATABASE", "TABLE"],
                            key="tag_object_type_selector"
                        )
                    
                    if selected_tag and selected_object_type:
                        st.info(f"This rule will ensure all {selected_object_type}s have the tag `{selected_tag}` assigned.")
                        
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button("Apply Tag Rule", type="primary", use_container_width=True):
                                try:
                                    apply_tag_rule(session, selected_tag, selected_object_type)
                                    st.success(f"Tag rule applied: '{selected_tag}' required on all {selected_object_type}s")
                                    st.rerun()
                                except ValueError as e:
                                    st.error(str(e))
                                except Exception as e:
                                    st.error(f"Error applying tag rule: {str(e)}")
            except Exception as e:
                st.error(f"Error loading tags: {str(e)}")
    else:
        st.warning("No configuration rules available")
    
    st.markdown("---")
    
    # Display applied rules
    st.markdown("#### Currently Applied Rules")
    applied_rules_df = get_applied_rules(session)
    applied_tag_rules_df = get_applied_tag_rules(session)
    try:
        tag_df = get_tag_compliance_details(session)
    except:
        tag_df = pd.DataFrame()
    
    # Create tabs for different rule types
    if not applied_rules_df.empty or not applied_tag_rules_df.empty:
        tab1, tab2, tab3 = st.tabs(["Database Rules", "Warehouse Rules", "Tag Rules"])
        
        # Tab 1: Database Rules
        with tab1:
            db_rules = applied_rules_df[applied_rules_df['RULE_TYPE'] == 'Database'] if not applied_rules_df.empty else pd.DataFrame()
            
            if not db_rules.empty:
                # Get compliance data once for all database rules
                retention_df = get_database_retention_details(session)
                whitelist_df = get_whitelisted_violations(session)
                
                for _, rule in db_rules.iterrows():
                    rule_type_class = "database"
                    rule_type_icon = '<span class="db-icon"></span>'
                    
                    # Calculate violation count for this specific applied rule
                    violation_count = 0
                    if not retention_df.empty:
                        compliance_data = check_table_compliance(retention_df, applied_rules_df[applied_rules_df['APPLIED_RULE_ID'] == rule['APPLIED_RULE_ID']],tag_df, whitelist_df)
                        for obj_comp in compliance_data:
                            for violation in obj_comp['violations']:
                                if violation.get('applied_rule_id') == rule['APPLIED_RULE_ID'] and not violation.get('is_whitelisted', False):
                                    violation_count += 1
                    
                    # Render the rule card using utility function with violation count
                    render_rule_card(rule, rule_type_class, rule_type_icon, violation_count)
                    
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
                        if st.button("Deactivate", key=f"deact_{rule['APPLIED_RULE_ID']}", help="Stop monitoring this rule", type="primary", use_container_width=True):
                            try:
                                deactivate_applied_rule(session, rule['APPLIED_RULE_ID'])
                                st.success("Rule deactivated")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    
                    # Show SQL if button was clicked
                    if st.session_state.get(f'show_sql_{rule["APPLIED_RULE_ID"]}', False):
                        # Generate SQL for database/schema/table rules - only for this specific applied rule
                        retention_df = get_database_retention_details(session)
                        compliance_data = check_table_compliance(retention_df, applied_rules_df[applied_rules_df['APPLIED_RULE_ID'] == rule['APPLIED_RULE_ID']], tag_df, whitelist_df)
                        
                        sql_statements = []
                        for obj_comp in compliance_data:
                            for violation in obj_comp['violations']:
                                if violation.get('applied_rule_id') == rule['APPLIED_RULE_ID'] and not violation.get('is_whitelisted', False):
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
                st.info("No database rules have been applied yet")
        
        # Tab 2: Warehouse Rules
        with tab2:
            wh_rules = applied_rules_df[applied_rules_df['RULE_TYPE'] == 'Warehouse'] if not applied_rules_df.empty else pd.DataFrame()
            
            if not wh_rules.empty:
                # Get compliance data once for all warehouse rules
                warehouse_df = get_warehouse_details(session)
                whitelist_df = get_whitelisted_violations(session)
                
                for _, rule in wh_rules.iterrows():
                    rule_type_class = "warehouse"
                    rule_type_icon = '<span class="wh-icon"></span>'
                    
                    # Calculate violation count for this specific applied rule
                    violation_count = 0
                    if not warehouse_df.empty:
                        # Pass only this specific applied rule to get violations for this rule instance
                        compliance_data = check_wh_compliance(warehouse_df, applied_rules_df[applied_rules_df['APPLIED_RULE_ID'] == rule['APPLIED_RULE_ID']],tag_df, whitelist_df)
                        for wh_comp in compliance_data:
                            for violation in wh_comp['violations']:
                                if violation.get('applied_rule_id') == rule['APPLIED_RULE_ID'] and not violation.get('is_whitelisted', False):
                                    violation_count += 1
                    
                    # Render the rule card using utility function with violation count
                    render_rule_card(rule, rule_type_class, rule_type_icon, violation_count)
                    
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
                        if st.button("Deactivate", key=f"deact_{rule['APPLIED_RULE_ID']}", help="Stop monitoring this rule", type="primary", use_container_width=True):
                            try:
                                deactivate_applied_rule(session, rule['APPLIED_RULE_ID'])
                                st.success("Rule deactivated")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    
                    # Show SQL if button was clicked
                    if st.session_state.get(f'show_sql_{rule["APPLIED_RULE_ID"]}', False):
                        # Generate SQL for warehouse rules - only for this specific applied rule
                        warehouse_df = get_warehouse_details(session)
                        compliance_data = check_wh_compliance(warehouse_df, applied_rules_df[applied_rules_df['APPLIED_RULE_ID'] == rule['APPLIED_RULE_ID']], tag_df, whitelist_df)
                        
                        sql_statements = []
                        for wh_comp in compliance_data:
                            for violation in wh_comp['violations']:
                                if violation.get('applied_rule_id') == rule['APPLIED_RULE_ID'] and not violation.get('is_whitelisted', False):
                                    sql = generate_wh_fix_sql(
                                        wh_comp['warehouse_name'],
                                        violation['parameter'],
                                        violation['threshold_value'] if violation['threshold_value'] != violation['current_value'] else st.session_state.wh_default_timeout
                                    )
                                    sql_statements.append(sql)
                        
                        if sql_statements:
                            combined_sql = "\n\n".join(sql_statements)
                            st.code(combined_sql, language="sql")
                        else:
                            st.success("All warehouses are compliant with this rule")
                    
                    st.markdown("---")
            else:
                st.info("No warehouse rules have been applied yet")
        
        # Tab 3: Tag Rules
        with tab3:
            if not applied_tag_rules_df.empty:
                for _, tag_rule in applied_tag_rules_df.iterrows():
                    # Calculate violation count for this tag rule
                    violation_count = 0
                    try:
                        all_objects_df = get_all_objects_by_type(session, tag_rule['OBJECT_TYPE'])
                        tag_assignments_df = get_tag_compliance_details(session, tag_rule['OBJECT_TYPE'])
                        whitelist_df = get_whitelisted_violations(session, object_type=tag_rule['OBJECT_TYPE'])
                        single_rule_df = applied_tag_rules_df[applied_tag_rules_df['APPLIED_TAG_RULE_ID'] == tag_rule['APPLIED_TAG_RULE_ID']]
                        compliance_data = check_tag_compliance(all_objects_df, tag_assignments_df, single_rule_df, whitelist_df)
                        
                        for obj_comp in compliance_data:
                            if obj_comp['violations']:
                                # Only count non-whitelisted violations for THIS specific tag rule
                                for violation in obj_comp['violations']:
                                    if (not violation.get('is_whitelisted', False) and 
                                        violation.get('applied_tag_rule_id') == tag_rule['APPLIED_TAG_RULE_ID']):
                                        violation_count += 1
                    except Exception as e:
                        # Log the error for debugging
                        st.warning(f"Error calculating violations for tag rule: {str(e)}")
                        violation_count = 0
                    
                    # Build violation count display
                    violation_html = ""
                    if violation_count > 0:
                        violation_html = f'<span class="violation-count"><span class="warning-icon"></span> {violation_count} violation{"s" if violation_count != 1 else ""}</span>'
                    else:
                        violation_html = '<span class="compliant-count"><span class="check-icon"></span> All compliant</span>'
                    
                    # Display tag rule card
                    st.html(f"""
                        <div class="rule-card tag">
                            <h4 style="margin-top:0;">
                                <span class="tag-icon"></span> Tag: {tag_rule['TAG_NAME']}
                                <span class="rule-type-label tag">TAG RULE</span>
                                {violation_html}
                            </h4>
                            <p style="margin-bottom:0.5rem;">
                                <strong>Object Type:</strong> {tag_rule['OBJECT_TYPE']} | 
                                <strong>Applied:</strong> {tag_rule['APPLIED_AT'].strftime('%Y-%m-%d %H:%M')} | 
                                <strong>Applied By:</strong> {tag_rule.get('APPLIED_BY', 'N/A')}
                            </p>
                        </div>
                    """)
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col2:
                        if st.button("Generate SQL", key=f"btn_tag_sql_{tag_rule['APPLIED_TAG_RULE_ID']}", help="Generate SQL for all non-compliant objects", use_container_width=True):
                            st.session_state[f'show_tag_sql_{tag_rule["APPLIED_TAG_RULE_ID"]}'] = True
                    
                    with col3:
                        if st.button("Deactivate", key=f"deact_tag_{tag_rule['APPLIED_TAG_RULE_ID']}", help="Stop monitoring this tag rule", type="primary", use_container_width=True):
                            try:
                                deactivate_tag_rule(session, tag_rule['APPLIED_TAG_RULE_ID'])
                                st.success("Tag rule deactivated")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    
                    # Show SQL if button was clicked
                    if st.session_state.get(f'show_tag_sql_{tag_rule["APPLIED_TAG_RULE_ID"]}', False):
                        # Get all objects of the specified type
                        all_objects_df = get_all_objects_by_type(session, tag_rule['OBJECT_TYPE'])
                        tag_assignments_df = get_tag_compliance_details(session, tag_rule['OBJECT_TYPE'])
                        whitelist_df = get_whitelisted_violations(session, object_type=tag_rule['OBJECT_TYPE'])
                        
                        # Check compliance for this specific tag rule
                        single_rule_df = applied_tag_rules_df[applied_tag_rules_df['APPLIED_TAG_RULE_ID'] == tag_rule['APPLIED_TAG_RULE_ID']]
                        compliance_data = check_tag_compliance(all_objects_df, tag_assignments_df, single_rule_df, whitelist_df)
                        
                        sql_statements = []
                        for obj_comp in compliance_data:
                            if obj_comp['violations']:
                                for violation in obj_comp['violations']:
                                    # Skip whitelisted violations
                                    if not violation.get('is_whitelisted', False):
                                        sql = generate_tag_fix_sql(
                                            obj_comp['object_name'],
                                            obj_comp['object_type'],
                                            violation['tag_name']
                                        )
                                        sql_statements.append(sql)
                        
                        if sql_statements:
                            combined_sql = "\n\n".join(sql_statements)
                            st.code(combined_sql, language="sql")
                        else:
                            st.success(f"All {tag_rule['OBJECT_TYPE']}s are compliant with this tag rule")
                    
                    st.markdown("---")
            else:
                st.info("No tag rules have been applied yet")
    else:
        st.info("No rules have been applied yet. Apply a rule above to start monitoring compliance.")
