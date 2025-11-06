"""
Warehouse Overview Tab
Displays detailed warehouse information and analytics
"""

import streamlit as st
import pandas as pd
from database import get_warehouse_details
from ui_utils import render_refresh_button


def render_warehouse_overview_tab(session):
    """Render the Warehouse Overview tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab3")
    with col_title:
        st.markdown("### Warehouse Overview")
    with col_refresh:
        if st.button("🔄", key="refresh_tab3", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    warehouse_df = get_warehouse_details(session)
    
    if warehouse_df.empty:
        st.warning("No warehouse data available yet. The monitoring task runs periodically.")
    else:
        _render_key_metrics(warehouse_df)
        _render_warehouse_details(warehouse_df)
        _render_summary_table(warehouse_df)
        _render_analytics(warehouse_df)


def _render_key_metrics(warehouse_df):
    """Render key metrics at the top"""
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


def _render_warehouse_details(warehouse_df):
    """Render detailed warehouse information in expandable sections"""
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


def _render_summary_table(warehouse_df):
    """Render summary table view"""
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


def _render_analytics(warehouse_df):
    """Render distribution analytics"""
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
