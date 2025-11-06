"""
Database operations module
Handles all Snowflake database queries and operations
"""

import pandas as pd

def execute_sql(session, sql):
    """Execute a SQL statement"""
    session.sql(sql).collect()

def get_config_rules(session):
    """Retrieve all configuration rules"""
    query = """
    SELECT rule_id, rule_name, rule_description, warehouse_parameter, 
           comparison_operator, unit, is_active
    FROM data_schema.config_rules
    WHERE is_active = TRUE
    ORDER BY rule_name
    """
    return session.sql(query).to_pandas()


def get_applied_rules(session):
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
