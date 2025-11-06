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
            <h1>Snowflake Config Rules</h1>
            <p>Manage and enforce warehouse configuration compliance rules</p>
        </div>
    """, unsafe_allow_html=True)


def render_footer():
    """Render the application footer"""
    st.markdown("---")
    st.markdown("""
        <div class="footer">
            <p><strong>Snowflake Config Rules</strong></p>
            <p>Monitor and enforce warehouse configuration compliance across your Snowflake account</p>
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
