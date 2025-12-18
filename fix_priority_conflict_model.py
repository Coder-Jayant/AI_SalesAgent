"""
Fix priority system to use 3 levels (1/2/3) for conflict resolution only
"""
import json

print("=" * 60)
print("FIXING PRIORITY SYSTEM - CONFLICT RESOLUTION MODEL")
print("=" * 60)

# Step 1: Update priority values to 1-3 scale
print("\n[1/2] Normalizing priority to 1-3 scale...")

with open('autopilot_state.json', 'r', encoding='utf-8') as f:
    state = json.load(f)

# Map current priorities to 1-3 scale
for rule in state['autopilot_rules']:
    current_priority = rule.get('priority', 2)
    
    # Normalize to 1, 2, or 3
    if current_priority <= 2:
        new_priority = 1  # Critical
    elif current_priority <= 4:
        new_priority = 2  # Medium
    else:
        new_priority = 3  # Low
    
    rule['priority'] = new_priority
    print(f"  {rule['name']}: Priority {current_priority} → {new_priority}")

# Save
with open('autopilot_state.json', 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2, ensure_ascii=False)

print("✅ All priorities normalized to 1-3")

# Step 2: Update autopilot instruction
print("\n[2/2] Updating agent instruction for conflict resolution...")

with open('autopilot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the instruction
old_instruction = '''AUTOPILOT MODE - Process this email by evaluating ALL rules below.
    
    {hands_free_instruction}
    
    RULES (sorted by PRIORITY - lower number = higher priority):
    {rules_context}
    
    **CRITICAL RULE MATCHING:**
    - Rules are sorted by PRIORITY (1 = highest, 2 = second, etc.)
    - Evaluate ALL rules above to determine which apply to this email
    - Apply the rule with the LOWEST priority number (highest priority)
    - If multiple rules match, use the one with lower priority number'''

new_instruction = '''AUTOPILOT MODE - Process this email by evaluating ALL rules below.
    
    {hands_free_instruction}
    
    RULES (with priority for conflict resolution):
    {rules_context}
    
    **CRITICAL RULE APPLICATION:**
    - Evaluate ALL rules above
    - Follow ALL rules that apply to this email
    - If rules contradict each other, use PRIORITY to decide:
      * Priority 1 (Critical) - Security, escalation, urgent matters
      * Priority 2 (Medium) - Standard operations, replies, acknowledgments  
      * Priority 3 (Low) - General guidelines, catch-all behaviors
    - In case of conflict, follow the rule with LOWER priority number (1 beats 2, 2 beats 3)
    - If no conflicts, apply ALL applicable rules together'''

if old_instruction in content:
    content = content.replace(old_instruction, new_instruction)
    print("✅ Agent instruction updated for conflict resolution model")
else:
    print("⚠️  Could not find exact instruction - manual edit needed")

# Save
with open('autopilot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 60)
print("✅ PRIORITY SYSTEM FIXED")
print("=" * 60)
print("\nChanges:")
print("  1. Priority levels limited to 1, 2, 3")
print("  2. ALL rules are followed (not just first match)")
print("  3. Priority only used to resolve contradictions")
print("\nPriority Meanings:")
print("  1 = Critical (security, escalation, urgent)")
print("  2 = Medium (standard replies, demos, RFPs)")
print("  3 = Low (general guidelines, catch-all)")
print("=" * 60)
