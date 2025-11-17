"""
Compliance checking module
Handles warehouse compliance validation against applied rules
"""

import pandas as pd


def check_rule_applies_to_object(rule, object_tags):
    """Check if a rule applies to an object based on scope and tags
    
    Args:
        rule: Rule row from applied_rules with SCOPE, TAG_NAME, TAG_VALUE
        object_tags: Dict of {tag_name: tag_value} for the object (tag names should be uppercase)
    
    Returns:
        bool: True if rule applies to this object
    """
    scope = rule.get('SCOPE', 'ALL')
    
    # ALL scope applies to all objects
    if scope == 'ALL':
        return True
    
    # TAG_BASED scope requires matching tag
    if scope == 'TAG_BASED':
        tag_name = rule.get('TAG_NAME')
        tag_value = rule.get('TAG_VALUE')
        
        if not tag_name:
            return False
        
        # Normalize tag name for comparison (extract simple name and uppercase)
        tag_name_parts = str(tag_name).split('.')
        tag_name_simple = tag_name_parts[-1] if tag_name_parts else tag_name
        tag_name_normalized = tag_name_simple.upper()
        
        # Check if object has this tag (object_tags keys should already be normalized)
        if tag_name_normalized not in object_tags:
            return False
        
        # If tag_value is specified, it must match
        if tag_value is not None and object_tags.get(tag_name_normalized) != tag_value:
            return False
        
        return True
    
    return False


def check_wh_compliance(warehouse_df, applied_rules_df, tag_df, whitelist_df):
    """Check warehouse compliance against applied rules
    
    Args:
        warehouse_df: DataFrame with warehouse details
        applied_rules_df: DataFrame with applied rules (includes SCOPE, TAG_NAME, TAG_VALUE)
        tag_df: DataFrame with tag compliance details for warehouses
        whitelist_df: DataFrame with whitelisted violations
    """
    compliance_data = []
    
    # Filter for warehouse rules only
    wh_rules = applied_rules_df[applied_rules_df['RULE_TYPE'] == 'Warehouse']
    
    for _, wh in warehouse_df.iterrows():
        wh_name = wh['NAME']
        
        # Get tags for this warehouse
        wh_tags = {}
        if tag_df is not None and not tag_df.empty:
            wh_tag_rows = tag_df[
                (tag_df['OBJECT_TYPE'] == 'WAREHOUSE') & 
                (tag_df['OBJECT_NAME'] == wh_name)
            ]
            for _, tag_row in wh_tag_rows.iterrows():
                if pd.notna(tag_row.get('TAG_NAME')) and pd.notna(tag_row.get('TAG_VALUE')):
                    # Normalize tag name: extract simple name and uppercase
                    tag_full_name = tag_row['TAG_NAME']
                    tag_parts = str(tag_full_name).split('.')
                    tag_name_simple = tag_parts[-1] if tag_parts else tag_full_name
                    wh_tags[tag_name_simple.upper()] = tag_row['TAG_VALUE']
        
        wh_compliance = {
            'warehouse_name': wh_name,
            'warehouse_type': wh['TYPE'],
            'warehouse_size': wh['SIZE'],
            'warehouse_owner': wh['OWNER'],
            'violations': [],
            'compliant_rules': []
        }
        
        for _, rule in wh_rules.iterrows():
            # Check if this rule applies to this warehouse based on scope and tags
            if not check_rule_applies_to_object(rule, wh_tags):
                continue
            
            param = rule['CHECK_PARAMETER']
            threshold = rule['THRESHOLD_VALUE']
            operator = rule['COMPARISON_OPERATOR']
            
            # Generate display name with scope
            from database import generate_rule_display_name
            rule_name = generate_rule_display_name(
                rule['RULE_NAME'],
                rule.get('SCOPE', 'ALL'),
                rule.get('TAG_NAME'),
                rule.get('TAG_VALUE')
            )
            
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
                # Check if this violation is whitelisted
                is_whitelisted = False
                if whitelist_df is not None and not whitelist_df.empty:
                    whitelisted = whitelist_df[
                        (whitelist_df['RULE_ID'] == rule['RULE_ID']) &
                        (whitelist_df['OBJECT_NAME'] == wh_name) &
                        (whitelist_df['OBJECT_TYPE'] == 'WAREHOUSE')
                    ]
                    is_whitelisted = not whitelisted.empty
                
                # Add violation with whitelisted flag
                wh_compliance['violations'].append({
                    'rule_id': rule['RULE_ID'],
                    'rule_name': rule_name,
                    'parameter': param,
                    'current_value': wh_value,
                    'threshold_value': threshold,
                    'operator': operator,
                    'unit': rule['UNIT'],
                    'has_fix_button': rule.get('HAS_FIX_BUTTON', False),
                    'has_fix_sql': rule.get('HAS_FIX_SQL', False),
                    'applied_rule_id': rule.get('APPLIED_RULE_ID'),
                    'is_whitelisted': is_whitelisted
                })
            else:
                # Track compliant rules
                wh_compliance['compliant_rules'].append({
                    'rule_name': rule_name,
                    'parameter': param
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


def check_table_compliance(table_df, applied_rules_df, tag_df, whitelist_df):
    """Check database, schema, and table compliance against applied rules
    
    Args:
        table_df: DataFrame with database/schema/table details
        applied_rules_df: DataFrame with applied rules (includes SCOPE, TAG_NAME, TAG_VALUE)
        tag_df: DataFrame with tag compliance details for databases/tables
        whitelist_df: DataFrame with whitelisted violations
    """
    compliance_data = []
    
    # Filter for database rules only
    db_rules = applied_rules_df[applied_rules_df['RULE_TYPE'] == 'Database']
    
    for _, obj in table_df.iterrows():
        object_type = obj['OBJECT_TYPE']
        db_name = obj['DATABASE_NAME']
        schema_name = obj.get('SCHEMA_NAME')
        table_name = obj.get('TABLE_NAME')
        
        # Construct object identifier for tag lookup
        if object_type == 'DATABASE':
            obj_identifier = db_name
        elif object_type == 'SCHEMA':
            obj_identifier = f"{db_name}.{schema_name}" if schema_name else db_name
        elif object_type == 'TABLE':
            obj_identifier = f"{db_name}.{schema_name}.{table_name}" if schema_name and table_name else db_name
        else:
            obj_identifier = db_name
        
        # Get tags for this object
        obj_tags = {}
        if tag_df is not None and not tag_df.empty:
            obj_tag_rows = tag_df[
                (tag_df['OBJECT_TYPE'] == object_type) & 
                (tag_df['OBJECT_NAME'] == obj_identifier)
            ]
            # Also try matching by individual components for tables if columns exist
            # Note: whitelist table uses DATABASE_NAME, SCHEMA_NAME, TABLE_NAME
            if obj_tag_rows.empty and object_type == 'TABLE':
                if all(col in tag_df.columns for col in ['DATABASE_NAME', 'SCHEMA_NAME', 'TABLE_NAME']):
                    obj_tag_rows = tag_df[
                        (tag_df['OBJECT_TYPE'] == 'TABLE') &
                        (tag_df['DATABASE_NAME'] == db_name) &
                        (tag_df['SCHEMA_NAME'] == schema_name) &
                        (tag_df['TABLE_NAME'] == table_name)
                    ]
            
            for _, tag_row in obj_tag_rows.iterrows():
                if pd.notna(tag_row.get('TAG_NAME')) and pd.notna(tag_row.get('TAG_VALUE')):
                    # Normalize tag name: extract simple name and uppercase
                    tag_full_name = tag_row['TAG_NAME']
                    tag_parts = str(tag_full_name).split('.')
                    tag_name_simple = tag_parts[-1] if tag_parts else tag_full_name
                    obj_tags[tag_name_simple.upper()] = tag_row['TAG_VALUE']
        
        obj_compliance = {
            'object_type': object_type,
            'database_name': db_name,
            'schema_name': schema_name,
            'table_name': table_name,
            'table_type': obj.get('TABLE_TYPE'),
            'table_owner': obj['OWNER'],
            'violations': [],
            'compliant_rules': []
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
            
            # Check if this rule applies to this object based on scope and tags
            if not check_rule_applies_to_object(rule, obj_tags):
                continue
            
            param = rule['CHECK_PARAMETER']
            threshold = rule['THRESHOLD_VALUE']
            operator = rule['COMPARISON_OPERATOR']
            
            # Generate display name with scope
            from database import generate_rule_display_name
            rule_name = generate_rule_display_name(
                rule['RULE_NAME'],
                rule.get('SCOPE', 'ALL'),
                rule.get('TAG_NAME'),
                rule.get('TAG_VALUE')
            )
            
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
                # Check if this violation is whitelisted
                is_whitelisted = False
                if whitelist_df is not None and not whitelist_df.empty:
                    whitelisted = whitelist_df[
                        (whitelist_df['RULE_ID'] == rule['RULE_ID']) &
                        (whitelist_df['OBJECT_NAME'] == obj_identifier) &
                        (whitelist_df['OBJECT_TYPE'] == object_type)
                    ]
                    is_whitelisted = not whitelisted.empty
                
                # Add violation with whitelisted flag
                obj_compliance['violations'].append({
                    'rule_id': rule['RULE_ID'],
                    'rule_name': rule_name,
                    'parameter': param,
                    'current_value': obj_value,
                    'threshold_value': threshold,
                    'operator': operator,
                    'unit': rule['UNIT'],
                    'has_fix_button': rule.get('HAS_FIX_BUTTON', False),
                    'has_fix_sql': rule.get('HAS_FIX_SQL', False),
                    'applied_rule_id': rule.get('APPLIED_RULE_ID'),
                    'is_whitelisted': is_whitelisted
                })
            else:
                # Track compliant rules
                obj_compliance['compliant_rules'].append({
                    'rule_name': rule_name,
                    'parameter': param
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


def check_tag_compliance(all_objects_df, tag_assignments_df, applied_tag_rules_df, whitelist_df):
    """Check tag compliance for objects against applied tag rules
    
    Args:
        all_objects_df: DataFrame of all objects of a specific type
        tag_assignments_df: DataFrame of tag assignments from tag_compliance_details
        applied_tag_rules_df: DataFrame of applied tag rules
        whitelist_df: DataFrame with whitelisted violations
    
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
        
        # Get all tags assigned to this specific object
        # Different matching strategy based on object type
        # Use case-insensitive comparison by converting to uppercase
        if pd.notna(object_schema):
            # For tables: match on database, schema, and table name
            if 'OBJECT_DATABASE' in tag_assignments_df.columns and 'OBJECT_SCHEMA' in tag_assignments_df.columns:
                object_tags_df = tag_assignments_df[
                    (tag_assignments_df['OBJECT_NAME'].str.upper() == str(object_name).upper()) &
                    (tag_assignments_df['OBJECT_DATABASE'].str.upper() == str(object_database).upper()) &
                    (tag_assignments_df['OBJECT_SCHEMA'].str.upper() == str(object_schema).upper())
                ]
            else:
                object_tags_df = pd.DataFrame()
        elif pd.notna(object_database):
            # For databases: match on database name
            if 'OBJECT_DATABASE' in tag_assignments_df.columns:
                object_tags_df = tag_assignments_df[
                    (tag_assignments_df['OBJECT_NAME'].str.upper() == str(object_name).upper()) &
                    (tag_assignments_df['OBJECT_DATABASE'].str.upper() == str(object_database).upper())
                ]
            else:
                object_tags_df = pd.DataFrame()
        else:
            # For warehouses: match by object name only (case-insensitive)
            object_tags_df = tag_assignments_df[
                tag_assignments_df['OBJECT_NAME'].str.upper() == str(object_name).upper()
            ]
        
        # Extract just the tag names (not the full qualified name) and normalize them
        object_tags = []
        for _, tag_row in object_tags_df.iterrows():
            tag_full_name = tag_row['TAG_NAME']
            # Extract just the tag name from fully qualified name (DATABASE.SCHEMA.TAG_NAME)
            if pd.notna(tag_full_name):
                # Get the last part after the last dot (the actual tag name)
                tag_parts = str(tag_full_name).split('.')
                tag_name_only = tag_parts[-1] if tag_parts else tag_full_name
                # Normalize to uppercase for consistent comparison
                object_tags.append(tag_name_only.upper())
        
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
            
            # Extract just the tag name from the fully qualified tag name and normalize
            required_tag_parts = str(required_tag_full).split('.')
            required_tag = required_tag_parts[-1] if required_tag_parts else required_tag_full
            required_tag_normalized = required_tag.upper()
            
            # Check if the required tag is missing (compare normalized versions)
            if required_tag_normalized not in object_tags:
                # Check if this violation is whitelisted
                is_whitelisted = False
                if whitelist_df is not None and not whitelist_df.empty:
                    # For tag violations, we need to match on object, tag, and rule
                    whitelisted = whitelist_df[
                        (whitelist_df['OBJECT_NAME'] == full_object_name) &
                        (whitelist_df['OBJECT_TYPE'] == rule['OBJECT_TYPE']) &
                        (whitelist_df['RULE_ID'] == 'MISSING_TAG_VALUE') &
                        (whitelist_df['TAG_NAME'] == required_tag_full)
                    ]
                    is_whitelisted = not whitelisted.empty
                
                obj_compliance['violations'].append({
                    'tag_name': required_tag_full,  # Keep full name for display
                    'rule_description': f"Compulsory tag '{required_tag_full}' missing on {rule['OBJECT_TYPE']}",
                    'is_whitelisted': is_whitelisted,
                    'applied_tag_rule_id': rule.get('APPLIED_TAG_RULE_ID')
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
