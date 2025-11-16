"""
Compliance checking module
Handles warehouse compliance validation against applied rules
"""

import pandas as pd


def check_wh_compliance(warehouse_df, applied_rules_df):
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
            param = rule['CHECK_PARAMETER']
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
            is_compliant = check_compliance(operator, wh_value, threshold)
            
            if not is_compliant:
                wh_compliance['violations'].append({
                    'rule_id': rule['RULE_ID'],
                    'rule_name': rule_name,
                    'parameter': param,
                    'current_value': wh_value,
                    'threshold_value': threshold,
                    'operator': operator,
                    'unit': rule['UNIT'],
                    'has_fix_button': rule.get('HAS_FIX_BUTTON', False),
                    'has_fix_sql': rule.get('HAS_FIX_SQL', False)
                })
        
        compliance_data.append(wh_compliance)
    
    return compliance_data


def generate_wh_fix_sql(warehouse_name, parameter, threshold_value):
    """Generate SQL to fix a non-compliant warehouse"""
    if parameter == 'AUTO_SUSPEND':
        return f"ALTER WAREHOUSE {warehouse_name}\nSET AUTO_SUSPEND = {int(threshold_value)};"
    elif parameter == 'STATEMENT_TIMEOUT_IN_SECONDS':
        return f"ALTER WAREHOUSE {warehouse_name}\nSET STATEMENT_TIMEOUT_IN_SECONDS = {int(threshold_value)};"
    else:
        return f"-- No SQL available for parameter: {parameter}"

def generate_wh_post_fix_update_sql(warehouse_name, parameter, threshold_value):
    """Generate SQL to update warehouse_details after fix"""
    if parameter == 'AUTO_SUSPEND':
        return f"UPDATE data_schema.warehouse_details \nSET AUTO_SUSPEND = {int(threshold_value)} \nWHERE name = '{warehouse_name}';"
    elif parameter == 'STATEMENT_TIMEOUT_IN_SECONDS':
        return f"UPDATE data_schema.warehouse_details \nSET STATEMENT_TIMEOUT_IN_SECONDS = {int(threshold_value)} \nWHERE name = '{warehouse_name}';"
    else:
        return f"-- No SQL available for parameter: {parameter}"


def check_table_compliance(table_df, applied_rules_df):
    """Check database, schema, and table compliance against applied rules"""
    compliance_data = []
    
    # Filter for database rules only
    db_rules = applied_rules_df[applied_rules_df['RULE_TYPE'] == 'Database']
    
    for _, obj in table_df.iterrows():
        object_type = obj['OBJECT_TYPE']
        
        obj_compliance = {
            'object_type': object_type,
            'database_name': obj['DATABASE_NAME'],
            'schema_name': obj.get('SCHEMA_NAME'),
            'table_name': obj.get('TABLE_NAME'),
            'table_type': obj.get('TABLE_TYPE'),
            'table_owner': obj['OWNER'],
            'violations': []
        }
        
        for _, rule in db_rules.iterrows():
            rule_id = rule['RULE_ID']
            
            # Match rules to object types
            if object_type == 'DATABASE' and rule_id != 'MAX_DATABASE_RETENTION_TIME':
                continue
            elif object_type == 'SCHEMA' and rule_id != 'MAX_SCHEMA_RETENTION_TIME':
                continue
            elif object_type == 'TABLE' and rule_id != 'MAX_TABLE_RETENTION_TIME':
                continue
            
            param = rule['CHECK_PARAMETER']
            threshold = rule['THRESHOLD_VALUE']
            operator = rule['COMPARISON_OPERATOR']
            rule_name = rule['RULE_NAME']
            
            # Get parameter value
            if param == 'DATA_RETENTION_TIME_IN_DAYS':
                obj_value = obj['DATA_RETENTION_TIME_IN_DAYS']
            else:
                continue
            
            # Check for NULL values
            if pd.isna(obj_value):
                obj_value = None
            
            # Check compliance based on operator
            is_compliant = check_compliance(operator, obj_value, threshold)
            
            if not is_compliant:
                obj_compliance['violations'].append({
                    'rule_id': rule['RULE_ID'],
                    'rule_name': rule_name,
                    'parameter': param,
                    'current_value': obj_value,
                    'threshold_value': threshold,
                    'operator': operator,
                    'unit': rule['UNIT'],
                    'has_fix_button': rule.get('HAS_FIX_BUTTON', False),
                    'has_fix_sql': rule.get('HAS_FIX_SQL', False)
                })
        
        compliance_data.append(obj_compliance)
    
    return compliance_data


def generate_table_fix_sql(database_name, schema_name, table_name, parameter, threshold_value, object_type='TABLE'):
    """Generate SQL to fix a non-compliant database, schema, or table"""
    if parameter == 'DATA_RETENTION_TIME_IN_DAYS':
        if object_type == 'DATABASE':
            return f"ALTER DATABASE {database_name}\nSET DATA_RETENTION_TIME_IN_DAYS = {int(threshold_value)};"
        elif object_type == 'SCHEMA':
            return f"ALTER SCHEMA {database_name}.{schema_name}\nSET DATA_RETENTION_TIME_IN_DAYS = {int(threshold_value)};"
        else:  # TABLE
            full_table_name = f"{database_name}.{schema_name}.{table_name}"
            return f"ALTER TABLE {full_table_name}\nSET DATA_RETENTION_TIME_IN_DAYS = {int(threshold_value)};"
    else:
        return f"-- No SQL available for parameter: {parameter}"

def check_compliance(operator, value, threshold):
    is_compliant = True
    if operator == 'MAX' and value is not None and value > threshold:
        is_compliant = False
    elif operator == 'MIN' and value is not None and value < threshold:
        is_compliant = False
    elif operator == 'EQUALS' and value != threshold:
        is_compliant = False
    elif operator == 'NOT_EQUALS' and value == threshold:
        is_compliant = False
    return is_compliant


def check_tag_compliance(all_objects_df, tag_assignments_df, applied_tag_rules_df):
    """Check tag compliance for objects against applied tag rules
    
    Args:
        all_objects_df: DataFrame of all objects of a specific type
        tag_assignments_df: DataFrame of tag assignments from tag_compliance_details
        applied_tag_rules_df: DataFrame of applied tag rules
    
    Returns:
        List of dictionaries with compliance information for each object
    """
    compliance_data = []
    
    for _, obj in all_objects_df.iterrows():
        object_name = obj['OBJECT_NAME']
        object_database = obj.get('OBJECT_DATABASE')
        object_schema = obj.get('OBJECT_SCHEMA')
        
        # Get full object name for display
        if pd.notna(object_schema):
            full_object_name = f"{object_database}.{object_schema}.{object_name}"
        elif pd.notna(object_database):
            full_object_name = object_database
        else:
            full_object_name = object_name
        
        # Get all tags assigned to this specific object by matching on object_name
        # For warehouses: match by OBJECT_NAME directly
        # For databases: match by OBJECT_NAME (which is the database name)
        # For tables: match by OBJECT_NAME (which is the table name) and also check schema/database if needed
        object_tags_df = tag_assignments_df[tag_assignments_df['OBJECT_NAME'] == object_name]
        
        # Extract just the tag names (not the full qualified name)
        object_tags = []
        for _, tag_row in object_tags_df.iterrows():
            tag_full_name = tag_row['TAG_NAME']
            # Extract just the tag name from fully qualified name (DATABASE.SCHEMA.TAG_NAME)
            if pd.notna(tag_full_name):
                # Get the last part after the last dot (the actual tag name)
                tag_parts = str(tag_full_name).split('.')
                tag_name_only = tag_parts[-1] if tag_parts else tag_full_name
                object_tags.append(tag_name_only)
        
        obj_compliance = {
            'object_name': full_object_name,
            'object_database': object_database,
            'object_schema': object_schema,
            'object_type': obj.get('OBJECT_TYPE', applied_tag_rules_df.iloc[0]['OBJECT_TYPE'] if not applied_tag_rules_df.empty else 'UNKNOWN'),
            'table_type': obj.get('TABLE_TYPE'),
            'owner': obj.get('OWNER'),
            'assigned_tags': object_tags,
            'violations': []
        }
        
        # Check each applied tag rule
        for _, rule in applied_tag_rules_df.iterrows():
            required_tag_full = rule['TAG_NAME']
            
            # Extract just the tag name from the fully qualified tag name
            required_tag_parts = str(required_tag_full).split('.')
            required_tag = required_tag_parts[-1] if required_tag_parts else required_tag_full
            
            # Check if the required tag is missing
            if required_tag not in object_tags:
                obj_compliance['violations'].append({
                    'tag_name': required_tag_full,  # Keep full name for display
                    'rule_description': f"Compulsory tag '{required_tag_full}' missing on {rule['OBJECT_TYPE']}"
                })
        
        compliance_data.append(obj_compliance)
    
    return compliance_data


def generate_tag_fix_sql(object_name, object_type, tag_name, tag_value='<applicable_value>'):
    """Generate SQL to add a tag to an object
    
    Args:
        object_name: Full name of the object
        object_type: Type of object ('WAREHOUSE', 'DATABASE', 'TABLE')
        tag_name: Name of the tag to add
        tag_value: Value for the tag (default placeholder)
    
    Returns:
        SQL statement to add the tag
    """
    if object_type == 'WAREHOUSE':
        return f"ALTER WAREHOUSE {object_name}\nSET TAG {tag_name} = '{tag_value}';"
    elif object_type == 'DATABASE':
        return f"ALTER DATABASE {object_name}\nSET TAG {tag_name} = '{tag_value}';"
    elif object_type == 'TABLE':
        return f"ALTER TABLE {object_name}\nSET TAG {tag_name} = '{tag_value}';"
    else:
        return f"-- Unsupported object type: {object_type}"
