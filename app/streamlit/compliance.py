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
                    'unit': rule['UNIT']
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
