# Priority System - Quick Reference Card

## 🎯 Core Principle

**ALL RULES ARE FOLLOWED** - Priority only used to resolve contradictions

---

## 📊 3 Priority Levels

| Level | Label | When to Use |
|-------|-------|-------------|
| **1** | **Critical** | Security, escalation, vacation, urgent |
| **2** | **Medium** | Sales, RFPs, demos, standard replies |
| **3** | **Low** | General guidelines, catch-all, spam |

---

## ⚙️ How It Works

```
Email arrives
    ↓
Evaluate ALL rules
    ↓
Do rules conflict?
    ├─ NO  → Apply ALL rules together ✅
    └─ YES → Use priority to decide (1 > 2 > 3) ✅
```

---

## 💡 Examples

### Example 1: NO Conflict
**Email:** "Send pricing and schedule demo"

**Rules Applied:**
- ✅ Pricing handler (Priority 2)
- ✅ Demo handler (Priority 2)

**Result:** Agent sends pricing AND schedules demo

---

### Example 2: WITH Conflict
**Email from @cyfuture.com:** "Need project update"

**Rules:**
1. Vacation response (Priority 1) - "Send out-of-office"
2. Sales inquiry (Priority 2) - "Respond with details"

**Conflict:** Can't do BOTH

**Result:** Priority 1 wins → Vacation response sent

---

## 🔧 Quick Setup

1. Go to **⚙️ Autopilot Rules** tab
2. For each rule, set priority:
   - **1-Critical** = Must override everything
   - **2-Medium** = Standard operations
   - **3-Low** = General fallback
3. Click **💾 Save**

---

## ✅ Best Practices

- Most rules should be **Priority 2**
- Reserve **Priority 1** for truly critical rules (vacation, security)
- Use **Priority 3** for catch-all rules
- Avoid creating conflicting rules when possible

---

## 🚀 What Changed

✅ Agent instruction: "Evaluate ALL rules, follow ALL unless conflict"  
✅ Priority limited to 3 levels (was unlimited)  
✅ UI shows dropdown: 1-Critical, 2-Medium, 3-Low  
✅ All existing rules normalized to 1/2/3  

---

**Last Updated:** 2025-12-11  
**Model:** Conflict Resolution (not first-match)
