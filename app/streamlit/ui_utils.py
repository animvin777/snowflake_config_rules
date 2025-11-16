"""
UI utilities module
Common UI components and helper functions
"""

import streamlit as st
from pathlib import Path
from datetime import datetime


def load_css():
    """Load custom CSS from external file"""
    css_file = Path(__file__).parent / "styles.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS file not found. Using default styles.")


def render_header():
    """Render the main application header"""
    st.markdown("""
        <div class="main-header">
            <h1><span class="settings-icon"></span> Configuration Compliance Manager</h1>
            <p>Monitor and enforce configuration standards across your Snowflake environment</p>
        </div>
    """, unsafe_allow_html=True)


def render_footer():
    """Render the application footer"""
    st.markdown("---")
    st.markdown("""
        <div class="footer">
            <p><strong>Snowflake Config Rules</strong></p>
            <p>Monitor and enforce configuration compliance across your Snowflake account</p>
            <p>Last refreshed: {}</p>
        </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)


def render_refresh_button(key_suffix):
    """Render a refresh button in the top right corner"""
    col_title, col_refresh = st.columns([10, 1])
    return col_title, col_refresh


def render_metric_card(value, label, card_type=""):
    """Render a metric card with optional styling"""
    card_class = f"metric-card {card_type}".strip()
    st.markdown(f"""
        <div class="{card_class}">
            <h3>{value}</h3>
            <p>{label}</p>
        </div>
    """, unsafe_allow_html=True)


def render_filter_button(label, value, filter_key, filter_value, session_state_key):
    """Render a filter button with primary/secondary type based on active state
    
    Args:
        label: Button label text
        value: Value to display (e.g., count, percentage)
        filter_key: Unique key for the button
        filter_value: Value to set when button is clicked
        session_state_key: Session state key to check/update
    
    Returns:
        bool: True if button was clicked
    """
    is_active = st.session_state.get(session_state_key) == filter_value
    btn_type = "primary" if is_active else "secondary"
    clicked = st.button(
        f"**{value}**\n\n{label}", 
        key=filter_key, 
        use_container_width=True, 
        type=btn_type
    )
    if clicked:
        st.session_state[session_state_key] = filter_value
        st.rerun()
    return clicked


def render_section_header(title, icon_class=""):
    """Render a section header with optional icon
    
    Args:
        title: Header text
        icon_class: CSS class for icon (e.g., 'chart-icon', 'wh-icon')
    """
    if icon_class:
        st.markdown(f'<h3><span class="{icon_class}"></span> {title}</h3>', unsafe_allow_html=True)
    else:
        st.markdown(f"### {title}")


def render_tab_header(title, icon_class, refresh_key):
    """Render a tab header with title, icon, and refresh button
    
    Args:
        title: Header title text
        icon_class: CSS class for icon
        refresh_key: Unique key for refresh button
        
    Returns:
        tuple: (title_col, refresh_col) for additional customization
    """
    col_title, col_refresh = st.columns([5, 1])
    return col_title, col_refresh


def execute_query_with_error_handling(session, query, error_message="Error executing query"):
    """Execute a SQL query with error handling
    
    Args:
        session: Snowflake session
        query: SQL query string
        error_message: Custom error message to display
        
    Returns:
        DataFrame or None if error occurs
    """
    try:
        return session.sql(query).collect()
    except Exception as e:
        st.error(f"{error_message}: {str(e)}")
        return None


def render_count_metric(session, query, label):
    """Render a metric showing count from a query
    
    Args:
        session: Snowflake session
        query: SQL query that returns a COUNT
        label: Metric label
    """
    try:
        count = session.sql(query).collect()[0]['CNT']
        st.metric(label, count)
    except:
        st.metric(label, "Error")


def filter_by_search(items, search_term, *search_fields):
    """Filter items by search term across multiple fields
    
    Args:
        items: List of dictionaries to filter
        search_term: Search string (case-insensitive)
        *search_fields: Field names or callables to extract search text
        
    Returns:
        Filtered list of items
    """
    if not search_term:
        return items
    
    search_lower = search_term.lower()
    filtered = []
    
    for item in items:
        match = False
        for field in search_fields:
            if callable(field):
                # Field is a function to extract text
                text = field(item)
            else:
                # Field is a dictionary key
                text = str(item.get(field, ''))
            
            if search_lower in text.lower():
                match = True
                break
        
        if match:
            filtered.append(item)
    
    return filtered


def render_rule_card(rule, rule_type_class, rule_type_icon):
    """Render an applied rule card with consistent styling
    
    Args:
        rule: Rule dictionary with RULE_NAME, THRESHOLD_VALUE, etc.
        rule_type_class: CSS class ('warehouse' or 'database')
        rule_type_icon: HTML for icon
    """
    st.markdown(f"""
        <div class="rule-card {rule_type_class}">
            <h4 style="margin-top:0;">
                {rule_type_icon} {rule['RULE_NAME']}
                <span class="rule-type-label {rule_type_class}">{rule['RULE_TYPE']}</span>
            </h4>
            <p style="margin-bottom:0.5rem;"><strong>Threshold:</strong> {int(rule['THRESHOLD_VALUE'])} {rule['UNIT']} | <strong>Applied:</strong> {rule['APPLIED_AT'].strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    """, unsafe_allow_html=True)

