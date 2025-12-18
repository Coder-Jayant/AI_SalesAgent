"""
react_agent.py
ReAct (Reasoning + Acting) Agent Implementation with Streaming Support
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List, Callable, Generator
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReActStep:
    """Represents one step in the ReAct loop"""
    step_type: str  # "thought", "action", "observation", "final_answer"
    content: str
    timestamp: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[str] = None


class ReActAgent:
    """
    ReAct Agent that explicitly shows Thought → Action → Observation → repeat
    Supports real-time streaming of thoughts and actions.
    """
    
    def __init__(self, llm, tools: List, system_prompt: str = ""):
        """
        Initialize ReAct agent.
        
        Args:
            llm: Language model instance
            tools: List of LangChain @tool decorated functions
            system_prompt: System-level instructions
        """
        self.llm = llm
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}
        self.system_prompt = system_prompt
        
        # ReAct prompt template - VERY STRICT FORMAT
        self.react_prompt_template = """You are a helpful AI Sales Assistant using the ReAct (Reasoning + Acting) framework.

You have access to the following tools:
{tool_descriptions}

CRITICAL: You MUST follow this EXACT format. Do NOT write conversational text. Do NOT describe what you "would" do.

**REQUIRED FORMAT:**

Thought: [Your reasoning - one concise sentence]
Action: [EXACT tool name from the list above]
Action Input: {{"arg1": "value1", "arg2": "value2"}}

STOP HERE! The system will execute the tool and provide the Observation. DO NOT continue writing!

**STRICT RULES:**
1. ALWAYS start with "Thought:" then your reasoning
2. ALWAYS use EXACT tool names from the list  
3. Action Input MUST be valid JSON - use lowercase true/false/null (NOT True/False/None)
4. STOP after Action Input - do NOT write "Observation:"
5. The system will execute the tool and add the real Observation
6. Do NOT write "I will" or "I would" - JUST DO IT
7. When task is complete, write "Final Answer:" immediately
8. **NEVER repeat actions** - check history below before acting
9. If you see "[END_TASK]" in Observation, provide Final Answer NOW
10. Maximum 3-4 actions per task, then conclude



**YOUR TURN:**

Question: {input}

**Previous actions (DO NOT REPEAT):**
{agent_scratchpad}

Continue (or Final Answer if done):
"""

    def _format_tool_descriptions(self) -> str:
        """Format tool names and descriptions"""
        descriptions = []
        for tool in self.tools:
            desc = f"- {tool.name}: {tool.description or 'No description'}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _parse_react_output(self, text: str) -> Dict[str, Any]:
        """
        Parse LLM output to extract Thought, Action, Action Input, or Final Answer.
        
        Returns:
            Dict with 'type' and relevant fields
        """
        logger.debug(f"[ReAct] Parsing output: {text[:200]}")
        
        # Check for Final Answer first
        final_match = re.search(r'Final Answer:\s*(.+)', text, re.DOTALL | re.IGNORECASE)
        if final_match:
            return {
                'type': 'final_answer',
                'content': final_match.group(1).strip()
            }
        
        # Extract Thought
        thought_match = re.search(r'Thought:\s*([^\n]+)', text, re.IGNORECASE)
        thought = thought_match.group(1).strip() if thought_match else ""
        
        # Extract Action
        action_match = re.search(r'Action:\s*([^\n]+)', text, re.IGNORECASE)
        action = action_match.group(1).strip() if action_match else None
        
        # Clean up action name
        if action:
            action = action.strip('`\'"')
            # Strip function call syntax - extract only tool name before '('
            # LLM sometimes outputs: query_knowledge_base({"query": "..."})
            # We need just: query_knowledge_base
            if '(' in action:
                action = action.split('(')[0].strip()
                logger.debug(f"[ReAct] Cleaned action name (removed function call syntax): {action}")
        
        # Extract Action Input
        action_input = None
        if action:
            # Try to match JSON more robustly - handle multiline and nested braces
            input_match = re.search(r'Action Input:\s*(\{.*?\}\s*$)', text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            
            if not input_match:
                # Fallback to simpler pattern
                input_match = re.search(r'Action Input:\s*(\{[^}]+\})', text, re.IGNORECASE)
            
            if input_match:
                json_str = input_match.group(1).strip()
                try:
                    action_input = json.loads(json_str)
                    logger.debug(f"[ReAct] Parsed action input: {action_input}")
                except json.JSONDecodeError as e:
                    logger.warning(f"[ReAct] Failed to parse JSON: {json_str} - {e}")
                    # Try to clean up the JSON string
                    try:
                        # Convert Python-style booleans/None to JSON format
                        cleaned = json_str
                        cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
                        cleaned = re.sub(r'\bFalse\b', 'false', cleaned)
                        cleaned = re.sub(r'\bNone\b', 'null', cleaned)
                        # Remove control characters
                        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned)
                        action_input = json.loads(cleaned)
                        logger.info(f"[ReAct] Parsed action input after cleaning: {action_input}")
                    except Exception as clean_error:
                        logger.warning(f"[ReAct] Could not parse even after cleaning: {clean_error}, using empty dict")
                        action_input = {}
            else:
                logger.warning(f"[ReAct] No Action Input for: {action}")
                action_input = {}
        
        if action:
            logger.info(f"[ReAct] Extracted - Thought: {thought[:50]}, Action: {action}, Input: {action_input}")
            return {
                'type': 'action',
                'thought': thought,
                'action': action,
                'action_input': action_input
            }
        elif thought:
            return {
                'type': 'thought',
                'thought': thought
            }
        else:
            logger.warning(f"[ReAct] Could not parse: {text[:200]}")
            return {
                'type': 'unknown',
                'content': text
            }
    
    def _clean_email_data(self, data: Any) -> Any:
        """
        Clean email data by removing only HTML/CSS bloat (body_html).
        Keeps ALL other fields intact - no truncation.
        """
        if not isinstance(data, (dict, list)):
            return data
        
        # Handle list of emails
        if isinstance(data, list):
            return [self._clean_email_data(item) for item in data]
        
        # Handle dict structures
        if isinstance(data, dict):
            cleaned = {}
            
            for key, value in data.items():
                # Skip body_html entirely (HTML/CSS bloat)
                if key == 'body_html':
                    continue
                
                # Recursively clean nested structures
                if isinstance(value, dict):
                    cleaned[key] = self._clean_email_data(value)
                elif isinstance(value, list):
                    cleaned[key] = self._clean_email_data(value)
                else:
                    cleaned[key] = value
            
            return cleaned
        
        return data
    
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool and return cleaned observation"""
        try:
            if tool_name not in self.tool_map:
                available = ", ".join(self.tool_map.keys())
                return f"Error: Tool '{tool_name}' not found. Available tools: {available[:200]}..."
            
            tool = self.tool_map[tool_name]
            
            # Execute tool
            logger.info(f"[ReAct] Executing tool: {tool_name} with input: {tool_input}")
            result = tool.invoke(tool_input)
            
            # Convert result to appropriate format
            if isinstance(result, dict) or isinstance(result, list):
                result_data = result
            else:
                result_str = str(result)
                try:
                    result_data = json.loads(result_str)
                except:
                    # Not JSON, return as string
                    return result_str
            
            # Clean email data if this is an email tool
            email_tools = {'search_and_fetch_emails', 'batch_fetch_emails', 'fetch_email', 'list_unread', 'dynamic_mail_fetch_tool'}
            if tool_name in email_tools:
                result_data = self._clean_email_data(result_data)
                logger.info(f"[ReAct] Cleaned email data for {tool_name}")
            
            # Convert back to JSON string
            result_str = json.dumps(result_data, default=str, indent=2)
            return result_str
            
        except Exception as e:
            logger.exception(f"[ReAct] Tool execution failed: {tool_name}")
            return f"Error executing tool '{tool_name}': {str(e)}"
    
    
    def run_streaming(
        self, 
        user_input: str, 
        max_iterations: int = 50,
        callback: Optional[Callable[[ReActStep], None]] = None,
        conversation_history: Optional[List] = None
    ) -> Generator[ReActStep, None, str]:
        """
        Run ReAct loop with streaming support and conversation history.
        Yields ReActStep objects in real-time.
        
        Args:
            user_input: User's question/request
            max_iterations: Maximum number of thought-action cycles
            callback: Optional callback function called for each step
            conversation_history: Optional list of previous messages for context
            
        Yields:
            ReActStep objects as they occur
            
        Returns:
            Final answer string
        """
        # Build initial prompt
        tool_descriptions = self._format_tool_descriptions()
        agent_scratchpad = ""
        
        # Build conversation context from history
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\n**Previous Conversation:**\n"
            for msg in conversation_history[-6:]:  # Last 6 messages (3 turns) for context
                if hasattr(msg, 'content'):
                    role = "User" if msg.__class__.__name__ == "HumanMessage" else "Assistant"
                    # Truncate long messages in history to save tokens
                    content = msg.content[:800] + "..." if len(msg.content) > 800 else msg.content
                    conversation_context += f"\n{role}: {content}\n"
            conversation_context += "\n**Current Question:**\n"
        
        # Add current time context for temporal awareness
        from datetime import datetime
        from zoneinfo import ZoneInfo
        current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
        time_context = f"**CURRENT TIME:** {current_time.strftime('%A, %B %d, %Y at %I:%M %p %Z')}\n\n"
        
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Build prompt with conversation context
            prompt = self.react_prompt_template.format(
                tool_descriptions=tool_descriptions,
                input=user_input,
                agent_scratchpad=agent_scratchpad
            )
            
            # Prepend conversation context if available
            if conversation_context:
                prompt = conversation_context + prompt
            
            # Add system prompt with time context
            if self.system_prompt:
                full_prompt = f"{self.system_prompt}\n\n{time_context}{prompt}"
            else:
                full_prompt = time_context + prompt
            
            # Get LLM response with STOP SEQUENCE to prevent hallucination
            try:
                from langchain_core.messages import HumanMessage
                
                # CRITICAL: Stop before LLM can generate fake Observations
                response = self.llm.invoke(
                    [HumanMessage(content=full_prompt)],
                    stop=["Observation:", "\nObservation"]
                )
                llm_output = response.content.strip()
                logger.debug(f"[ReAct] LLM output: {llm_output[:200]}")
            except Exception as e:
                logger.exception("[ReAct] LLM invocation failed")
                
                # Check if it's a context length error
                error_str = str(e)
                is_context_error = (
                    "maximum context length" in error_str.lower() 
                    or "tokens" in error_str.lower() 
                    or "context" in error_str.lower()
                )
                
                error_content = f"LLM error: {str(e)}"
                if is_context_error:
                    error_content = (
                        "⚠️ **Context Length Exceeded!**\n\n"
                        f"The conversation has exceeded the maximum token limit.\n\n"
                        f"**Error:** {str(e)}\n\n"
                        "**Solution:** Please clear the chat history using the '🧹 Clear Chat' button in the sidebar and start a new conversation."
                    )
                
                error_step = ReActStep(
                    step_type="error",
                    content=error_content,
                    timestamp=datetime.now().isoformat()
                )
                if callback:
                    callback(error_step)
                yield error_step
                return error_content
            
            # Parse LLM output
            parsed = self._parse_react_output(llm_output)
            
            if parsed['type'] == 'final_answer':
                # Done!
                final_step = ReActStep(
                    step_type="final_answer",
                    content=parsed['content'],
                    timestamp=datetime.now().isoformat()
                )
                if callback:
                    callback(final_step)
                yield final_step
                return parsed['content']
            
            elif parsed['type'] == 'action':
                # Yield thought
                if parsed['thought']:
                    thought_step = ReActStep(
                        step_type="thought",
                        content=parsed['thought'],
                        timestamp=datetime.now().isoformat()
                    )
                    if callback:
                        callback(thought_step)
                    yield thought_step
                
                # Yield action
                action_step = ReActStep(
                    step_type="action",
                    content=f"{parsed['action']}",
                    timestamp=datetime.now().isoformat(),
                    tool_name=parsed['action'],
                    tool_input=parsed['action_input']
                )
                if callback:
                    callback(action_step)
                yield action_step
                
                # Execute tool
                observation = self._execute_tool(parsed['action'], parsed['action_input'])
                
                # Yield observation (FULL content for UI display and immediate LLM reasoning)
                obs_step = ReActStep(
                    step_type="observation",
                    content=observation,
                    timestamp=datetime.now().isoformat(),
                    tool_name=parsed['action'],
                    tool_output=observation
                )
                if callback:
                    callback(obs_step)
                yield obs_step
                
                # Update scratchpad with FULL observation (HTML already cleaned)
                agent_scratchpad += f"\nThought: {parsed['thought']}\n"
                agent_scratchpad += f"Action: {parsed['action']}\n"
                agent_scratchpad += f"Action Input: {json.dumps(parsed['action_input'])}\n"
                agent_scratchpad += f"Observation: {observation}\n"


                
                # Check if task is complete (END_TASK observed)
                if "[END_TASK]" in observation:
                    logger.info("[ReAct] END_TASK detected, forcing Final Answer")
                    # Force the agent to conclude on next iteration
                    agent_scratchpad += "\n[SYSTEM]: Task marked as complete. Provide Final Answer now.\n"
            
            elif parsed['type'] == 'thought':
                # Just a thought
                thought_step = ReActStep(
                    step_type="thought",
                    content=parsed['thought'],
                    timestamp=datetime.now().isoformat()
                )
                if callback:
                    callback(thought_step)
                yield thought_step
                
                agent_scratchpad += f"\nThought: {parsed['thought']}\n"
            
            else:
                # Unknown - log and continue
                logger.warning(f"[ReAct] Unknown parse result: {parsed}")
                agent_scratchpad += f"\n{llm_output}\n"
        
        # Max iterations reached
        timeout_step = ReActStep(
            step_type="final_answer",
            content=f"I've reached the maximum number of reasoning steps ({max_iterations}). Based on what I've accomplished, the task has been completed.",
            timestamp=datetime.now().isoformat()
        )
        if callback:
            callback(timeout_step)
        yield timeout_step
        
        return timeout_step.content
    
    def run(self, user_input: str, max_iterations: int = 50) -> str:
        """
        Run ReAct loop without streaming (simple version).
        Returns final answer.
        """
        steps = list(self.run_streaming(user_input, max_iterations))
        
        # Find the final answer
        for step in reversed(steps):
            if step.step_type == "final_answer":
                return step.content
        
        return "No answer generated."
