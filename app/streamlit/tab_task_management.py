"""
Task Management Tab
Handles the display and control of all tasks in the application
"""

import time
import streamlit as st
from database import execute_sql, get_all_tasks, get_task_history, suspend_task, resume_task, execute_task, wait_for_task_completion
from ui_utils import render_refresh_button, render_section_header
import pandas as pd


def render_task_management_tab(session):
    """Render the Task Management tab"""
    # Refresh button in top right
    col_title, col_refresh = render_refresh_button("tab_tasks")
    with col_title:
        render_section_header("Schedule & Task Management", "schedule-icon")
    with col_refresh:
        if st.button("⟳", key="refresh_tab_tasks", help="Refresh data"):
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
            
            st.markdown("---")
            
            # Create table header
            st.html("""
                <table class="task-table">
                    <thead>
                        <tr>
                            <th>Task Name</th>
                            <th>State</th>
                            <th>Schedule</th>
                            <th>Owner</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                </table>
            """)
            
            # Display each task in table rows
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
                
                # Determine state styling
                state_class = "task-state-started" if task_state == 'started' else "task-state-suspended"
                
                # Create table row
                col_name, col_state, col_schedule, col_owner, col_actions = st.columns([2, 1, 2, 1.5, 2.5])
                
                with col_name:
                    st.markdown(f"**{task_name}**")
                
                with col_state:
                    st.html(f'<span class="{state_class}">{task_state.upper()}</span>')
                
                with col_schedule:
                    st.markdown(task_schedule)
                
                with col_owner:
                    st.markdown(task_owner)
                
                with col_actions:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    
                    with btn_col1:
                        if task_state == 'started':
                            if st.button("Suspend", key=f"suspend_{unique_key}", use_container_width=True):
                                try:
                                    suspend_task(session, full_task_name)
                                    st.success(f"Task {task_name} suspended")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                        else:
                            if st.button("Resume", key=f"resume_{unique_key}", use_container_width=True):
                                try:
                                    resume_task(session, full_task_name)
                                    st.success(f"Task {task_name} resumed")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                    
                    with btn_col2:
                        if st.button("Execute", key=f"execute_{unique_key}", use_container_width=True):
                            try:
                                execute_task(session, full_task_name)
                                st.success(f"Task {task_name} executed")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    
                    with btn_col3:
                        if st.button("History", key=f"history_{unique_key}", use_container_width=True):
                            # Set session state to show this task's history
                            st.session_state['current_task_history'] = task_name

                st.markdown("---")
            
            # Show task history below the table
            if 'current_task_history' in st.session_state and st.session_state['current_task_history']:
                task_name = st.session_state['current_task_history']
                st.html(f'<div class="task-history-container">')
                st.html(f'<h5><span class="chart-icon"></span> Last 3 Runs for {task_name}</h5>')
                history_df = get_task_history(session, task_name)
                
                if not history_df.empty:
                    for hist_idx, run in history_df.iterrows():
                        state_color = "green" if run['STATE'] == 'SUCCEEDED' else ("orange" if run['STATE'] == 'SCHEDULED' else "red")
                        error_info = ""
                        if run['STATE'] == 'FAILED' and run['ERROR_MESSAGE']:
                            error_info = f"<br><strong>Error:</strong> {run['ERROR_MESSAGE']}"
                        
                        st.html(f"""
                            <div style="padding: 10px; margin: 5px 0; background-color: #f8f9fa; border-left: 3px solid {state_color};">
                                <strong>Status:</strong> <span style="color: {state_color};">{run['STATE']}</span><br>
                                <strong>Scheduled:</strong> {run['SCHEDULED_TIME']}<br>
                                <strong>Completed:</strong> {run['COMPLETED_TIME'] if run['COMPLETED_TIME'] else 'N/A'}<br>
                                <strong>Duration:</strong> {run['DURATION_SECONDS'] if run['DURATION_SECONDS'] else 'N/A'} seconds
                                {error_info}
                            </div>
                        """)
                else:
                    st.info("No execution history found for this task in the last 7 days.")
                st.html('</div>')
            
            # Add collapsible informational section
            with st.expander("Task Information", expanded=False):
                st.html("""
                    <div class="task-info-section">
                        <p><strong>warehouse_monitor_task</strong>: Captures warehouse configuration details every day at 7:00 AM EST.</p>
                        
                        <p><strong>db_retention_monitor_task</strong>: Captures database, schema, and table retention time information every day at 7:00 AM EST.</p>
                        
                        <p><strong>tag_monitor_task</strong>: Captures tag assignments on warehouses, databases, and tables every day at 7:05 AM EST.</p>
                        
                        <p><strong>warehouse_params_monitor_task</strong> (if created by consumer): Custom task for monitoring additional warehouse parameters.</p>
                        
                        <p><strong>Execution Order</strong>: When using "Execute All Tasks", tasks run sequentially in dependency order:</p>
                        <ol>
                            <li>warehouse_monitor_task (base data collection)</li>
                            <li>db_retention_monitor_task (depends on warehouse data)</li>
                            <li>tag_monitor_task (depends on database data)</li>
                            <li>warehouse_params_monitor_task (if exists, depends on warehouse data)</li>
                        </ol>
                        
                        <p>You can execute tasks immediately using the "Execute" button, suspend/resume them as needed, and view execution history with the "History" button.</p>
                    </div>
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
        - **tag_monitor_task**: Monitors tag assignments on objects
        
        Please ensure the tasks are properly set up in the application.
        """)
