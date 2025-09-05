"""
Strands Agent with Native MCP Integration
Properly implements MCP tool integration with Amazon Bedrock
"""

import os
import json
import logging
import asyncio
import importlib
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from pathlib import Path
from contextlib import ExitStack

# Set environment variable to bypass tool consent prompts
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# Import Strands components
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)

class FilteredMCPClient(MCPClient):
    """Subclass of MCPClient that filters None parameters in tool calls"""
    
    def call_tool_sync(self, tool_name, **kwargs):
        """Override call_tool_sync to filter None parameters"""
        # Filter out None values and offset=0
        filtered_kwargs = {}
        for k, v in kwargs.items():
            if v is None:
                continue
            if k == 'offset' and v == 0:
                continue
            filtered_kwargs[k] = v
        
        logger.info(f"Filtering MCP sync call: {tool_name}")
        logger.info(f"  Original: {list(kwargs.keys())}")
        logger.info(f"  Filtered: {filtered_kwargs}")
        
        # Call the parent method with filtered parameters
        return super().call_tool_sync(tool_name, **filtered_kwargs)
    
    async def call_tool_async(self, tool_use_id, name, arguments, **kwargs):
        """Override call_tool_async to filter None parameters"""
        # Filter out None values and offset=0 from arguments
        if arguments:
            filtered_arguments = {}
            for k, v in arguments.items():
                if v is None:
                    continue
                if k == 'offset' and v == 0:
                    continue
                filtered_arguments[k] = v
            
            logger.info(f"Filtering MCP async call: {name}")
            logger.info(f"  Original args: {list(arguments.keys())}")
            logger.info(f"  Filtered args: {filtered_arguments}")
        else:
            filtered_arguments = arguments
        
        # Call the parent method with filtered parameters
        return await super().call_tool_async(tool_use_id, name, filtered_arguments, **kwargs)

class StrandsMCPAgent:
    """Strands Agent with proper MCP tool integration and Bedrock support"""
    
    def __init__(self, config_path: str = "data/mcp_servers.json", tools_config_path: str = "data/strands_tools_config.json"):
        self.config_path = Path(config_path)
        self.tools_config_path = Path(tools_config_path)
        self.mcp_servers = {}
        self.mcp_clients = {}
        self.conversation_history = []
        self.connected_servers = {}
        self.strands_tools = {}  # Store loaded Strands tools
        self.tools_config = {}  # Store tools configuration
        
        # Configure Bedrock model (default to Nova Lite)
        self.current_model_id = "amazon.nova-lite-v1:0"
        self.bedrock_model = BedrockModel(
            model_id=self.current_model_id,
            temperature=0.7,
            max_tokens=9500,
            streaming=True
        )
        
        # Load configurations
        self.load_mcp_server_configs()
        self.load_strands_tools_config()
        self.load_enabled_strands_tools()
        
        # Log loaded tools for debugging
        logger.info(f"Loaded {len(self.strands_tools)} Strands tools: {list(self.strands_tools.keys())}")
    
    def update_model(self, model_id: str):
        """Update the Bedrock model being used"""
        logger.info(f"Updating model from {self.current_model_id} to {model_id}")
        self.current_model_id = model_id
        
        # Create new model instance with updated ID
        self.bedrock_model = BedrockModel(
            model_id=model_id,
            temperature=0.7,
            max_tokens=9500,
            streaming=True
        )
        logger.info(f"Model updated successfully to {model_id}")
    
    def load_strands_tools_config(self):
        """Load Strands tools configuration"""
        if not self.tools_config_path.exists():
            logger.warning(f"Strands tools config file not found: {self.tools_config_path}")
            return
        
        try:
            with open(self.tools_config_path, 'r') as f:
                self.tools_config = json.load(f)
            
            # Apply tool preferences
            if self.tools_config.get('tool_preferences', {}).get('consent_bypass', False):
                os.environ["BYPASS_TOOL_CONSENT"] = "true"
                logger.info("Tool consent bypass enabled")
            
            logger.info(f"Loaded Strands tools configuration")
        except Exception as e:
            logger.error(f"Failed to load Strands tools config: {str(e)}")
            self.tools_config = {"enabled_tools": [], "tool_categories": {}}
    
    def load_enabled_strands_tools(self):
        """Dynamically load enabled Strands tools"""
        self.strands_tools = {}
        
        if not self.tools_config:
            return
        
        # Get all enabled tools from categories
        enabled_tools = set()
        for category, tools in self.tools_config.get('tool_categories', {}).items():
            for tool_id, tool_info in tools.items():
                if tool_info.get('enabled', False):
                    module_name = tool_info.get('module', tool_id)
                    enabled_tools.add(module_name)
        
        # Load each enabled tool
        for tool_name in enabled_tools:
            try:
                # Import the specific tool module from strands_tools
                tool_module = importlib.import_module(f'strands_tools.{tool_name}')
                
                # Get the tool function from the module (usually has the same name)
                if hasattr(tool_module, tool_name):
                    tool = getattr(tool_module, tool_name)
                    self.strands_tools[tool_name] = tool
                    logger.info(f"Loaded Strands tool: {tool_name}")
                else:
                    # Some tools might have different function names, check TOOL_SPEC
                    logger.warning(f"Tool function {tool_name} not found in module strands_tools.{tool_name}")
            except ImportError as e:
                logger.error(f"Failed to import tool {tool_name}: {str(e)}")
            except Exception as e:
                logger.error(f"Error loading tool {tool_name}: {str(e)}")
    
    def get_strands_tools_status(self) -> Dict[str, Any]:
        """Get status of all Strands tools"""
        status = {
            "categories": {},
            "total_available": 0,
            "total_enabled": 0,
            "loaded_tools": list(self.strands_tools.keys())
        }
        
        for category, tools in self.tools_config.get('tool_categories', {}).items():
            category_info = {
                "tools": {},
                "enabled_count": 0
            }
            
            for tool_id, tool_info in tools.items():
                is_enabled = tool_info.get('enabled', False)
                is_loaded = tool_info.get('module', tool_id) in self.strands_tools
                
                category_info["tools"][tool_id] = {
                    "name": tool_info.get('name', tool_id),
                    "description": tool_info.get('description', ''),
                    "enabled": is_enabled,
                    "loaded": is_loaded,
                    "requires_extra": tool_info.get('requires_extra')
                }
                
                status["total_available"] += 1
                if is_enabled:
                    category_info["enabled_count"] += 1
                    status["total_enabled"] += 1
            
            status["categories"][category] = category_info
        
        return status
    
    def toggle_strands_tool(self, tool_id: str, category: str, enabled: bool) -> bool:
        """Enable or disable a Strands tool"""
        try:
            # Update configuration
            if category in self.tools_config.get('tool_categories', {}):
                if tool_id in self.tools_config['tool_categories'][category]:
                    self.tools_config['tool_categories'][category][tool_id]['enabled'] = enabled
                    
                    # Save configuration
                    with open(self.tools_config_path, 'w') as f:
                        json.dump(self.tools_config, f, indent=2)
                    
                    # Reload tools
                    self.load_enabled_strands_tools()
                    
                    logger.info(f"Tool {tool_id} {'enabled' if enabled else 'disabled'}")
                    return True
            
            logger.error(f"Tool {tool_id} not found in category {category}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to toggle tool {tool_id}: {str(e)}")
            return False
    
    def bulk_update_strands_tools(self, updates: Dict[str, bool]) -> Dict[str, bool]:
        """Bulk update multiple Strands tools"""
        results = {}
        
        for tool_key, enabled in updates.items():
            # tool_key format: "category:tool_id"
            if ':' in tool_key:
                category, tool_id = tool_key.split(':', 1)
                success = self.toggle_strands_tool(tool_id, category, enabled)
                results[tool_key] = success
            else:
                results[tool_key] = False
        
        return results
    
    def load_mcp_server_configs(self):
        """Load MCP server configurations without connecting"""
        if not self.config_path.exists():
            logger.warning(f"MCP config file not found: {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            servers = config.get('active_servers', {})
            logger.info(f"Loaded {len(servers)} MCP server configurations")
            
            for server_id, server_config in servers.items():
                if server_config.get('enabled', True):
                    self.mcp_servers[server_id] = server_config
                    logger.info(f"Loaded config for: {server_config.get('name', server_id)}")
                
        except Exception as e:
            logger.error(f"Failed to load MCP server configs: {str(e)}")
    
    async def connect_server(self, server_id: str) -> bool:
        """Connect to a specific MCP server"""
        if server_id not in self.mcp_servers:
            logger.error(f"Server {server_id} not found in configuration")
            return False
        
        if server_id in self.mcp_clients:
            logger.info(f"Server {server_id} already connected")
            return True
        
        server_config = self.mcp_servers[server_id]
        
        try:
            # Prepare command and environment
            command = server_config.get('command', [])
            args = server_config.get('args', [])
            env_vars = server_config.get('env_vars', {})
            
            if not command:
                logger.error(f"No command specified for server {server_id}")
                return False
            
            # Prepare environment
            env = os.environ.copy()
            env.update(env_vars)
            
            # Create transport function for stdio connection
            def create_stdio_transport():
                full_command = command + args
                return stdio_client(StdioServerParameters(
                    command=full_command[0],
                    args=full_command[1:] if len(full_command) > 1 else [],
                    env=env
                ))
            
            # Create FilteredMCPClient (subclass that filters None params)
            mcp_client = FilteredMCPClient(create_stdio_transport)
            
            # Test connection by listing tools synchronously
            # MCPClient uses sync context manager
            with mcp_client:
                tools = mcp_client.list_tools_sync()
                tool_count = len(tools) if tools else 0
            
            self.mcp_clients[server_id] = mcp_client
            self.connected_servers[server_id] = {
                'name': server_config.get('name', f'Server {server_id}'),
                'description': server_config.get('description', ''),
                'status': 'connected',
                'tools_count': tool_count
            }
            
            logger.info(f"Connected to {server_config.get('name', server_id)}: {tool_count} tools available")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {server_id}: {str(e)}")
            self.connected_servers[server_id] = {
                'name': server_config.get('name', f'Server {server_id}'),
                'status': 'error',
                'error': str(e)
            }
            return False
    
    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from a specific MCP server"""
        if server_id in self.mcp_clients:
            try:
                del self.mcp_clients[server_id]
                if server_id in self.connected_servers:
                    del self.connected_servers[server_id]
                logger.info(f"Disconnected from server {server_id}")
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from {server_id}: {str(e)}")
                return False
        return True
    
    async def get_available_tools(self) -> List[Dict]:
        """Get list of all available tools from connected servers and Strands"""
        # Start with loaded Strands tools
        all_tools = list(self.strands_tools.values())
        
        for server_id, mcp_client in self.mcp_clients.items():
            try:
                # Use sync context manager
                with mcp_client:
                    tools = mcp_client.list_tools_sync()
                    # Note: Don't wrap here since this is just for listing, not execution
                    for tool in tools:
                        # Handle MCPAgentTool structure
                        if hasattr(tool, 'tool_def'):
                            name = tool.tool_def.name
                            description = tool.tool_def.description
                        else:
                            name = getattr(tool, 'name', 'unknown')
                            description = getattr(tool, 'description', '')
                        
                        all_tools.append({
                            'name': name,
                            'description': description,
                            'server_id': server_id,
                            'server_name': self.connected_servers.get(server_id, {}).get('name', 'Unknown')
                        })
            except Exception as e:
                logger.error(f"Failed to get tools from {server_id}: {str(e)}")
        
        return all_tools
    
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 9500,
        use_tools: bool = True
    ) -> Dict[str, Any]:
        """Send a chat message and get response with proper MCP context management"""
        try:
            # Update model parameters
            self.bedrock_model.temperature = temperature
            self.bedrock_model.max_tokens = max_tokens
            
            # Prepare the conversation context
            conversation_messages = []
            
            # Add tool usage guidance
            tool_guidance = """IMPORTANT: You have access to real tools that you MUST use to complete tasks. 

When a user asks you to perform an action that requires a tool:
1. IMMEDIATELY invoke the appropriate tool - DO NOT describe what you would do
2. Use the actual tool function, not a JSON representation
3. Wait for the tool's response before continuing
4. Base your response on the actual tool output

Tool Usage Rules:
- ALWAYS use tools when they are relevant to the user's request
- NEVER describe tool usage in hypothetical terms like "I would use" or "I will use"
- DIRECTLY invoke tools without asking for permission
- Only provide parameters that have actual values
- Never provide empty strings, None, null, or undefined values
- For file operations: Use file_read to read files, file_edit to modify them
- For system operations: Use shell to execute commands
- For calculations: Use calculator for mathematical operations

Example: If asked to "read the README file":
✓ CORRECT: Directly call file_read(file_path="README.md")
✗ WRONG: "I will use the file_read tool to read the README file"

You are an AI assistant with REAL tool access. Use them!"""
            
            if system_prompt:
                conversation_messages.append(f"System: {system_prompt}\n\n{tool_guidance}")
            else:
                conversation_messages.append(f"System: {tool_guidance}")
            
            # Add recent conversation history
            recent_history = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
            for item in recent_history:
                if item['role'] == 'user':
                    conversation_messages.append(f"User: {item['content']}")
                else:
                    conversation_messages.append(f"Assistant: {item['content']}")
            
            conversation_messages.append(f"User: {message}")
            full_conversation = "\n\n".join(conversation_messages)
            
            response_text = ""
            
            if use_tools and (self.mcp_clients or self.strands_tools):
                # Execute within all MCP client contexts using sync context manager
                with ExitStack() as stack:
                    # Start with loaded Strands tools
                    all_tools = list(self.strands_tools.values())
                    
                    # Add MCP tools if any clients are connected
                    for mcp_client in self.mcp_clients.values():
                        stack.enter_context(mcp_client)
                        tools = mcp_client.list_tools_sync()
                        all_tools.extend(tools)
                    
                    # Create agent with Bedrock model and all tools
                    logger.info(f"Creating agent with {len(all_tools)} tools")
                    agent = Agent(model=self.bedrock_model, tools=all_tools)
                    
                    # Run the agent (using direct call, not run_async)
                    response = agent(full_conversation)
                    response_text = str(response) if response else "No response generated"
            else:
                # Create agent without tools
                agent = Agent(model=self.bedrock_model)
                response = agent(full_conversation)
                response_text = str(response) if response else "No response generated"
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep history manageable
            if len(self.conversation_history) > 50:
                self.conversation_history = self.conversation_history[-40:]
            
            return {
                "success": True,
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Chat error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def stream_chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 9500,
        use_tools: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat responses with proper event handling"""
        try:
            # Update model parameters
            self.bedrock_model.temperature = temperature
            self.bedrock_model.max_tokens = max_tokens
            
            # Prepare conversation
            conversation_messages = []
            
            # Add tool usage guidance
            tool_guidance = """IMPORTANT: You have access to real tools that you MUST use to complete tasks. 

When a user asks you to perform an action that requires a tool:
1. IMMEDIATELY invoke the appropriate tool - DO NOT describe what you would do
2. Use the actual tool function, not a JSON representation
3. Wait for the tool's response before continuing
4. Base your response on the actual tool output

Tool Usage Rules:
- ALWAYS use tools when they are relevant to the user's request
- NEVER describe tool usage in hypothetical terms like "I would use" or "I will use"
- DIRECTLY invoke tools without asking for permission
- Only provide parameters that have actual values
- Never provide empty strings, None, null, or undefined values
- For file operations: Use file_read to read files, file_edit to modify them
- For system operations: Use shell to execute commands
- For calculations: Use calculator for mathematical operations

Example: If asked to "read the README file":
✓ CORRECT: Directly call file_read(file_path="README.md")
✗ WRONG: "I will use the file_read tool to read the README file"

You are an AI assistant with REAL tool access. Use them!"""
            
            if system_prompt:
                conversation_messages.append(f"System: {system_prompt}\n\n{tool_guidance}")
            else:
                conversation_messages.append(f"System: {tool_guidance}")
            
            recent_history = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
            for item in recent_history:
                if item['role'] == 'user':
                    conversation_messages.append(f"User: {item['content']}")
                else:
                    conversation_messages.append(f"Assistant: {item['content']}")
            
            conversation_messages.append(f"User: {message}")
            full_conversation = "\n\n".join(conversation_messages)
            
            full_response = ""
            current_tool_use = None
            
            if use_tools and (self.mcp_clients or self.strands_tools):
                # Stream within MCP contexts
                with ExitStack() as stack:
                    # Start with loaded Strands tools
                    all_tools = list(self.strands_tools.values())
                    
                    # Add MCP tools if any clients are connected
                    for mcp_client in self.mcp_clients.values():
                        stack.enter_context(mcp_client)
                        tools = mcp_client.list_tools_sync()
                        all_tools.extend(tools)
                    
                    # Create agent with all tools
                    logger.info(f"Streaming with {len(all_tools)} tools")
                    agent = Agent(model=self.bedrock_model, tools=all_tools)
                    
                    # Stream the response - simplified approach
                    async for event in agent.stream_async(full_conversation):
                        # Parse the complex event structure
                        if isinstance(event, dict):
                            # Check for nested event structure
                            if 'event' in event:
                                event_data = event['event']
                                
                                # Handle text deltas - just send raw text
                                if 'contentBlockDelta' in event_data:
                                    delta = event_data['contentBlockDelta'].get('delta', {})
                                    if 'text' in delta:
                                        text = delta['text']
                                        full_response += text
                                        # Send raw text to frontend for parsing
                                        yield {
                                            "type": "text_delta",
                                            "text": text,
                                            "timestamp": datetime.now().isoformat()
                                        }
                                
                                # Handle tool use
                                elif 'toolUse' in event_data:
                                    tool_info = event_data['toolUse']
                                    yield {
                                        "type": "tool_execution",
                                        "tool_name": tool_info.get('name', 'unknown'),
                                        "tool_id": tool_info.get('toolUseId', ''),
                                        "input": tool_info.get('input', {}),
                                        "timestamp": datetime.now().isoformat()
                                    }
                                
                                # Handle tool results
                                elif 'toolResult' in event_data:
                                    result_info = event_data['toolResult']
                                    yield {
                                        "type": "tool_result",
                                        "content": result_info.get('content', []),
                                        "timestamp": datetime.now().isoformat()
                                    }
                                
                                # Handle message stop
                                elif 'messageStop' in event_data:
                                    # Message is complete
                                    pass  # Will handle completion below
                            
                            # Don't also process 'data' field if we already processed 'event'
                            # This was causing duplication
                        elif isinstance(event, str):
                            # Handle direct string responses
                            text = event
                            # Skip metadata output 
                            if not text.startswith('{'):
                                full_response += text
                                yield {
                                    "type": "text_delta",
                                    "text": text,
                                    "timestamp": datetime.now().isoformat()
                                }
            else:
                # Stream without tools
                agent = Agent(model=self.bedrock_model)
                
                async for event in agent.stream_async(full_conversation):
                    # Parse event structure
                    if isinstance(event, dict):
                        if 'event' in event:
                            event_data = event['event']
                            if 'contentBlockDelta' in event_data:
                                delta = event_data['contentBlockDelta'].get('delta', {})
                                if 'text' in delta:
                                    text = delta['text']
                                    full_response += text
                                    yield {
                                        "type": "text_delta",
                                        "text": text,
                                        "timestamp": datetime.now().isoformat()
                                    }
                        # Don't process 'data' if we already processed 'event'
            
            # Signal completion
            yield {
                "type": "message_complete",
                "timestamp": datetime.now().isoformat()
            }
            
            # Update history
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep history manageable
            if len(self.conversation_history) > 50:
                self.conversation_history = self.conversation_history[-40:]
                
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_server_status(self, server_id: str = None) -> Dict[str, Any]:
        """Get status of MCP servers"""
        if server_id:
            if server_id in self.connected_servers:
                return self.connected_servers[server_id]
            elif server_id in self.mcp_servers:
                return {
                    "name": self.mcp_servers[server_id].get('name', server_id),
                    "status": "disconnected"
                }
            else:
                return {"error": "Server not found"}
        
        # Return status for all servers
        all_servers = {}
        
        # Add connected servers
        for sid, info in self.connected_servers.items():
            all_servers[sid] = info
        
        # Add disconnected servers
        for sid, config in self.mcp_servers.items():
            if sid not in all_servers:
                all_servers[sid] = {
                    "name": config.get('name', sid),
                    "status": "disconnected"
                }
        
        total_tools = sum(
            s.get('tools_count', 0) 
            for s in self.connected_servers.values() 
            if s.get('status') == 'connected'
        )
        
        return {
            "servers": all_servers,
            "total_servers": len(self.mcp_servers),
            "connected_servers": len([s for s in self.connected_servers.values() if s['status'] == 'connected']),
            "total_tools": total_tools
        }
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_conversation_stats(self) -> Dict:
        """Get conversation statistics"""
        total_messages = len(self.conversation_history)
        user_messages = sum(1 for msg in self.conversation_history if msg['role'] == 'user')
        assistant_messages = sum(1 for msg in self.conversation_history if msg['role'] == 'assistant')
        
        total_tools = sum(
            s.get('tools_count', 0) 
            for s in self.connected_servers.values() 
            if s.get('status') == 'connected'
        )
        
        return {
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "available_tools": total_tools,
            "connected_servers": len([s for s in self.connected_servers.values() if s['status'] == 'connected'])
        }
    
    async def test_connection(self) -> bool:
        """Test the agent connectivity"""
        try:
            # Test basic Bedrock connection without tools
            agent = Agent(model=self.bedrock_model)
            response = agent("Say 'Hello' and nothing else")
            return bool(response)
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

# Singleton instance
_strands_agent = None

def get_strands_mcp_agent(config_path: str = "data/mcp_servers.json") -> StrandsMCPAgent:
    """Get or create the Strands MCP agent singleton"""
    global _strands_agent
    if _strands_agent is None:
        _strands_agent = StrandsMCPAgent(config_path)
    return _strands_agent