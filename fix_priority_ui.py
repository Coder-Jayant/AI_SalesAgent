"""
Update UI to limit priority to 1-3 and show conflict resolution labels
"""
import re

print("Updating UI for 3-level priority system...")

with open('main_react.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find priority number_input and update it
old_pattern = r'''priority = st\.number_input\(
                    "Priority",
                    min_value=1,
                    max_value=100,
                    value=int\(rule\.get\('priority', idx \+ 1\)\),
                    step=1,
                    key=f"rule_priority_\{rule\['id'\]\}",
                    label_visibility="collapsed",
                    help="Lower number = higher priority \(1 is highest\)"
                \)'''

new_code = '''priority = st.selectbox(
                    "Priority",
                    options=[1, 2, 3],
                    index=[1, 2, 3].index(int(rule.get('priority', 2))),
                    key=f"rule_priority_{rule['id']}",
                    format_func=lambda x: {1: "1-Critical", 2: "2-Medium", 3: "3-Low"}.get(x, str(x)),
                    label_visibility="collapsed",
                    help="1=Critical (urgent/security), 2=Medium (standard), 3=Low (general). Used only when rules conflict."
                )'''

if re.search(old_pattern, content, re.DOTALL):
    content = re.sub(old_pattern, new_code, content, count=1, flags=re.DOTALL)
    print("✅ Updated priority input to dropdown (1/2/3)")
else:
    print("⚠️  Could not find priority input pattern")

# Update the caption/help text
old_caption = 'st.caption("💡 Lower priority number = higher priority (1 is highest)")'
new_caption = 'st.caption("💡 Priority: 1=Critical, 2=Medium, 3=Low. Used only when rules contradict each other.")'

if old_caption in content:
    content = content.replace(old_caption, new_caption)
    print("✅ Updated help text")

# Save
with open('main_react.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ UI UPDATED")
print("  - Priority dropdown: 1-Critical, 2-Medium, 3-Low")
print("  - Help text clarifies conflict resolution usage")
