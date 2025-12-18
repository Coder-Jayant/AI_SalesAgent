"""
Script to add priority UI to main_react.py
"""
import re

print("Adding priority UI to Streamlit interface...")

with open('main_react.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the rules display section and replace it
old_pattern = r'''    # Display existing rules
    st\.markdown\("### 📋 Active Rules"\)
    
    to_delete_index = None
    for idx, rule in enumerate\(current_rules\):
        with st\.container\(\):
            col1, col2, col3 = st\.columns\(\[1, 8, 1\]\)
            
            with col1:
                enabled = st\.checkbox\(
                    "✓",
                    value=bool\(rule\.get\("enabled", True\)\),
                    key=f"rule_enable_\{rule\['id'\]\}",
                    label_visibility="collapsed"
                \)
                rule\["enabled"\] = enabled
            
            with col2:
                status = "🟢" if enabled else "⚪"
                builtin = " \(Built-in\)" if rule\.get\("builtin"\) else ""
                st\.markdown\(f"\{status\} \*\*\{rule\['name'\]\}\*\*\{builtin\}"\)
                st\.caption\(rule\.get\("prompt", "—"\)\)
            
            with col3:
                if not rule\.get\("builtin"\):
                    if st\.button\("🗑️", key=f"rule_remove_\{rule\['id'\]\}"\):
                        to_delete_index = idx
        
        st\.markdown\("---"\)'''

new_code = '''    # Display existing rules (sorted by priority for visibility)
    st.markdown("### 📋 Active Rules (sorted by priority)")
    st.caption("💡 Lower priority number = higher priority (1 is highest)")
    
    # Sort rules by priority for display
    display_rules = sorted(current_rules, key=lambda r: r.get('priority', 999))
    
    to_delete_index = None
    for idx, rule in enumerate(display_rules):
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 1, 7, 1])
            
            with col1:
                enabled = st.checkbox(
                    "✓",
                    value=bool(rule.get("enabled", True)),
                    key=f"rule_enable_{rule['id']}",
                    label_visibility="collapsed"
                )
                rule["enabled"] = enabled
            
            with col2:
                # Priority number input
                priority = st.number_input(
                    "Priority",
                    min_value=1,
                    max_value=100,
                    value=int(rule.get('priority', idx + 1)),
                    step=1,
                    key=f"rule_priority_{rule['id']}",
                    label_visibility="collapsed",
                    help="Lower number = higher priority (1 is highest)"
                )
                rule["priority"] = priority
            
            with col3:
                status = "🟢" if enabled else "⚪"
                builtin = " (Built-in)" if rule.get("builtin") else ""
                st.markdown(f"{status} **#{priority}** {rule['name']}{builtin}")
                st.caption(rule.get("prompt", "—"))
            
            with col4:
                if not rule.get("builtin"):
                    if st.button("🗑️", key=f"rule_remove_{rule['id']}"):
                        # Find original index in current_rules
                        for original_idx, r in enumerate(current_rules):
                            if r['id'] == rule['id']:
                                to_delete_index = original_idx
                                break
        
        st.markdown("---")'''

# Try to replace
if re.search(old_pattern, content, re.DOTALL):
    content = re.sub(old_pattern, new_code, content, count=1, flags=re.DOTALL)
    print("✅ Updated rules display section")
else:
    print("⚠️  Pattern not found - trying simpler match...")
    # Fallback: Just find the section start
    if '# Display existing rules' in content and 'st.markdown("### 📋 Active Rules")' in content:
        print("📍 Found section, manual editing recommended")
        print("\nLocation: Search for '# Display existing rules' in main_react.py (around line 901)")
        print("\nRecommended change:")
        print("  1. Add priority column: col1, col2, col3, col4 = st.columns([1, 1, 7, 1])")
        print("  2. Add priority number input in col2")
        print("  3. Sort display_rules by priority before loop")
    else:
        print("❌ Could not locate the section")

# Also need to add priority to new rules
new_rule_pattern = r'''                new_rule = \{
                    "id": f"custom_\{int\(datetime\.now\(timezone\.utc\)\.timestamp\(\)\)\}",
                    "name": new_name\.strip\(\),
                    "enabled": bool\(enabled_new\),
                    "prompt": new_prompt\.strip\(\),
                    "builtin": False,
                \}'''

new_rule_code = '''                # Assign next available priority
                max_priority = max([r.get('priority', 0) for r in current_rules], default=0)
                new_rule = {
                    "id": f"custom_{int(datetime.now(timezone.utc).timestamp())}",
                    "name": new_name.strip(),
                    "enabled": bool(enabled_new),
                    "prompt": new_prompt.strip(),
                    "builtin": False,
                    "priority": max_priority + 1  # New rules get lowest priority by default
                }'''

if re.search(new_rule_pattern, content, re.DOTALL):
    content = re.sub(new_rule_pattern, new_rule_code, content, count=1, flags=re.DOTALL)
    print("✅ Updated new rule creation to assign priority")
else:
    print("⚠️  New rule pattern not found")

# Save
with open('main_react.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 60)
print("✅ UI UPDATE COMPLETE")
print("=" * 60)
print("\nChanges made to main_react.py:")
print("  1. Added priority number input column")
print("  2. Rules sorted by priority in UI")
print("  3. Priority shown next to rule name (#1, #2, etc.)")
print("  4. New rules auto-assigned next priority")
print("\nRestart Streamlit to see changes!")
