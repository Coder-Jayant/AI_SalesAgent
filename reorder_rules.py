import json

# Load the autopilot state
with open('autopilot_state.json', 'r', encoding='utf-8') as f:
    state = json.load(f)

# Find the vacation rule
vacation_rule = None
other_rules = []

for rule in state['autopilot_rules']:
    if rule['id'] == 'custom_1765430156':  # Vacation/Auto response rule
        vacation_rule = rule
    else:
        other_rules.append(rule)

# Reorder: Put vacation rule first
if vacation_rule:
    state['autopilot_rules'] = [vacation_rule] + other_rules
    print(f"✅ Moved '{vacation_rule['name']}' rule to first position")
    print(f"Total rules: {len(state['autopilot_rules'])}")
    
    # Save back
    with open('autopilot_state.json', 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    print("✅ Autopilot rules reordered successfully!")
    print("\nNew rule order:")
    for i, rule in enumerate(state['autopilot_rules'], 1):
        status = "✓" if rule['enabled'] else "✗"
        print(f"  {i}. [{status}] {rule['name']}")
else:
    print("❌ Vacation rule not found!")
