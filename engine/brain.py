import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from engine.actions import MavrickActions

load_dotenv(override=True)

class MavrickBrain:
    def __init__(self, user_name=None, summary=None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.user_name = user_name or os.getenv("USER_NAME", "Sir")
        summary_text = summary.strip() if isinstance(summary, str) else ""
        self.summary = summary_text
        self.memory = [
            {"role": "system", "content": f"You are Mavrick, a highly intelligent AI assistant (like JARVIS). You are helpful and witty. You have access to system tools. Use them to help the user with time, date, opening apps, searching the web, system stats, media control, reminders, and running complex protocols. Protocols are user-defined; call list_protocols to see available names. You can also switch your persona between Mavrick (default), Jarvis (polite/British), and Friday (efficient/sharp)."}
        ]
        if summary_text:
            self.memory.append({"role": "system", "content": f"Memory summary (previous session): {summary_text}"})
        self.total_cost = 0.0
        self.total_tokens = 0
        self.session_cost = 0.0
        
        # Load starting balance from .env (fallback to 0.0)
        try:
            self.current_balance = float(os.getenv("OPENAI_BALANCE", "0.0"))
        except (ValueError, TypeError):
            self.current_balance = 0.0
        
        self.debug_mode = os.getenv("DEBUG_MODE", "False") == "True"

    def log_debug(self, msg):
        if self.debug_mode:
            print(f" [DEBUG] [BRAIN]: {msg}")
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_system_info",
                    "description": "Get current time, date, or system stats (CPU, RAM, Battery)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "enum": ["time", "date", "stats"]}
                        },
                        "required": ["category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_application",
                    "description": "Open a system application",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string"}
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for a query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "initiate_protocol",
                    "description": "Launch a set of applications for a specific task protocol",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "protocol_name": {"type": "string"}
                        },
                        "required": ["protocol_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_protocols",
                    "description": "List available protocol names",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "schedule_reminder",
                    "description": "Schedule a reminder. 'when' supports 'in 10 minutes', 'HH:MM', or 'YYYY-MM-DD HH:MM'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "when": {"type": "string"}
                        },
                        "required": ["message", "when"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_reminders",
                    "description": "List upcoming reminders",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "cancel_reminder",
                    "description": "Cancel a reminder by id",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reminder_id": {"type": "string"}
                        },
                        "required": ["reminder_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "media_control",
                    "description": "Control system media playback and volume",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["volume up", "volume down", "mute", "play pause", "next", "previous"]}
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "switch_persona",
                    "description": "Change the assistant's persona, voice, and speaking style",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "persona": {"type": "string", "enum": ["mavrick", "jarvis", "friday"]}
                        },
                        "required": ["persona"]
                    }
                }
            }
        ]

    def get_response(self, user_input):
        if self.current_balance <= 0:
            return f"I apologize, {self.user_name}, but your OpenAI balance has reached zero. Please top up your account to continue our interaction."
            
        self.memory.append({"role": "user", "content": user_input})
        self.log_debug(f"Processing query through GPT-4o. Memory depth: {len(self.memory)}")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=self.memory,
                tools=self.tools,
                tool_choice="auto"
            )
            
            msg = response.choices[0].message
            
            if msg.tool_calls:
                self.log_debug(f"Logic sequence triggered. {len(msg.tool_calls)} tool calls requested.")
                # Add the assistant message with tool calls to memory ONCE
                self.memory.append(msg)
                
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    self.log_debug(f"TOOL EXECUTION: {func_name}({args})")
                    
                    if func_name == "get_system_info":
                        if args["category"] == "time": result = MavrickActions.get_time()
                        elif args["category"] == "date": result = MavrickActions.get_date()
                        else: result = MavrickActions.get_system_stats()
                    elif func_name == "open_application":
                        result = MavrickActions.open_app(args["app_name"])
                    elif func_name == "web_search":
                        result = MavrickActions.search_web(args["query"])
                    elif func_name == "initiate_protocol":
                        result = MavrickActions.run_protocol(args["protocol_name"])
                    elif func_name == "media_control":
                        result = MavrickActions.media_control(args["action"])
                    elif func_name == "switch_persona":
                        # We return a special string for main.py to handle the external voice change
                        result = f"SWITCHING_PERSONA_TO_{args['persona'].upper()}"
                    elif func_name == "list_protocols":
                        protocols = MavrickActions.list_protocols()
                        if protocols:
                            result = "Available protocols: " + ", ".join(protocols)
                        else:
                            result = "No protocols are available."
                    elif func_name == "schedule_reminder":
                        result = MavrickActions.schedule_reminder(args["message"], args["when"])
                    elif func_name == "list_reminders":
                        result = MavrickActions.list_reminders()
                    elif func_name == "cancel_reminder":
                        result = MavrickActions.cancel_reminder(args["reminder_id"])
                    
                    self.log_debug(f"TOOL RESULT: {result[:50]}...")
                    # Append each tool response
                    self.memory.append({"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": result})
                
                # Get final response after tool execution
                self.log_debug("Synthesizing final response from tool data...")
                second_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=self.memory
                )
                assistant_message = second_response.choices[0].message.content
                usage = second_response.usage
            else:
                self.log_debug("Direct response generated (No tool calls).")
                assistant_message = msg.content
                usage = response.usage

            if usage:
                self.log_debug(f"TOKEN USAGE: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")
                self.total_tokens += usage.total_tokens
                # GPT-4o pricing (approx): 
                # Input: $2.50 / 1M tokens
                # Output: $10.00 / 1M tokens
                input_cost = (usage.prompt_tokens / 1_000_000) * 2.50
                output_cost = (usage.completion_tokens / 1_000_000) * 10.00
                cost = input_cost + output_cost
                
                self.session_cost += cost
                self.current_balance -= cost
                
                # Prevent balance from going negative in display (if desired, though usually it just hits 0)
                if self.current_balance < 0:
                    self.current_balance = 0.0

            if not msg.tool_calls:
                # Only add if it wasn't already added (if no tool calls)
                self.memory.append({"role": "assistant", "content": assistant_message})
            else:
                # Add the final chat response as well
                self.memory.append({"role": "assistant", "content": assistant_message})

            # Safer memory cleanup: don't break assistant-tool-assistant chains crudely
            if len(self.memory) > 30: # Increased threshold for safety
                self.log_debug("Memory threshold reached. Optimizing conversation context...")
                # Always preserve the system prompt (index 0)
                system_prompt = self.memory[0]
                
                # We want to keep about 15 messages, but we MUST start with a 'user' message
                # to satisfy OpenAI's requirement that tool responses follow assistant calls.
                start_index = len(self.memory) - 15
                
                # Search forward from start_index to find the first 'user' message
                new_start = -1
                for i in range(start_index, len(self.memory)):
                    if self.memory[i].get("role") == "user":
                        new_start = i
                        break
                
                if new_start != -1:
                    self.memory = [system_prompt] + self.memory[new_start:]
                    self.log_debug(f"Context optimized. New memory depth: {len(self.memory)}")
                else:
                    # Fallback if no user message found in the last 15 (unlikely but safe)
                    self.memory = [system_prompt] + self.memory[-2:]
                    self.log_debug("Fallback context reset performed.")

            self.summary = self._build_summary()
                    
            return assistant_message
            
        except Exception as e:
            return f"I apologize, {self.user_name}, but I encountered an error: {str(e)}"

    def _build_summary(self):
        def _clean(text):
            return " ".join(str(text).split())

        recent_users = [_clean(m.get("content", "")) for m in self.memory if m.get("role") == "user"][-3:]
        recent_assistant = [_clean(m.get("content", "")) for m in self.memory if m.get("role") == "assistant"][-2:]
        parts = []
        if recent_users:
            parts.append("Recent user requests: " + " | ".join(recent_users))
        if recent_assistant:
            parts.append("Recent assistant replies: " + " | ".join(recent_assistant))
        summary = " / ".join(parts).strip()
        return summary[:800]

    def get_summary(self):
        return self.summary

if __name__ == "__main__":
    brain = MavrickBrain()
    print(brain.get_response("Mavrick, what's the time?"))
