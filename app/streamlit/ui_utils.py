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
            st.html(f"<style>{f.read()}</style>")
    else:
        st.warning("CSS file not found. Using default styles.")


def render_header():
    """Render the main application header"""
    st.html("""
        <div class="main-header">
            <h1><span class="settings-icon"></span> Configuration Compliance Manager</h1>
            <p>Monitor and enforce configuration standards across your Snowflake environment</p>
        </div>
    """)


def render_footer():
    """Render the application footer"""
    st.markdown("---")
    st.html("""
        <div class="footer">
            <p><strong>Snowflake Config Rules</strong></p>
            <p>Monitor and enforce configuration compliance across your Snowflake account</p>
            <p>Last refreshed: {}</p>
        </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


def render_refresh_button(key_suffix):
    """Render a refresh button in the top right corner"""
    col_title, col_refresh = st.columns([10, 1])
    return col_title, col_refresh


def render_metric_card(value, label, card_type=""):
    """Render a metric card with optional styling"""
    card_class = f"metric-card {card_type}".strip()
    st.html(f"""
        <div class="{card_class}">
            <h3>{value}</h3>
            <p>{label}</p>
        </div>
    """)


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
        st.html(f'<h3><span class="{icon_class}"></span> {title}</h3>')
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


def render_rule_card(rule, rule_type_class, rule_type_icon, violation_count=None):
    """Render an applied rule card with consistent styling
    
    Args:
        rule: Rule dictionary with RULE_NAME, THRESHOLD_VALUE, SCOPE, TAG_NAME, TAG_VALUE, etc.
        rule_type_class: CSS class ('warehouse' or 'database')
        rule_type_icon: HTML for icon
        violation_count: Optional number of violations for this rule
    """
    # Build violation count display if provided
    violation_html = ""
    if violation_count is not None:
        if violation_count > 0:
            violation_html = f'<span class="violation-count"><span class="warning-icon"></span> {violation_count} violation{"s" if violation_count != 1 else ""}</span>'
        else:
            violation_html = '<span class="compliant-count"><span class="check-icon"></span> All compliant</span>'
    
    # Build scope display
    scope = rule.get('SCOPE', 'ALL')
    tag_name = rule.get('TAG_NAME')
    tag_value = rule.get('TAG_VALUE')
    
    if scope == 'TAG_BASED' and tag_name:
        if tag_value:
            scope_html = f'<span class="rule-scope-label tag-based">Tag: {tag_name}={tag_value}</span>'
        else:
            scope_html = f'<span class="rule-scope-label tag-based">Tag: {tag_name}</span>'
    else:
        scope_html = '<span class="rule-scope-label all-objects">All Objects</span>'
    
    st.html(f"""
        <div class="rule-card {rule_type_class}">
            <h4 style="margin-top:0;">
                {rule_type_icon} {rule['RULE_NAME']}
                <span class="rule-type-label {rule_type_class}">{rule['RULE_TYPE']}</span>
                {scope_html}
                {violation_html}
            </h4>
            <p style="margin-bottom:0.5rem;"><strong>Threshold:</strong> {int(rule['THRESHOLD_VALUE'])} {rule['UNIT']} | <strong>Applied:</strong> {rule['APPLIED_AT'].strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    """)


def render_pagination_controls(total_count, page_size, current_page, key_prefix):
    """Render pagination controls with page size selector and navigation
    
    Args:
        total_count: Total number of items
        page_size: Current page size
        current_page: Current page number (0-indexed)
        key_prefix: Unique prefix for widget keys
    
    Returns:
        tuple: (new_page_size, new_page_number)
    """
    total_pages = max(1, (total_count + page_size - 1) // page_size)  # Ceiling division
    current_page = min(current_page, total_pages - 1)  # Ensure page is valid
    
    col1, col2, col3, col4 = st.columns([2, 2, 3, 3])
    
    with col1:
        page_size_options = [10, 25, 50, 100]
        new_page_size = st.selectbox(
            "Items per page",
            options=page_size_options,
            index=page_size_options.index(page_size) if page_size in page_size_options else 0,
            key=f"{key_prefix}_page_size"
        )
    
    with col2:
        st.html(f"""
            <div style="margin-top: 1.8rem; color: #666;">
                Page {current_page + 1} of {total_pages} ({total_count} total)
            </div>
        """)
    
    with col3:
        page_col1, page_col2, page_col3, page_col4 = st.columns(4)
        
        with page_col1:
            if st.button("⏮", key=f"{key_prefix}_first", disabled=current_page == 0, help="First page"):
                return new_page_size, 0
        
        with page_col2:
            if st.button("◀", key=f"{key_prefix}_prev", disabled=current_page == 0, help="Previous page"):
                return new_page_size, max(0, current_page - 1)
        
        with page_col3:
            if st.button("▶", key=f"{key_prefix}_next", disabled=current_page >= total_pages - 1, help="Next page"):
                return new_page_size, min(total_pages - 1, current_page + 1)
        
        with page_col4:
            if st.button("⏭", key=f"{key_prefix}_last", disabled=current_page >= total_pages - 1, help="Last page"):
                return new_page_size, total_pages - 1
    
    # If page size changed, reset to page 0
    if new_page_size != page_size:
        return new_page_size, 0
    
    return page_size, current_page


