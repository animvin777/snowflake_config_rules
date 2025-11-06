"""
Snowflake Config Rules App
Manage and enforce configuration rules across Snowflake warehouses
"""

import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session
from datetime import datetime
from pathlib import Path

# Get the active Snowflake session
session = get_active_session()

# Set page configuration
st.set_page_config(
    page_title="Snowflake Config Rules",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
def load_css():
    """Load custom CSS from external file"""
    css_file = Path(__file__).parent / "styles.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS file not found. Using default styles.")

# Load the CSS
load_css()

# App header
st.markdown("""
    <div class="main-header">
        <h1>Snowflake Config Rules</h1>
        <p>Manage and enforce warehouse configuration compliance rules</p>
    </div>
""", unsafe_allow_html=True)

# Helper functions
def get_config_rules():
    """Retrieve all configuration rules"""
    query = """
    SELECT rule_id, rule_name, rule_description, warehouse_parameter, 
           comparison_operator, unit, is_active
    FROM data_schema.config_rules
    WHERE is_active = TRUE
    ORDER BY rule_name
    """
    return session.sql(query).to_pandas()

def get_applied_rules():
    """Retrieve all applied rules with their threshold values"""
    query = """
    SELECT ar.applied_rule_id, ar.rule_id, cr.rule_name, ar.threshold_value,
           cr.warehouse_parameter, cr.comparison_operator, cr.unit,
           ar.applied_at, ar.is_active
    FROM data_schema.applied_rules ar
    JOIN data_schema.config_rules cr ON ar.rule_id = cr.rule_id
    WHERE ar.is_active = TRUE
    ORDER BY ar.applied_at DESC
    """
    return session.sql(query).to_pandas()

def get_warehouse_details():
    """Retrieve latest warehouse details"""
    query = """
    SELECT DISTINCT 
        name, type, size, auto_suspend, statement_timeout_in_seconds,
        owner, created_on, resumed_on, updated_on,
        min_cluster_count, max_cluster_count, scaling_policy,
        max_concurrency_level, statement_queued_timeout_in_seconds,
        comment, capture_timestamp
    FROM data_schema.warehouse_details
    QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY capture_timestamp DESC) = 1
    ORDER BY name
    """
    return session.sql(query).to_pandas()

def apply_rule(rule_id, threshold_value):
    """Apply a configuration rule with a threshold value"""
    # Deactivate any existing active rule for this rule_id
    deactivate_query = f"""
    UPDATE data_schema.applied_rules 
    SET is_active = FALSE 
    WHERE rule_id = '{rule_id}' AND is_active = TRUE
    """
    session.sql(deactivate_query).collect()
    
    # Insert new applied rule
    insert_query = f"""
    INSERT INTO data_schema.applied_rules (rule_id, threshold_value, applied_by)
    VALUES ('{rule_id}', {threshold_value}, CURRENT_USER())
    """
    session.sql(insert_query).collect()

def deactivate_applied_rule(applied_rule_id):
    """Deactivate an applied rule"""
    query = f"""
    UPDATE data_schema.applied_rules 
    SET is_active = FALSE 
    WHERE applied_rule_id = {applied_rule_id}
    """
    session.sql(query).collect()

def check_compliance(warehouse_df, applied_rules_df):
    """Check warehouse compliance against applied rules"""
    compliance_data = []
    
    for _, wh in warehouse_df.iterrows():
        wh_compliance = {
            'warehouse_name': wh['NAME'],
            'warehouse_type': wh['TYPE'],
            'warehouse_size': wh['SIZE'],
            'warehouse_owner': wh['OWNER'],
            'violations': []
        }
        
        for _, rule in applied_rules_df.iterrows():
            param = rule['WAREHOUSE_PARAMETER']
            threshold = rule['THRESHOLD_VALUE']
            operator = rule['COMPARISON_OPERATOR']
            rule_name = rule['RULE_NAME']
            
            # Get warehouse parameter value
            if param == 'AUTO_SUSPEND':
                wh_value = wh['AUTO_SUSPEND']
            elif param == 'STATEMENT_TIMEOUT_IN_SECONDS':
                wh_value = wh['STATEMENT_TIMEOUT_IN_SECONDS']
            else:
                continue
            
            # Check for NULL values
            if pd.isna(wh_value):
                wh_value = None
            
            # Check compliance based on operator
            is_compliant = True
            if operator == 'MAX' and wh_value is not None and wh_value > threshold:
                is_compliant = False
            elif operator == 'MIN' and wh_value is not None and wh_value < threshold:
                is_compliant = False
            elif operator == 'EQUALS' and wh_value != threshold:
                is_compliant = False
            
            if not is_compliant:
                wh_compliance['violations'].append({
                    'rule_id': rule['RULE_ID'],
                    'rule_name': rule_name,
                    'parameter': param,
                    'current_value': wh_value,
                    'threshold_value': threshold,
                    'operator': operator,
                    'unit': rule['UNIT']
                })
        
        compliance_data.append(wh_compliance)
    
    return compliance_data

def generate_fix_sql(warehouse_name, parameter, threshold_value):
    """Generate SQL to fix a non-compliant warehouse"""
    if parameter == 'AUTO_SUSPEND':
        return f"ALTER WAREHOUSE {warehouse_name}\nSET AUTO_SUSPEND = {int(threshold_value)};"
    elif parameter == 'STATEMENT_TIMEOUT_IN_SECONDS':
        return f"ALTER WAREHOUSE {warehouse_name}\nSET STATEMENT_TIMEOUT_IN_SECONDS = {int(threshold_value)};"
    else:
        return f"-- No SQL available for parameter: {parameter}"

# Create tabs
tab1, tab2, tab3 = st.tabs(["Rule Configuration", "Compliance View", "Warehouse Overview"])

with tab1:
    # Refresh button in top right
    col_title, col_refresh = st.columns([10, 1])
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
    
    rules_df = get_config_rules()
    
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
                            apply_rule(selected_rule, threshold_value)
                            st.success(f"Rule '{rule_info['RULE_NAME']}' applied with threshold: {threshold_value} {rule_info['UNIT']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error applying rule: {str(e)}")
    else:
        st.warning("No configuration rules available")
    
    st.markdown("---")
    
    # Display applied rules
    st.markdown("#### Currently Applied Rules")
    applied_rules_df = get_applied_rules()
    
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
                        deactivate_applied_rule(rule['APPLIED_RULE_ID'])
                        st.success("Rule deactivated")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            # Show SQL if button was clicked
            if st.session_state.get(f'show_sql_{rule["APPLIED_RULE_ID"]}', False):
                warehouse_df = get_warehouse_details()
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

with tab2:
    # Refresh button in top right
    col_title, col_refresh = st.columns([10, 1])
    with col_title:
        st.markdown("### Warehouse Compliance Status")
    with col_refresh:
        if st.button("🔄", key="refresh_tab2", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    applied_rules_df = get_applied_rules()
    
    if applied_rules_df.empty:
        st.info("No rules applied yet. Go to 'Rule Configuration' tab to apply rules.")
    else:
        warehouse_df = get_warehouse_details()
        
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
                # List view - compact table format
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
            
            else:
                # Tile view - card format (default)
                for wh_comp in compliance_data:
                    has_violations = len(wh_comp['violations']) > 0
                    
                    # Apply filter
                    if view_filter == "Non-Compliant Only" and not has_violations:
                        continue
                    elif view_filter == "Compliant Only" and has_violations:
                        continue
                    
                    # Display warehouse card - compact version
                    card_class = "warehouse-compact non-compliant" if has_violations else "warehouse-compact compliant"
                    
                    with st.container():
                        st.markdown(f"""
                            <div class="{card_class}">
                                <div class="warehouse-name">{wh_comp['warehouse_name']}</div>
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
                                if st.button("Fix", key=f"fix_{wh_comp['warehouse_name']}", type="primary", use_container_width=True):
                                    # Execute the fix SQL
                                    try:
                                        for violation in wh_comp['violations']:
                                            sql = generate_fix_sql(
                                                wh_comp['warehouse_name'],
                                                violation['parameter'],
                                                violation['threshold_value']
                                            )
                                            session.sql(sql).collect()
                                        st.success(f"Fixed {wh_comp['warehouse_name']}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                        
                        st.markdown("<br>", unsafe_allow_html=True)

with tab3:
    # Refresh button in top right
    col_title, col_refresh = st.columns([10, 1])
    with col_title:
        st.markdown("### Warehouse Overview")
    with col_refresh:
        if st.button("🔄", key="refresh_tab3", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    warehouse_df = get_warehouse_details()
    
    if warehouse_df.empty:
        st.warning("No warehouse data available yet. The monitoring task runs periodically.")
    else:
        # Key metrics at the top
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <h3>{len(warehouse_df)}</h3>
                    <p>Total Warehouses</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            unique_sizes = warehouse_df['SIZE'].nunique()
            st.markdown(f"""
                <div class="metric-card purple">
                    <h3>{unique_sizes}</h3>
                    <p>Unique Sizes</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            multi_cluster = len(warehouse_df[warehouse_df['MAX_CLUSTER_COUNT'] > 1])
            st.markdown(f"""
                <div class="metric-card warning">
                    <h3>{multi_cluster}</h3>
                    <p>Multi-Cluster</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            avg_auto_suspend = warehouse_df['AUTO_SUSPEND'].mean()
            st.markdown(f"""
                <div class="metric-card cyan">
                    <h3>{int(avg_auto_suspend) if pd.notna(avg_auto_suspend) else 'N/A'}</h3>
                    <p style="margin: 0; color: #666;">Avg Auto-Suspend (sec)</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Detailed warehouse information in expandable sections
        st.markdown("#### 🏢 Warehouse Details")
        
        for _, wh in warehouse_df.iterrows():
            with st.expander(f"🔹 {wh['NAME']} ({wh['SIZE']})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Basic Configuration**")
                    st.markdown(f"- **Type:** {wh['TYPE']}")
                    st.markdown(f"- **Size:** {wh['SIZE']}")
                    st.markdown(f"- **Owner:** {wh['OWNER']}")
                    st.markdown(f"- **Auto Suspend:** {int(wh['AUTO_SUSPEND']) if pd.notna(wh['AUTO_SUSPEND']) else 'Not Set'} sec")
                
                with col2:
                    st.markdown("**Cluster Configuration**")
                    st.markdown(f"- **Min Clusters:** {int(wh['MIN_CLUSTER_COUNT']) if pd.notna(wh['MIN_CLUSTER_COUNT']) else 'N/A'}")
                    st.markdown(f"- **Max Clusters:** {int(wh['MAX_CLUSTER_COUNT']) if pd.notna(wh['MAX_CLUSTER_COUNT']) else 'N/A'}")
                    st.markdown(f"- **Scaling Policy:** {wh['SCALING_POLICY'] if pd.notna(wh['SCALING_POLICY']) else 'N/A'}")
                    if pd.notna(wh['MAX_CONCURRENCY_LEVEL']):
                        st.markdown(f"- **Max Concurrency:** {int(wh['MAX_CONCURRENCY_LEVEL'])}")
                
                with col3:
                    st.markdown("**Timeout Settings**")
                    if pd.notna(wh['STATEMENT_TIMEOUT_IN_SECONDS']):
                        st.markdown(f"- **Statement Timeout:** {int(wh['STATEMENT_TIMEOUT_IN_SECONDS'])} sec")
                    else:
                        st.markdown("- **Statement Timeout:** Not Set")
                    
                    if pd.notna(wh['STATEMENT_QUEUED_TIMEOUT_IN_SECONDS']):
                        st.markdown(f"- **Queued Timeout:** {int(wh['STATEMENT_QUEUED_TIMEOUT_IN_SECONDS'])} sec")
                    else:
                        st.markdown("- **Queued Timeout:** Not Set")
                
                st.markdown("**Timestamps**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"- **Created:** {wh['CREATED_ON'].strftime('%Y-%m-%d %H:%M') if pd.notna(wh['CREATED_ON']) else 'N/A'}")
                with col2:
                    st.markdown(f"- **Last Resumed:** {wh['RESUMED_ON'].strftime('%Y-%m-%d %H:%M') if pd.notna(wh['RESUMED_ON']) else 'Never'}")
                with col3:
                    st.markdown(f"- **Last Updated:** {wh['UPDATED_ON'].strftime('%Y-%m-%d %H:%M') if pd.notna(wh['UPDATED_ON']) else 'N/A'}")
                
                if pd.notna(wh['COMMENT']) and wh['COMMENT']:
                    st.markdown(f"**Comment:** {wh['COMMENT']}")
        
        st.markdown("---")
        
        # Summary table view
        st.markdown("#### 📋 Summary Table")
        display_df = warehouse_df.copy()
        display_df['AUTO_SUSPEND'] = display_df['AUTO_SUSPEND'].apply(
            lambda x: f"{int(x)} sec" if pd.notna(x) else "Not Set"
        )
        display_df['STATEMENT_TIMEOUT_IN_SECONDS'] = display_df['STATEMENT_TIMEOUT_IN_SECONDS'].apply(
            lambda x: f"{int(x)} sec" if pd.notna(x) else "Not Set"
        )
        
        st.dataframe(
            display_df[['NAME', 'TYPE', 'SIZE', 'AUTO_SUSPEND', 'STATEMENT_TIMEOUT_IN_SECONDS', 'MIN_CLUSTER_COUNT', 'MAX_CLUSTER_COUNT', 'OWNER']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "NAME": "Warehouse",
                "TYPE": "Type",
                "SIZE": "Size",
                "AUTO_SUSPEND": "Auto Suspend",
                "STATEMENT_TIMEOUT_IN_SECONDS": "Statement Timeout",
                "MIN_CLUSTER_COUNT": "Min Clusters",
                "MAX_CLUSTER_COUNT": "Max Clusters",
                "OWNER": "Owner"
            }
        )
        
        st.markdown("---")
        
        # Analytics
        st.markdown("#### 📈 Distribution Analytics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Warehouses by Size**")
            size_counts = warehouse_df.groupby('SIZE')['NAME'].count().reset_index()
            size_counts.columns = ['Size', 'Count']
            st.bar_chart(size_counts.set_index('Size'), height=250)
        
        with col2:
            st.markdown("**Warehouses by Type**")
            type_counts = warehouse_df.groupby('TYPE')['NAME'].count().reset_index()
            type_counts.columns = ['Type', 'Count']
            st.bar_chart(type_counts.set_index('Type'), height=250)
        
        with col3:
            st.markdown("**Warehouses by Owner**")
            owner_counts = warehouse_df.groupby('OWNER')['NAME'].count().reset_index()
            owner_counts.columns = ['Owner', 'Count']
            # Show top 5 owners
            owner_counts = owner_counts.nlargest(5, 'Count')
            st.bar_chart(owner_counts.set_index('Owner'), height=250)
        
        # Auto-suspend distribution
        st.markdown("**Auto-Suspend Distribution**")
        auto_suspend_data = warehouse_df[warehouse_df['AUTO_SUSPEND'].notna()][['NAME', 'AUTO_SUSPEND']].set_index('NAME')
        if not auto_suspend_data.empty:
            st.bar_chart(auto_suspend_data, height=300)
        else:
            st.info("No auto-suspend data available")

# Footer
st.markdown("---")
st.markdown("""
    <div class="footer">
        <p><strong>Snowflake Config Rules</strong></p>
        <p>Monitor and enforce warehouse configuration compliance across your Snowflake account</p>
        <p>Last refreshed: {}</p>
    </div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)
