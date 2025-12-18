# Autopilot Rule Priority Issues & Solutions

## Current Issues

### 1. ❌ UI Doesn't Support Rule Reordering
**Problem:** Users can create/edit/delete rules but cannot change their priority order
**Impact:** New rules are always added at the bottom (lowest priority)

### 2. ❌ LLM Doesn't Reliably Follow ALL Rules
**Problem:** The agent instruction says "Process this email according to the rules below" which is vague
**Impact:** LLM may stop at first matching rule instead of evaluating all rules

---

## Solutions Implemented

### ✅ Temporary Fix: Manual JSON Reordering
Created `reorder_rules.py` script that allows manual rule reordering by editing `autopilot_state.json`

```bash
# Usage example:
python reorder_rules.py
```

The script moves rules by their ID to desired positions.

---

## Recommended Permanent Solutions

### Solution 1: Add UI Rule Reordering (Recommended)

**Option A: Drag & Drop Interface**
```python
# In Streamlit UI, use st-aggrid or streamlit-sortables
import streamlit as st
from streamlit_sortables import sort_items

# Display rules as sortable list
sorted_rules = sort_items(
    items=[{r['name']: r} for r in autopilot_rules],
    key='rule_sorter'
)

# Save reordered rules back to autopilot_state.json
```

**Option B: Priority Number Field**
- Add a `priority` field to each rule (1 = highest)
- Display input number next to each rule
- Sort rules by priority before passing to LLM

### Solution 2: Improve LLM Instruction (Critical)

**Current Instruction:**
```python
agent_instruction = f"""
AUTOPILOT MODE - Process this email according to the rules below.

RULES:
{rules_context}
"""
```

**Improved Instruction:**
```python
agent_instruction = f"""
AUTOPILOT MODE - Process this email by evaluating ALL rules below.

RULES (in PRIORITY order - highest priority first):
{rules_context}

**CRITICAL RULE MATCHING:**
- Rules are listed in PRIORITY ORDER (top = highest priority)
- Evaluate ALL rules above to find which ones apply to this email
- Apply the FIRST (highest priority) matching rule
- If multiple rules match, always use the one that appears FIRST in the list

EMAIL DETAILS:
...
"""
```

**Location to Edit:** `autopilot.py`, line ~484-489

---

## Implementation Plan

### Phase 1: Quick Fix (Manual)
1. ✅ Use `reorder_rules.py` to manually set rule order
2. ⏳ Update agent instruction (edit audit `autopilot.py` line 484)

### Phase 2: UI Enhancement (Proper Solution)
1. Add drag-drop rule reordering in Streamlit UI
2. OR add priority number input field
3. Update UI to show rule priority visually (1, 2, 3...)
4. Save rule order to `autopilot_state.json`

### Phase 3: Testing
1. Create test rules with different priorities
2. Send test emails matching multiple rules
3. Verify highest-priority rule is applied

---

## Quick Code Patch for Agent Instruction

**File:** `autopilot.py`  
**Line:** ~484-489

**Find:**
```python
    AUTOPILOT MODE - Process this email according to the rules below.
    
    {hands_free_instruction}
    
    RULES:
    {rules_context}
```

**Replace with:**
```python
    AUTOPILOT MODE - Process this email by evaluating ALL rules below.
    
    {hands_free_instruction}
    
    RULES (in PRIORITY order - highest priority first):
    {rules_context}
    
    **CRITICAL RULE MATCHING:**
    - Rules are listed in PRIORITY ORDER (top = highest priority)
    - Evaluate ALL rules above to find which ones apply to this email
    - Apply the FIRST (highest priority) matching rule
    - If multiple rules match, always use the one that appears FIRST in the list
```

---

## Why This Matters

**Example Scenario:**
- Rule #1: "Vacation auto-response for @cyfuture.com emails"
- Rule #5: "Reply to all sales inquiries"

If an internal sales inquiry comes in:
- ❌ **Without priority:** LLM might pick rule #5 (more general)
- ✅ **With priority:** LLM picks rule #1 (higher priority, more specific)

**The fix ensures:**
1. ALL rules are considered
2. Priority order is respected
3. Most specific/important rule wins
