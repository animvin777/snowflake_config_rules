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
    SELECT rule_id, rule_name, rule_description, rule_type, check_parameter, 
           comparison_operator, unit, default_threshold, allow_threshold_override,
           is_active, has_fix_button, has_fix_sql
    FROM data_schema.config_rules
    WHERE is_active = TRUE
    ORDER BY rule_type, rule_name
    """
    return session.sql(query).to_pandas()


def get_applied_rules(session):
    """Retrieve all applied rules with their threshold values and tag scope"""
    query = """
    SELECT ar.applied_rule_id, ar.rule_id, cr.rule_name, ar.threshold_value,
           cr.rule_type, cr.check_parameter, cr.comparison_operator, cr.unit,
           ar.scope, ar.tag_name, ar.tag_value,
           ar.applied_at, ar.is_active, cr.has_fix_button, cr.has_fix_sql
    FROM data_schema.applied_rules ar
    JOIN data_schema.config_rules cr ON ar.rule_id = cr.rule_id
    WHERE ar.is_active = TRUE
    ORDER BY ar.applied_at DESC
    """
    return session.sql(query).to_pandas()


def generate_rule_display_name(rule_name, scope, tag_name=None, tag_value=None):
    """Generate a descriptive rule name based on scope and tag criteria
    
    Args:
        rule_name: Base rule name
        scope: 'ALL' or 'TAG_BASED'
        tag_name: Tag name (if TAG_BASED)
        tag_value: Tag value (if TAG_BASED)
    
    Returns:
        str: Formatted rule name with scope information
    """
    if scope == 'TAG_BASED' and tag_name:
        if tag_value:
            return f"{rule_name} [Tag: {tag_name}={tag_value}]"
        else:
            return f"{rule_name} [Tag: {tag_name}]"
    else:
        return f"{rule_name} [All Objects]"


def get_wh_statement_timeout_default(session):
    """Retrieve the default statement timeout value for warehouses to fix 0 value set"""
    query = """
    SELECT threshold_value
    FROM data_schema.applied_rules ar
    where ar.rule_id = 'MAX_STATEMENT_TIMEOUT' AND ar.is_active = TRUE
    union
    SELECT cr.default_threshold as threshold_value
    FROM data_schema.config_rules cr
    where cr.rule_id = 'MAX_STATEMENT_TIMEOUT'
    order by threshold_value desc
    LIMIT 1
    """
    result = session.sql(query).to_pandas()
    if not result.empty:
        return result.iloc[0]['THRESHOLD_VALUE']
    return 3600*4  # Default to 4 hours if not set


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


def apply_rule(session, rule_id, threshold_value, scope='ALL', tag_name=None, tag_value=None):
    """Apply a configuration rule with a threshold value and optional tag-based scope
    
    Args:
        session: Snowflake session
        rule_id: ID of the rule to apply
        threshold_value: Threshold value for the rule
        scope: 'ALL' for all objects, or 'TAG_BASED' for specific tagged objects
        tag_name: Tag name for tag-based rules (required if scope='TAG_BASED')
        tag_value: Tag value for tag-based rules (required if scope='TAG_BASED')
    """
    # Validate tag-based rules
    if scope == 'TAG_BASED' and (not tag_name or tag_value is None):
        raise ValueError("tag_name and tag_value are required for TAG_BASED scope")
    
    # Set NULL for tag fields if scope is ALL
    tag_name_val = f"'{tag_name}'" if scope == 'TAG_BASED' and tag_name else 'NULL'
    tag_value_val = f"'{tag_value}'" if scope == 'TAG_BASED' and tag_value is not None else 'NULL'
    
    # Deactivate any existing active rule with same scope and tag criteria
    deactivate_query = f"""
    UPDATE data_schema.applied_rules 
    SET is_active = FALSE 
    WHERE rule_id = '{rule_id}' 
      AND scope = '{scope}'
      AND COALESCE(tag_name, '') = COALESCE({tag_name_val}, '')
      AND COALESCE(tag_value, '') = COALESCE({tag_value_val}, '')
      AND is_active = TRUE
    """
    execute_sql(session, deactivate_query)
    
    # Insert new applied rule
    insert_query = f"""
    INSERT INTO data_schema.applied_rules 
        (rule_id, threshold_value, scope, tag_name, tag_value, applied_by)
    VALUES 
        ('{rule_id}', {threshold_value}, '{scope}', {tag_name_val}, {tag_value_val}, CURRENT_USER())
    """
    execute_sql(session, insert_query)


def get_available_tag_names(session):
    """Get list of available tags in the account
    
    Returns:
        DataFrame with tag names from SNOWFLAKE.ACCOUNT_USAGE.TAGS
    """
    query = """
    SELECT DISTINCT tag_name
    FROM SNOWFLAKE.ACCOUNT_USAGE.TAGS
    WHERE deleted IS NULL
    ORDER BY tag_name
    """
    try:
        return session.sql(query).to_pandas()
    except Exception as e:
        # Return empty dataframe if account usage not accessible
        import pandas as pd
        return pd.DataFrame(columns=['TAG_NAME'])


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
    """Execute a task immediately and return the query ID"""
    query = f"EXECUTE TASK {task_name}"
    result = session.sql(query).collect()
    # Get the query ID from the last executed statement
    query_id_result = session.sql("SELECT LAST_QUERY_ID() as query_id").collect()
    if query_id_result:
        return query_id_result[0]['QUERY_ID']
    return None


def wait_for_task_completion(session, task_name, execution_time, max_wait_seconds=60, poll_interval=2):
    """Wait for a task to complete execution
    
    Args:
        session: Snowflake session
        task_name: Name of the task (without schema prefix)
        execution_time: Timestamp when execute_task was called
        max_wait_seconds: Maximum time to wait in seconds
        poll_interval: Seconds between status checks
    
    Returns:
        tuple: (success: bool, state: str, error_message: str or None)
    """
    import time
    
    elapsed = 0
    while elapsed < max_wait_seconds:
        # Query task history from INFORMATION_SCHEMA for real-time data
        # Note: Using data_schema as that's where tasks are created
        query = f"""
        SELECT state, error_message, scheduled_time, completed_time
        FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
            TASK_NAME => 'DATA_SCHEMA.{task_name.upper()}',
            SCHEDULED_TIME_RANGE_START => DATEADD(minute, -5, CURRENT_TIMESTAMP())
        ))
        WHERE scheduled_time >= '{execution_time}'
        ORDER BY scheduled_time DESC
        LIMIT 1
        """
        
        try:
            result = session.sql(query).to_pandas()
            
            if not result.empty:
                state = result.iloc[0]['STATE']
                error_message = result.iloc[0].get('ERROR_MESSAGE')
                
                if state == 'SUCCEEDED':
                    return True, state, None
                elif state == 'FAILED':
                    return False, state, error_message
                elif state in ['SCHEDULED', 'EXECUTING']:
                    # Task is still running, continue waiting
                    time.sleep(poll_interval)
                    elapsed += poll_interval
                else:
                    # Unknown state
                    time.sleep(poll_interval)
                    elapsed += poll_interval
            else:
                # No history yet for this execution, wait a bit
                time.sleep(poll_interval)
                elapsed += poll_interval
        except Exception as e:
            # If we can't check status, wait and retry
            time.sleep(poll_interval)
            elapsed += poll_interval
    
    # Timeout reached
    return False, 'TIMEOUT', f'Task did not complete within {max_wait_seconds} seconds'


# ===================================
# TAG RULES FUNCTIONS
# ===================================

def get_available_tags(session):
    """Retrieve all available tags from SNOWFLAKE.ACCOUNT_USAGE.TAGS"""
    query = """
    SELECT DISTINCT 
        tag_database,
        tag_schema,
        tag_name
    FROM SNOWFLAKE.ACCOUNT_USAGE.TAGS
    WHERE deleted IS NULL
    ORDER BY tag_database, tag_schema, tag_name
    """
    return session.sql(query).to_pandas()


def get_applied_tag_rules(session):
    """Retrieve all applied tag rules"""
    query = """
    SELECT 
        applied_tag_rule_id,
        tag_name,
        object_type,
        applied_at,
        applied_by,
        is_active
    FROM data_schema.applied_tag_rules
    WHERE is_active = TRUE
    ORDER BY applied_at DESC
    """
    return session.sql(query).to_pandas()


def apply_tag_rule(session, tag_name, object_type):
    """Apply a tag rule for a specific tag and object type
    
    Args:
        session: Snowflake session
        tag_name: Name of the tag to check for
        object_type: Type of object ('WAREHOUSE', 'DATABASE', 'TABLE')
    """
    # Check if this combination already exists
    check_query = f"""
    SELECT COUNT(*) as count
    FROM data_schema.applied_tag_rules
    WHERE tag_name = '{tag_name}' 
      AND object_type = '{object_type}'
      AND is_active = TRUE
    """
    result = session.sql(check_query).to_pandas()
    
    if result.iloc[0]['COUNT'] > 0:
        raise ValueError(f"Tag rule for '{tag_name}' on {object_type} already exists")
    
    # Insert new tag rule
    insert_query = f"""
    INSERT INTO data_schema.applied_tag_rules (tag_name, object_type, applied_by)
    VALUES ('{tag_name}', '{object_type}', CURRENT_USER())
    """
    execute_sql(session, insert_query)


def deactivate_tag_rule(session, applied_tag_rule_id):
    """Deactivate an applied tag rule"""
    query = f"""
    UPDATE data_schema.applied_tag_rules 
    SET is_active = FALSE 
    WHERE applied_tag_rule_id = {applied_tag_rule_id}
    """
    execute_sql(session, query)


def get_tag_compliance_details(session, object_type=None):
    """Retrieve tag compliance details for objects
    
    Args:
        session: Snowflake session
        object_type: Filter by object type ('WAREHOUSE', 'DATABASE', 'TABLE'). If None, returns all.
    """
    object_type_filter = f"AND object_type = '{object_type}'" if object_type else ""
    
    query = f"""
    SELECT DISTINCT 
        object_type,
        object_database,
        object_schema,
        object_name,
        tag_name,
        tag_value,
        capture_timestamp
    FROM data_schema.tag_compliance_details
    WHERE 1=1 {object_type_filter}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY object_type, object_name, tag_name
        ORDER BY capture_timestamp DESC
    ) = 1
    ORDER BY object_type, object_name, tag_name
    """
    return session.sql(query).to_pandas()


def get_all_objects_by_type(session, object_type):
    """Get all objects of a specific type for tag compliance checking
    
    Args:
        session: Snowflake session
        object_type: Type of object ('WAREHOUSE', 'DATABASE', 'TABLE')
    """
    if object_type == 'WAREHOUSE':
        query = """
        SELECT DISTINCT name as object_name, NULL as object_database, NULL as object_schema
        FROM data_schema.warehouse_details
        QUALIFY ROW_NUMBER() OVER (PARTITION BY name ORDER BY capture_timestamp DESC) = 1
        """
    elif object_type == 'DATABASE':
        query = """
        SELECT DISTINCT database_name as object_name, database_name as object_database, NULL as object_schema
        FROM data_schema.database_retention_details
        WHERE object_type = 'DATABASE'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY database_name ORDER BY capture_timestamp DESC) = 1
        """
    elif object_type == 'TABLE':
        query = """
        SELECT DISTINCT 
            table_name as object_name,
            database_name as object_database,
            schema_name as object_schema,
            table_type,
            owner
        FROM data_schema.database_retention_details
        WHERE object_type = 'TABLE'
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY database_name, schema_name, table_name 
            ORDER BY capture_timestamp DESC
        ) = 1
        """
    else:
        return pd.DataFrame()
    
    return session.sql(query).to_pandas()


# ===================================
# WHITELIST FUNCTIONS
# ===================================

def add_to_whitelist(session, rule_id, applied_rule_id, object_type, object_name, 
                     database_name=None, schema_name=None, table_name=None, tag_name=None, reason=None):
    """Add a violation to the whitelist
    
    Args:
        session: Snowflake session
        rule_id: ID of the rule being whitelisted
        applied_rule_id: ID of the applied rule instance
        object_type: Type of object ('WAREHOUSE', 'DATABASE', 'SCHEMA', 'TABLE')
        object_name: Fully qualified name of the object
        database_name: Database name (for database objects)
        schema_name: Schema name (for schema/table objects)
        table_name: Table name (for table objects)
        tag_name: Tag name (for tag compliance violations)
        reason: Optional reason for whitelisting
    """
    # Escape single quotes in strings
    object_name_escaped = object_name.replace("'", "''") if object_name else ''
    reason_escaped = reason.replace("'", "''") if reason else None
    tag_name_escaped = tag_name.replace("'", "''") if tag_name else None
    
    # Build values for optional fields
    db_val = f"'{database_name}'" if database_name else 'NULL'
    schema_val = f"'{schema_name}'" if schema_name else 'NULL'
    table_val = f"'{table_name}'" if table_name else 'NULL'
    tag_val = f"'{tag_name_escaped}'" if tag_name_escaped else 'NULL'
    reason_val = f"'{reason_escaped}'" if reason_escaped else 'NULL'
    applied_rule_val = f"{applied_rule_id}" if applied_rule_id else 'NULL'
    
    # Check if already whitelisted - for tag violations, also check tag_name
    tag_check = f"AND COALESCE(tag_name, '') = COALESCE({tag_val}, '')" if rule_id == 'MISSING_TAG_VALUE' else ""
    
    check_query = f"""
    SELECT COUNT(*) as count
    FROM data_schema.rule_whitelist
    WHERE rule_id = '{rule_id}'
      AND object_type = '{object_type}'
      AND object_name = '{object_name_escaped}'
      {tag_check}
      AND is_active = TRUE
    """
    result = session.sql(check_query).to_pandas()
    
    if result.iloc[0]['COUNT'] > 0:
        raise ValueError(f"This violation is already whitelisted")
    
    # Insert whitelist entry
    insert_query = f"""
    INSERT INTO data_schema.rule_whitelist 
        (rule_id, applied_rule_id, object_type, object_name, database_name, schema_name, table_name, tag_name, reason, whitelisted_by)
    VALUES 
        ('{rule_id}', {applied_rule_val}, '{object_type}', '{object_name_escaped}', {db_val}, {schema_val}, {table_val}, {tag_val}, {reason_val}, CURRENT_USER())
    """
    execute_sql(session, insert_query)


def remove_from_whitelist(session, whitelist_id):
    """Remove a violation from the whitelist
    
    Args:
        session: Snowflake session
        whitelist_id: ID of the whitelist entry to remove
    """
    query = f"""
    UPDATE data_schema.rule_whitelist
    SET is_active = FALSE
    WHERE whitelist_id = {whitelist_id}
    """
    execute_sql(session, query)


def bulk_remove_from_whitelist(session, whitelist_ids):
    """Remove multiple violations from the whitelist
    
    Args:
        session: Snowflake session
        whitelist_ids: List of whitelist IDs to remove
    """
    if not whitelist_ids:
        return
    
    ids_str = ','.join(str(id) for id in whitelist_ids)
    query = f"""
    UPDATE data_schema.rule_whitelist
    SET is_active = FALSE
    WHERE whitelist_id IN ({ids_str})
    """
    execute_sql(session, query)


def get_whitelisted_violations(session, rule_id=None, object_type=None):
    """Get all whitelisted violations
    
    Args:
        session: Snowflake session
        rule_id: Optional filter by rule ID
        object_type: Optional filter by object type
    
    Returns:
        DataFrame with whitelist entries
    """
    rule_filter = f"AND wl.rule_id = '{rule_id}'" if rule_id else ""
    type_filter = f"AND wl.object_type = '{object_type}'" if object_type else ""
    
    query = f"""
    SELECT 
        wl.whitelist_id,
        wl.rule_id,
        cr.rule_name,
        cr.rule_type,
        wl.applied_rule_id,
        wl.object_type,
        wl.object_name,
        wl.database_name,
        wl.schema_name,
        wl.table_name,
        wl.tag_name,
        wl.reason,
        wl.whitelisted_by,
        wl.whitelisted_at,
        wl.is_active
    FROM data_schema.rule_whitelist wl
    LEFT JOIN data_schema.config_rules cr ON wl.rule_id = cr.rule_id
    WHERE wl.is_active = TRUE
    {rule_filter}
    {type_filter}
    ORDER BY wl.whitelisted_at DESC
    """
    return session.sql(query).to_pandas()


def is_violation_whitelisted(session, rule_id, object_name):
    """Check if a specific violation is whitelisted
    
    Args:
        session: Snowflake session
        rule_id: ID of the rule
        object_name: Name of the object
    
    Returns:
        bool: True if whitelisted, False otherwise
    """
    object_name_escaped = object_name.replace("'", "''") if object_name else ''
    
    query = f"""
    SELECT COUNT(*) as count
    FROM data_schema.rule_whitelist
    WHERE rule_id = '{rule_id}'
      AND object_name = '{object_name_escaped}'
      AND is_active = TRUE
    """
    result = session.sql(query).to_pandas()
    return result.iloc[0]['COUNT'] > 0
