import re

# Read the file
with open('autopilot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the specific section
old_text = '''            # Use ReAct agent for intelligent multi-step processing
            agent_instruction = f"""
    AUTOPILOT MODE - Process this email according to the rules below.
    
    {hands_free_instruction}
    
    RULES:
    {rules_context}'''

new_text = '''            # Use ReAct agent for intelligent multi-step processing
            agent_instruction = f"""
    AUTOPILOT MODE - Process this email by evaluating ALL rules below.
    
    {hands_free_instruction}
    
    RULES (in PRIORITY order - highest priority first):
    {rules_context}
    
    **CRITICAL RULE MATCHING:**
    - Rules are listed in PRIORITY ORDER (top = highest priority)
    - Evaluate ALL rules above to find which ones apply to this email  
    - Apply the FIRST (highest priority) matching rule
    - If multiple rules match, always use the one that appears FIRST in the list'''

if old_text in content:
    content = content.replace(old_text, new_text)
    
    with open('autopilot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Updated autopilot instruction to enforce priority-based rule matching!")
    print("\nChanges made:")
    print("  - Explicit instruction to evaluate ALL rules")
    print("  - Priority order enforcement (first = highest)")
    print("  - Clear matching logic: apply first matching rule")
else:
    print("❌ Could not find exact text pattern to replace")
    print("Manual editing may be required")
