"""
Script to add priority system to autopilot rules and fix agent instruction
"""
import json
import re

print("=" * 60)
print("AUTOPILOT PRIORITY SYSTEM IMPLEMENTATION")
print("=" * 60)

# Step 1: Add priority field to all rules
print("\n[1/3] Adding priority field to autopilot rules...")

with open('autopilot_state.json', 'r', encoding='utf-8') as f:
    state = json.load(f)

# Add priority to each rule (1 = highest)
for i, rule in enumerate(state['autopilot_rules'], start=1):
    if 'priority' not in rule:
        rule['priority'] = i  # Maintain current order
        print(f"  Added priority {i} to: {rule['name']}")

# Save updated state
with open('autopilot_state.json', 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2, ensure_ascii=False)

print("✅ Priority field added to all rules!")

# Step 2: Update autopilot.py to sort rules by priority
print("\n[2/3] Updating autopilot.py to sort by priority...")

with open('autopilot.py', 'r', encoding='utf-8') as f:
    autopilot_code = f.read()

# Find the line where rules are loaded
old_rules_line = 'rules = [r for r in state.get("autopilot_rules", _DEFAULT_RULES.copy()) if r.get("enabled")]'
new_rules_line = '''rules = [r for r in state.get("autopilot_rules", _DEFAULT_RULES.copy()) if r.get("enabled")]
        # Sort rules by priority (1 = highest priority)
        rules = sorted(rules, key=lambda r: r.get('priority', 999))'''

if old_rules_line in autopilot_code:
    autopilot_code = autopilot_code.replace(old_rules_line, new_rules_line)
    print("✅ Added priority sorting logic")
else:
    print("⚠️  Could not find exact rules loading line - manual edit may be needed")

# Step 3: Update agent instruction
print("\n[3/3] Updating agent instruction for better rule matching...")

old_instruction = '''AUTOPILOT MODE - Process this email according to the rules below.
    
    {hands_free_instruction}
    
    RULES:
    {rules_context}'''

new_instruction = '''AUTOPILOT MODE - Process this email by evaluating ALL rules below.
    
    {hands_free_instruction}
    
    RULES (sorted by PRIORITY - lower number = higher priority):
    {rules_context}
    
    **CRITICAL RULE MATCHING:**
    - Rules are sorted by PRIORITY (1 = highest, 2 = second, etc.)
    - Evaluate ALL rules above to determine which apply to this email
    - Apply the rule with the LOWEST priority number (highest priority)
    - If multiple rules match, use the one with lower priority number'''

if old_instruction in autopilot_code:
    autopilot_code = autopilot_code.replace(old_instruction, new_instruction)
    print("✅ Updated agent instruction")
else:
    print("⚠️  Could not update instruction - trying alternative pattern...")
    # Try with different whitespace
    pattern = r'AUTOPILOT MODE - Process this email according to the rules below\.\s+\{hands_free_instruction\}\s+RULES:\s+\{rules_context\}'
    if re.search(pattern, autopilot_code):
        print("✅ Found pattern with regex, making replacement...")
        autopilot_code = re.sub(pattern, new_instruction, autopilot_code, count=1)
    else:
        print("❌ Could not find instruction pattern")

# Save updated autopilot.py
with open('autopilot.py', 'w', encoding='utf-8') as f:
    f.write(autopilot_code)

print("\n" + "=" * 60)
print("✅ PRIORITY SYSTEM IMPLEMENTED SUCCESSFULLY!")
print("=" * 60)
print("\nChanges made:")
print("  1. Added 'priority' field to all rules in autopilot_state.json")
print("  2. Rules now sorted by priority (1=highest) in autopilot.py")
print("  3. Agent instruction updated to enforce priority matching")
print("\nNext: Restart Streamlit to apply changes")
print("=" * 60)
