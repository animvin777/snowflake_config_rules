# Quick Guide: Adding New Configuration Rules

This guide shows how to extend the Snowflake Config Rules app with custom rules.

## Example: Adding a "Min Auto Suspend" Rule

### Step 1: Insert the Rule Definition

```sql
USE APPLICATION snowflake_config_rules_app;

INSERT INTO data_schema.config_rules (
    rule_id, 
    rule_name, 
    rule_description, 
    warehouse_parameter, 
    comparison_operator, 
    unit
)
VALUES (
    'MIN_AUTO_SUSPEND',
    'Min Auto Suspend in Seconds',
    'Minimum required auto suspend time to prevent rapid cycling',
    'AUTO_SUSPEND',
    'MIN',
    'seconds'
);
```

### Step 2: No Code Changes Needed! 

If the parameter is already monitored (like `AUTO_SUSPEND` or `STATEMENT_TIMEOUT_IN_SECONDS`), the Streamlit app will automatically:
- Show the new rule in the Rule Configuration tab
- Check compliance when the rule is applied
- Generate appropriate SQL to fix violations

The app will work immediately without code modifications!

## Example: Adding a "Max Warehouse Size" Rule

For parameters that need special handling (not directly captured from SHOW WAREHOUSES):

### Step 1: Insert the Rule Definition

```sql
INSERT INTO data_schema.config_rules (
    rule_id, 
    rule_name, 
    rule_description, 
    warehouse_parameter, 
    comparison_operator, 
    unit
)
VALUES (
    'MAX_WAREHOUSE_SIZE',
    'Max Warehouse Size',
    'Restrict warehouse sizes to control costs',
    'SIZE',
    'MAX',
    'size_level'
);
```

### Step 2: Update Streamlit App (if needed)

Since SIZE is already captured, no changes needed! The app handles it automatically.

## Example: Adding a Custom Parameter Rule

For truly custom parameters:

### Step 1: Ensure the Parameter is Captured

Modify `setup_script.sql` to capture the parameter in `warehouse_details` table if not already captured.

### Step 2: Insert the Rule Definition

```sql
INSERT INTO data_schema.config_rules (
    rule_id, 
    rule_name, 
    rule_description, 
    warehouse_parameter, 
    comparison_operator, 
    unit
)
VALUES (
    'REQUIRE_AUTO_RESUME',
    'Require Auto Resume',
    'Ensures all warehouses have auto-resume enabled',
    'AUTO_RESUME',
    'EQUALS',
    'boolean'
);
```

### Step 3: Update Streamlit App

Edit `app/streamlit/app.py` in the `check_compliance()` function:

```python
# Add this section for the new parameter
elif param == 'AUTO_RESUME':
    wh_value = wh['AUTO_RESUME']  # Assuming you've captured this
```

And in the `generate_fix_sql()` function:

```python
elif parameter == 'AUTO_RESUME':
    return f"ALTER WAREHOUSE {warehouse_name}\nSET AUTO_RESUME = {threshold_value};"
```

## Supported Comparison Operators

- **MAX**: Warehouse value must be ≤ threshold
  - Example: Max auto-suspend = 300 → warehouse auto-suspend must be 300 or less
  
- **MIN**: Warehouse value must be ≥ threshold
  - Example: Min auto-suspend = 60 → warehouse auto-suspend must be 60 or more
  
- **EQUALS**: Warehouse value must exactly match threshold
  - Example: Auto-resume = true → warehouse auto-resume must be true

## Rule Definition Fields

| Field | Description | Example |
|-------|-------------|---------|
| `rule_id` | Unique identifier (uppercase, underscores) | `MAX_AUTO_SUSPEND` |
| `rule_name` | Display name shown in UI | `Max Auto Suspend in Seconds` |
| `rule_description` | Explanation of the rule's purpose | `Maximum allowed auto suspend time...` |
| `warehouse_parameter` | Warehouse parameter to check | `AUTO_SUSPEND` |
| `comparison_operator` | How to compare: MAX, MIN, or EQUALS | `MAX` |
| `unit` | Display unit for the threshold | `seconds` |

## Parameters Already Captured

These parameters are already available and can be used immediately:

- `AUTO_SUSPEND` (from SHOW WAREHOUSES)
- `STATEMENT_TIMEOUT_IN_SECONDS` (requires optional parameter monitoring task)
- `SIZE` (from SHOW WAREHOUSES)
- `TYPE` (from SHOW WAREHOUSES)
- `MIN_CLUSTER_COUNT` (from SHOW WAREHOUSES)
- `MAX_CLUSTER_COUNT` (from SHOW WAREHOUSES)
- `SCALING_POLICY` (from SHOW WAREHOUSES)

## Testing Your New Rule

1. Insert the rule definition
2. Open the Streamlit app
3. Go to Rule Configuration tab
4. Select your new rule from the dropdown
5. Set a threshold value
6. Click "Apply Rule"
7. Go to Compliance View tab to see violations
8. Click "Generate Fix SQL" to test SQL generation

## Best Practices

1. **Start Simple**: Use existing parameters before adding new ones
2. **Clear Naming**: Use descriptive rule names that explain the intent
3. **Meaningful Thresholds**: Choose realistic threshold values for testing
4. **Test Incrementally**: Test with one warehouse before rolling out
5. **Document Rules**: Update your internal docs with custom rule rationale

## Common Rule Ideas

### Cost Control
- Max auto-suspend time
- Min auto-suspend time
- Max warehouse size
- Require multi-cluster scaling for specific warehouses

### Performance
- Min statement timeout (prevent query truncation)
- Max concurrency level requirements

### Governance
- Require specific scaling policies
- Enforce naming conventions (via custom logic)
- Require resource monitors

## Getting Help

For complex custom rules that require significant code changes, consider:
1. Reviewing the existing `check_compliance()` function logic
2. Understanding how the SQL generation works
3. Testing thoroughly in a development environment
4. Documenting your custom rules for future maintainers
