"""
Database operations module
Handles all Snowflake database queries and operations
"""

import pandas as pd
import streamlit as st

def execute_sql(session, sql):
    """Execute a SQL statement"""
    session.sql(sql).collect()

def get_config_rules(session):
    """Retrieve all configuration rules"""
    query = """
    SELECT rule_id, rule_name, rule_description, rule_type, warehouse_parameter, 
           comparison_operator, unit, is_active, has_fix_button, has_fix_sql
    FROM data_schema.config_rules
    WHERE is_active = TRUE
    ORDER BY rule_type, rule_name
    """
    return session.sql(query).to_pandas()


def get_applied_rules(session):
    """Retrieve all applied rules with their threshold values"""
    query = """
    SELECT ar.applied_rule_id, ar.rule_id, cr.rule_name, ar.threshold_value,
           cr.rule_type, cr.warehouse_parameter, cr.comparison_operator, cr.unit,
           ar.applied_at, ar.is_active, cr.has_fix_button, cr.has_fix_sql
    FROM data_schema.applied_rules ar
    JOIN data_schema.config_rules cr ON ar.rule_id = cr.rule_id
    WHERE ar.is_active = TRUE
    ORDER BY ar.applied_at DESC
    """
    return session.sql(query).to_pandas()


def get_warehouse_details(session):
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


def apply_rule(session, rule_id, threshold_value):
    """Apply a configuration rule with a threshold value"""
    # Deactivate any existing active rule for this rule_id
    deactivate_query = f"""
    UPDATE data_schema.applied_rules 
    SET is_active = FALSE 
    WHERE rule_id = '{rule_id}' AND is_active = TRUE
    """
    execute_sql(session, deactivate_query)
    
    # Insert new applied rule
    insert_query = f"""
    INSERT INTO data_schema.applied_rules (rule_id, threshold_value, applied_by)
    VALUES ('{rule_id}', {threshold_value}, CURRENT_USER())
    """
    execute_sql(session, insert_query)


def deactivate_applied_rule(session, applied_rule_id):
    """Deactivate an applied rule"""
    query = f"""
    UPDATE data_schema.applied_rules 
    SET is_active = FALSE 
    WHERE applied_rule_id = {applied_rule_id}
    """
    execute_sql(session, query)


def get_database_retention_details(session, object_type=None):
    """Retrieve latest database, schema, and table retention details
    
    Args:
        session: Snowflake session
        object_type: Filter by object type ('DATABASE', 'SCHEMA', 'TABLE'). If None, returns all.
    """
    object_type_filter = f"AND object_type = '{object_type}'" if object_type else ""
    
    query = f"""
    SELECT DISTINCT 
        object_type, database_name, schema_name, table_name, table_type,
        data_retention_time_in_days, owner, created_on, last_altered,
        row_count, bytes, comment, capture_timestamp
    FROM data_schema.database_retention_details
    WHERE 1=1 {object_type_filter}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY object_type, database_name, 
                     COALESCE(schema_name, ''), 
                     COALESCE(table_name, '') 
        ORDER BY capture_timestamp DESC
    ) = 1
    ORDER BY object_type, database_name, schema_name, table_name
    """
    return session.sql(query).to_pandas()


# Keep backwards compatibility
def get_table_retention_details(session):
    """Retrieve latest table retention details (backward compatibility)"""
    return get_database_retention_details(session, object_type='TABLE')


def get_all_tasks(session):
    """Retrieve all tasks in the application - includes consumer created tasks"""
    query = """
    SHOW TASKS IN DATABASE SNOWFLAKE_CONFIG_RULES_APP
    """
    return session.sql(query).to_pandas()


def get_task_history(session, task_name):
    """Retrieve last 3 run details for a specific task"""
    query = f"""
    SELECT 
        name,
        state,
        scheduled_time,
        completed_time,
        DATEDIFF('second', scheduled_time, completed_time) as duration_seconds,
        return_value,
        error_code,
        error_message
    from SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY
        where name = '{task_name}'      
    ORDER BY completed_time DESC
    LIMIT 3
    """
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        # Return empty dataframe if task has no history
        return pd.DataFrame()


def suspend_task(session, task_name):
    """Suspend a task"""
    query = f"ALTER TASK {task_name} SUSPEND"
    execute_sql(session, query)


def resume_task(session, task_name):
    """Resume a task"""
    query = f"ALTER TASK {task_name} RESUME"
    execute_sql(session, query)


def execute_task(session, task_name):
    """Execute a task immediately"""
    query = f"EXECUTE TASK {task_name}"
    execute_sql(session, query)
