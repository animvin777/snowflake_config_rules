"""
Task Management Tab
Handles the display and control of all tasks in the application
"""

import streamlit as st
from database import get_all_tasks, get_task_history, suspend_task, resume_task, execute_task
from ui_utils import render_refresh_button
import pandas as pd


def render_task_management_tab(session):
    """Render the Task Management tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_tasks")
    with col_title:
        st.markdown("### ⏱️ Scheduled Tasks & Monitoring")
    with col_refresh:
        if st.button("🔄", key="refresh_tab_tasks", help="Refresh data"):
            st.rerun()
    st.markdown("---")
    
    st.markdown("""
    Manage your automated data collection tasks. Monitor execution history, control task schedules, 
    and run tasks on-demand to keep your compliance data up-to-date.
    """)
    
    st.markdown("---")
    
    # Get all tasks
    try:
        tasks_df = get_all_tasks(session)
        
        if not tasks_df.empty:
            st.markdown("#### Application Tasks")
            
            # Display each task in a card
            for idx, task in tasks_df.iterrows():
                # Handle both uppercase and lowercase column names
                task_name = task.get('"name"', '')
                task_state = task.get('"state"', '')
                task_warehouse = task.get('"warehouse"', 'N/A')
                task_schedule = task.get('"schedule"', 'N/A')
                task_owner = task.get('"owner"', 'N/A')

                full_task_name = f"data_schema.{task_name}"
                
                # Create unique key using index
                unique_key = f"{idx}_{task_name}"
                
                st.markdown(f"""
                    <div class="rule-card">
                        <h4 style="margin-top:0;">📋 {task_name}</h4>
                        <p style="margin-bottom:0.5rem;">
                            <strong>State:</strong> <span style="color: {'green' if task_state == 'started' else 'red'};">{task_state.upper()}</span> | 
                            <strong>Schedule:</strong> {task_schedule}
                        </p>
                        <p style="margin-bottom:0.5rem;"><strong>Owner:</strong> {task_owner}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                
                with col1:
                    if task_state == 'started':
                        if st.button("⏸️ Suspend", key=f"suspend_{unique_key}", use_container_width=True):
                            try:
                                suspend_task(session, full_task_name)
                                st.success(f"Task {task_name} suspended")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    else:
                        if st.button("▶️ Resume", key=f"resume_{unique_key}", use_container_width=True):
                            try:
                                resume_task(session, full_task_name)
                                st.success(f"Task {task_name} resumed")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with col2:
                    if st.button("▶️ Execute Now", key=f"execute_{unique_key}", use_container_width=True):
                        try:
                            execute_task(session, full_task_name)
                            st.success(f"Task {task_name} executed")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                
                with col3:
                    # Toggle button to show/hide task history
                    if st.button("📊 History", key=f"history_{unique_key}", use_container_width=True):
                        if f'show_history_{unique_key}' not in st.session_state:
                            st.session_state[f'show_history_{unique_key}'] = True
                        else:
                            st.session_state[f'show_history_{unique_key}'] = not st.session_state.get(f'show_history_{unique_key}', False)

                # Show task history if toggled
                if st.session_state.get(f'show_history_{unique_key}', False):
                    st.markdown(f"##### 📊 Last 3 Runs for {task_name}")
                    history_df = get_task_history(session, task_name)
                    
                    if not history_df.empty:
                        for hist_idx, run in history_df.iterrows():
                            state_color = "green" if run['STATE'] == 'SUCCEEDED' else ("orange" if run['STATE'] == 'SCHEDULED' else "red")
                            error_info = ""
                            if run['STATE'] == 'FAILED' and run['ERROR_MESSAGE']:
                                error_info = f"<br><strong>Error:</strong> {run['ERROR_MESSAGE']}"
                            
                            st.markdown(f"""
                                <div style="padding: 10px; margin: 5px 0; background-color: #f8f9fa; border-left: 3px solid {state_color};">
                                    <strong>Status:</strong> <span style="color: {state_color};">{run['STATE']}</span><br>
                                    <strong>Scheduled:</strong> {run['SCHEDULED_TIME']}<br>
                                    <strong>Completed:</strong> {run['COMPLETED_TIME'] if run['COMPLETED_TIME'] else 'N/A'}<br>
                                    <strong>Duration:</strong> {run['DURATION_SECONDS'] if run['DURATION_SECONDS'] else 'N/A'} seconds
                                    {error_info}
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No execution history found for this task in the last 7 days.")
                
                st.markdown("---")
            
            # Add informational section
            st.markdown("#### ℹ️ Task Information")
            st.info("""
            **warehouse_monitor_task**: Captures warehouse configuration details every day at 7:00 AM EST.
            
            **db_retention_monitor_task**: Captures database, schema, and table retention time information every day at 7:00 AM EST.
            
            **warehouse_params_monitor_task** (if created by consumer): Custom task for monitoring additional warehouse parameters.
            
            You can execute tasks immediately using the "Execute Now" button, suspend/resume them as needed, and view execution history with the "History" button.
            """)
        else:
            st.warning("No tasks found in the application")
    except Exception as e:
        st.error(f"Error loading tasks: {str(e)}")
        
        # Show fallback information
        st.markdown("#### Default Application Tasks")
        st.markdown("""
        The application includes the following tasks:
        - **warehouse_monitor_task**: Monitors warehouse configurations
        - **db_retention_monitor_task**: Monitors database, schema, and table retention settings
        
        Please ensure the tasks are properly set up in the application.
        """)
