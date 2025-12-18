# Complete Testing Prompts for Sales Agent

## 🧪 Test Categories

1. [Email Threading Tests](#email-threading-tests)
2. [Autopilot Rules Tests](#autopilot-rules-tests)
3. [Action Plans with Stopping Conditions](#action-plans-with-stopping-conditions)
4. [Chatbox Integration Tests](#chatbox-integration-tests)
5. [End-to-End Scenarios](#end-to-end-scenarios)

---

## 📧 Email Threading Tests

### Test 1: Draft Reply with Threading
**Prompt:**
```
Fetch the latest unread email and create a draft reply saying "Thank you for reaching out. I'll review your request and get back to you shortly."
```

**What to Check:**
- ✅ Draft appears in same thread as original
- ✅ Draft has "Re:" prefix
- ✅ Quoted original email appears below your reply
- ✅ From/Sent/Subject header visible in quoted content

---

### Test 2: Send Reply with Quoted Content
**Prompt:**
```
Reply to the email with subject containing "pricing" and say "Thanks for your interest! I'll send you our pricing details shortly."
```

**What to Check:**
- ✅ Reply sent successfully
- ✅ Original marked as read
- ✅ Check Sent Items - reply includes quoted original at bottom
- ✅ Reply threads correctly in email client

---

### Test 3: Reply with CC
**Prompt:**
```
Fetch the latest email from a customer and reply "We've received your request" with CC to jayant.verma@cyfuture.com
```

**What to Check:**
- ✅ Reply sent with CC preserved
- ✅ Threading headers intact
- ✅ Quoted original included

---

## 🤖 Autopilot Rules Tests

### Test 4: Create Autopilot Rule
**Prompt:**
```
Create an autopilot rule with priority 1 that says "For any email from potential customers asking about GPU servers, reply with information about our GPU cloud offerings and query the knowledge base for pricing details"
```

**What to Check:**
- ✅ Rule created with priority 1
- ✅ Rule appears in Autopilot tab
- ✅ Rule is enabled by default

---

### Test 5: List Autopilot Rules
**Prompt:**
```
Show me all autopilot rules sorted by priority
```

**What to Check:**
- ✅ All rules displayed
- ✅ Priority shown for each rule
- ✅ Enabled/disabled status visible

---

### Test 6: Update Autopilot Rule Priority
**Prompt:**
```
Change the priority of the "GPU servers" rule to priority 2
```

**What to Check:**
- ✅ Priority updated successfully
- ✅ UI reflects new priority

---

### Test 7: Delete Autopilot Rule
**Prompt:**
```
Delete the autopilot rule about GPU servers
```

**What to Check:**
- ✅ Rule deleted
- ✅ Cannot delete built-in rules
- ✅ Confirmation message shown

---

## 📅 Action Plans with Stopping Conditions

### Test 8: Create Action Plan with Execution Count Stop
**Prompt:**
```
Create an action plan that runs every 6 hours to check for unreplied VIP emails and send follow-ups. Stop after 5 executions.
```

**What to Check:**
- ✅ Plan created with custom 6-hour interval
- ✅ Stopping condition: "Stop after 5 executions"
- ✅ Plan shows in Action Plans tab

---

### Test 9: Create Action Plan with Date-Based Stop
**Prompt:**
```
Create a daily action plan at 9 AM to send a summary of new inquiries. Stop after December 31, 2024.
```

**What to Check:**
- ✅ Daily schedule at 09:00
- ✅ Stopping condition includes date
- ✅ Next execution time calculated

---

### Test 10: Create Action Plan with Email-Based Stop
**Prompt:**
```
Create an action plan that sends a follow-up every 2 hours to prospects who haven't replied. Stop when customer replies or requests to stop.
```

**What to Check:**
- ✅ Custom interval: 2 hours
- ✅ Stopping condition: "Stop when customer replies or requests to stop"
- ✅ Auto-delete flag can be set

---

### Test 11: List Action Plans
**Prompt:**
```
Show me all action plans with their stopping conditions
```

**What to Check:**
- ✅ All plans listed
- ✅ Stopping conditions displayed
- ✅ Execution count and last run shown

---

### Test 12: Update Action Plan Stopping Condition
**Prompt:**
```
Update the VIP follow-up plan to stop after 3 executions instead of 5
```

**What to Check:**
- ✅ Stopping condition updated
- ✅ Plan re-saved successfully

---

### Test 13: Delete Action Plan
**Prompt:**
```
Delete the action plan for daily summaries
```

**What to Check:**
- ✅ Plan deleted successfully
- ✅ Removed from Action Plans tab

---

## 💬 Chatbox Integration Tests

### Test 14: Create Rules AND Plans Together
**Prompt:**
```
Set up automation for new prospects: 
1. Create an autopilot rule to send intro emails when I receive inquiries about cloud hosting
2. Create an action plan to follow up every 12 hours if they don't reply
3. Stop the follow-ups after 5 attempts or when they reply
```

**What to Check:**
- ✅ Autopilot rule created
- ✅ Action plan created
- ✅ Stopping condition set correctly
- ✅ Both working together

---

### Test 15: Query Knowledge Base in Reply
**Prompt:**
```
Find the latest email about colocation pricing, query the knowledge base for our colo pricing, and draft a reply with the pricing information
```

**What to Check:**
- ✅ KB queried successfully
- ✅ Draft includes KB information
- ✅ Draft threads correctly
- ✅ Quoted original included

---

### Test 16: Web Search in Reply
**Prompt:**
```
Reply to the email asking about GPU comparison, search the web for "NVIDIA A100 vs H100 specs", and include the comparison in your reply
```

**What to Check:**
- ✅ Web search executed
- ✅ Reply includes search results
- ✅ Sources cited
- ✅ Threading preserved

---

## 🔄 End-to-End Scenarios

### Test 17: Complete Prospect Follow-up Flow
**Prompt:**
```
I want to automate follow-ups for prospects interested in GPU servers:
1. When someone emails about GPU servers, send them our GPU brochure
2. If they don't reply in 24 hours, send a follow-up every 8 hours
3. Stop after 4 follow-ups or when they reply
4. Make sure all emails thread correctly
```

**What to Check:**
- ✅ Autopilot rule created for GPU inquiries
- ✅ Action plan created with 8-hour interval
- ✅ Stopping condition: "4 follow-ups OR customer replies"
- ✅ All emails thread properly

---

### Test 18: Daily Summary Automation
**Prompt:**
```
Create a  daily action plan at 6 PM that:
1. Fetches all unread emails from today
2. Queries knowledge base for any relevant info
3. Sends me a summary email
4. Runs for 30 days then stops
```

**What to Check:**
- ✅ Daily schedule at 18:00
- ✅ Plan fetches unread emails
- ✅ KB queries in task
- ✅ Stopping condition: "30 days"

---

### Test 19: VIP Customer Handling
**Prompt:**
```
Set up VIP customer handling:
1. Autopilot rule: Any email from @bigcorp.com gets immediate personalized response
2. Action plan: Check for unreplied VIP emails every 2 hours
3. Stop checking after business hours (6 PM)
```

**What to Check:**
- ✅ Autopilot rule with domain filter
- ✅ Action plan with 2-hour interval
- ✅ Time-based stopping condition

---

### Test 20: Knowledge Base Management
**Prompt:**
```
Query the knowledge base for "datacenter locations" and send the top 3 results to test@example.com
```

**What to Check:**
- ✅ KB queried with top_k=3
- ✅ Results formatted nicely
- ✅ Email sent (not as reply - new email)

---

## 🐛 Edge Case Tests

### Test 21: Empty Stopping Condition
**Prompt:**
```
Create an hourly action plan to monitor server alerts. No stopping condition - run indefinitely.
```

**What to Check:**
- ✅ Plan created without stopping_condition field
- ✅ Runs continuously

---

### Test 22: Complex Stopping Condition
**Prompt:**
```
Create action plan: follow up every 6 hours. Stop if: customer replies OR 7 days pass OR 10 executions reached, whichever comes first.
```

**What to Check:**
- ✅ Complex condition stored as-is
- ✅ Agent can interpret "OR" logic
- ✅ Multiple conditions handled

---

### Test 23: Concurrent Plan Execution
**Prompt:**
```
Create two action plans both running every 5 minutes to test if lock mechanism prevents conflicts
```

**What to Check:**
- ✅ Lock prevents concurrent runs
- ✅ Plans execute sequentially
- ✅ No race conditions

---

## 📊 Monitoring & Validation Tests

### Test 24: Check Execution History
**Prompt:**
```
Show me the execution history for the VIP follow-up plan
```

**What to Check:**
- ✅ History displayed with timestamps
- ✅ Success/failure status shown
- ✅ Last 3 executions visible

---

### Test 25: Validate Threading in Email Client
**Steps:**
1. Send several replies using the agent
2. Open Gmail/Outlook
3. Check All Mail or Sent Items

**What to Check:**
- ✅ All replies group in same thread
- ✅ Quoted originals display correctly
- ✅ No broken HTML rendering

---

## 🎯 Priority Test Checklist

Run these in order for quickest validation:

### Quick Test (5 minutes)
- [ ] Test 2: Send reply with quoted content
- [ ] Test 8: Create action plan with stop condition
- [ ] Test 4: Create autopilot rule
- [ ] Test 25: Validate in email client

### Medium Test (15 minutes)
- [ ] Test 1: Draft reply
- [ ] Test 11: List action plans
- [ ] Test 5: List autopilot rules
- [ ] Test 14: Create rules + plans together
- [ ] Test 17: End-to-end prospect flow

### Full Test (30+ minutes)
- [ ] All 25 tests above
- [ ] Monitor autopilot service logs
- [ ] Monitor action plan service logs  
- [ ] Check for errors in Streamlit UI

---

## 🔍 What to Look For

### In Logs
```powershell
# Autopilot logs
tail -f autopilot_service.log | grep -E "threading|quoted|InReplyTo"

# Action plan logs
tail -f action_plan_service.log | grep -E "stopping_condition|execution_count"
```

### In UI
- **Autopilot Tab**: Rules with priorities
- **Action Plans Tab**: Plans with stopping conditions
- **Chat**: Agent mentions stopping conditions when creating plans

### In Email Client
- **Threading**: Replies grouped correctly
- **Quoted Content**: Original appears with From/Sent/Subject
- **Draft Headers**: InReplyTo and References visible (view source)

---

## ✅ Success Criteria

**Email Threading**: PASS if
- Drafts thread correctly (InReplyTo header set)
- Replies include quoted original
- HTML renders properly in Gmail + Outlook

**Autopilot**: PASS if
- Rules created with priority
- Rules trigger on matching emails
- Agent can list/update/delete rules

**Action Plans**: PASS if
- Plans created with stopping conditions
- Agent evaluates conditions correctly
- Plans auto-disable/delete when stopped
- Execution history tracks runs

**Integration**: PASS if
- Rules + plans work together
- No conflicts or race conditions
- All logging clear and helpful

---

## 🚨 If Tests Fail

1. **Check service logs** for errors
2. **Verify services running**: autopilot & action plan services
3. **Clear Python cache**: `Remove-Item -Recurse __pycache__, action_plans\__pycache__`
4. **Restart services**
5. **Check backup**: Restore from `.backup_threading` if needed

---

## 📝 Test Results Template

```
Test ID: ___
Test Name: ___
Status: ✅ PASS / ❌ FAIL
Notes: ___
Issues Found: ___
```

---

Ready to start testing! Begin with the **Quick Test** checklist above. 🚀
