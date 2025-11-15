"""
Compliance checking module
Handles warehouse compliance validation against applied rules
"""

import pandas as pd


def check_compliance(warehouse_df, applied_rules_df):
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
            param = rule['WAREHOUSE_PARAMETER']
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
            is_compliant = True
            if operator == 'MAX' and wh_value is not None and wh_value > threshold:
                is_compliant = False
            elif operator == 'MIN' and wh_value is not None and wh_value < threshold:
                is_compliant = False
            elif operator == 'EQUALS' and wh_value != threshold:
                is_compliant = False
            
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


def generate_fix_sql(warehouse_name, parameter, threshold_value):
    """Generate SQL to fix a non-compliant warehouse"""
    if parameter == 'AUTO_SUSPEND':
        return f"ALTER WAREHOUSE {warehouse_name}\nSET AUTO_SUSPEND = {int(threshold_value)};"
    elif parameter == 'STATEMENT_TIMEOUT_IN_SECONDS':
        return f"ALTER WAREHOUSE {warehouse_name}\nSET STATEMENT_TIMEOUT_IN_SECONDS = {int(threshold_value)};"
    else:
        return f"-- No SQL available for parameter: {parameter}"

def generate_post_fix_update_sql(warehouse_name, parameter, threshold_value):
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
            
            param = rule['WAREHOUSE_PARAMETER']
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
            is_compliant = True
            if operator == 'MAX' and obj_value is not None and obj_value > threshold:
                is_compliant = False
            elif operator == 'MIN' and obj_value is not None and obj_value < threshold:
                is_compliant = False
            elif operator == 'EQUALS' and obj_value != threshold:
                is_compliant = False
            
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
