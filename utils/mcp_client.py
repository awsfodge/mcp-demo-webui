"""
MCP (Model Context Protocol) Client Manager
Handles connections to MCP servers and manages tool execution
"""
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import subprocess
import sys
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)

@dataclass
class MCPServer:
    """Represents an MCP server configuration"""
    id: str
    name: str
    description: str
    command: List[str]
    args: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    auto_connect: bool = False
    category: str = "General"
    
    process: Optional[subprocess.Popen] = None
    stdin: Optional[Any] = None
    stdout: Optional[Any] = None
    session: Optional[Any] = None
    available_tools: List[Dict] = field(default_factory=list)
    status: str = "disconnected"
    last_error: Optional[str] = None
    connected_at: Optional[datetime] = None

class MCPClientManager:
    """Manages multiple MCP server connections"""
    
    def __init__(self, config_path: str = "data/mcp_servers.json"):
        self.config_path = Path(config_path)
        self.servers: Dict[str, MCPServer] = {}
        self.active_connections: Dict[str, AsyncExitStack] = {}
        self.tool_call_history: List[Dict] = []
        self.event_callbacks: Dict[str, List] = {}
        self.load_config()
    
    def load_config(self):
        """Load MCP server configurations from file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                for server_id, server_config in config.get('active_servers', {}).items():
                    self.servers[server_id] = MCPServer(
                        id=server_id,
                        name=server_config.get('name', 'Unknown Server'),
                        description=server_config.get('description', ''),
                        command=server_config.get('command', []),
                        args=server_config.get('args', []),
                        env_vars=server_config.get('env_vars', {}),
                        enabled=server_config.get('enabled', True),
                        auto_connect=server_config.get('auto_connect', False),
                        category=server_config.get('category', 'General')
                    )
    
    def save_config(self):
        """Save current server configurations to file"""
        config = {
            'active_servers': {},
            'settings': {
                'auto_reconnect': True,
                'connection_timeout': 30.0,
                'tool_timeout': 60.0,
                'session_init_timeout': 15.0,
                'list_tools_timeout': 10.0,
                'max_concurrent_tools': 5,
                'log_tool_calls': True,
                'updated_at': datetime.now().isoformat()
            }
        }
        
        for server_id, server in self.servers.items():
            config['active_servers'][server_id] = {
                'name': server.name,
                'description': server.description,
                'command': server.command,
                'args': server.args,
                'env_vars': server.env_vars,
                'enabled': server.enabled,
                'auto_connect': server.auto_connect,
                'category': server.category,
                'added_at': datetime.now().isoformat()
            }
        
        os.makedirs(self.config_path.parent, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    async def connect_server(self, server_id: str, timeout: float = 30.0) -> bool:
        """Connect to an MCP server using stdio transport with proper timeout handling"""
        if server_id not in self.servers:
            logger.error(f"Server {server_id} not found")
            return False
        
        server = self.servers[server_id]
        
        try:
            # Import MCP SDK components
            try:
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client
            except ImportError:
                logger.error("MCP SDK not installed. Please install with: pip install mcp")
                server.status = "error"
                server.last_error = "MCP SDK not installed"
                return False
            
            # Prepare environment
            env = os.environ.copy()
            env.update(server.env_vars)
            
            # Create server parameters
            # Combine command and args properly
            full_command = server.command + server.args
            server_params = StdioServerParameters(
                command=full_command[0] if full_command else "node",
                args=full_command[1:] if len(full_command) > 1 else [],
                env=env
            )
            
            # Connect to server with timeout
            exit_stack = AsyncExitStack()
            self.active_connections[server_id] = exit_stack
            
            # Start stdio client with timeout - it returns (read_stream, write_stream) directly
            transport = await asyncio.wait_for(
                exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=timeout
            )
            read_stream, write_stream = transport
            
            # Initialize client session with timeout
            session = await asyncio.wait_for(
                exit_stack.enter_async_context(ClientSession(read_stream, write_stream)),
                timeout=10.0  # Shorter timeout for session creation
            )
            
            # Initialize the session with timeout
            await asyncio.wait_for(session.initialize(), timeout=15.0)
            
            # Store session info
            server.session = session
            server.status = "connected"
            server.connected_at = datetime.now()
            
            # List available tools with timeout
            tools_response = await asyncio.wait_for(session.list_tools(), timeout=10.0)
            server.available_tools = [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'inputSchema': tool.inputSchema
                }
                for tool in tools_response.tools
            ]
            
            logger.info(f"Connected to MCP server: {server.name} with {len(server.available_tools)} tools")
            self._trigger_event('server_connected', {
                'server_id': server_id,
                'tools': server.available_tools
            })
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to server {server.name} after {timeout} seconds")
            server.status = "error"
            server.last_error = f"Connection timeout after {timeout} seconds"
            # Clean up on timeout
            if server_id in self.active_connections:
                try:
                    await self.active_connections[server_id].aclose()
                    del self.active_connections[server_id]
                except Exception:
                    pass
            self._trigger_event('server_error', {
                'server_id': server_id,
                'error': f"Connection timeout after {timeout} seconds"
            })
            return False
        except Exception as e:
            logger.error(f"Failed to connect to server {server.name}: {str(e)}")
            server.status = "error"
            server.last_error = str(e)
            # Clean up on error
            if server_id in self.active_connections:
                try:
                    await self.active_connections[server_id].aclose()
                    del self.active_connections[server_id]
                except Exception:
                    pass
            self._trigger_event('server_error', {
                'server_id': server_id,
                'error': str(e)
            })
            return False
    
    async def disconnect_server(self, server_id: str):
        """Disconnect from an MCP server"""
        if server_id in self.active_connections:
            try:
                exit_stack = self.active_connections[server_id]
                await exit_stack.aclose()
                del self.active_connections[server_id]
                
                if server_id in self.servers:
                    server = self.servers[server_id]
                    server.status = "disconnected"
                    server.session = None
                    server.connected_at = None
                    server.available_tools = []
                
                logger.info(f"Disconnected from server: {server_id}")
                self._trigger_event('server_disconnected', {'server_id': server_id})
                
            except Exception as e:
                logger.error(f"Error disconnecting from server {server_id}: {str(e)}")
    
    async def call_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any], timeout: float = 60.0) -> Dict[str, Any]:
        """Execute a tool on an MCP server with timeout"""
        if server_id not in self.servers:
            return {'error': f"Server {server_id} not found"}
        
        server = self.servers[server_id]
        
        if server.status != "connected" or not server.session:
            return {'error': f"Server {server.name} is not connected"}
        
        # Record tool call
        call_record = {
            'server_id': server_id,
            'server_name': server.name,
            'tool_name': tool_name,
            'arguments': arguments,
            'timestamp': datetime.now().isoformat(),
            'status': 'executing'
        }
        self.tool_call_history.append(call_record)
        
        # Trigger event for UI update
        self._trigger_event('tool_call_start', call_record)
        
        try:
            # Execute tool with timeout
            result = await asyncio.wait_for(
                server.session.call_tool(tool_name, arguments),
                timeout=timeout
            )
            
            # Update call record
            call_record['status'] = 'completed'
            call_record['result'] = result.content if hasattr(result, 'content') else str(result)
            call_record['duration'] = (datetime.now() - datetime.fromisoformat(call_record['timestamp'])).total_seconds()
            
            # Trigger completion event
            self._trigger_event('tool_call_complete', call_record)
            
            return {
                'success': True,
                'result': call_record['result'],
                'duration': call_record['duration']
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Tool execution timed out after {timeout} seconds: {tool_name}")
            
            # Update call record
            call_record['status'] = 'failed'
            call_record['error'] = f"Tool execution timed out after {timeout} seconds"
            call_record['duration'] = timeout
            
            # Trigger error event
            self._trigger_event('tool_call_error', call_record)
            
            return {
                'success': False,
                'error': f"Tool execution timed out after {timeout} seconds"
            }
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            
            # Update call record
            call_record['status'] = 'failed'
            call_record['error'] = str(e)
            call_record['duration'] = (datetime.now() - datetime.fromisoformat(call_record['timestamp'])).total_seconds()
            
            # Trigger error event
            self._trigger_event('tool_call_error', call_record)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_server(self, server_config: Dict) -> str:
        """Add a new MCP server configuration"""
        import uuid
        server_id = str(uuid.uuid4())
        
        server = MCPServer(
            id=server_id,
            name=server_config['name'],
            description=server_config.get('description', ''),
            command=server_config['command'],
            args=server_config.get('args', []),
            env_vars=server_config.get('env_vars', {}),
            enabled=server_config.get('enabled', True),
            auto_connect=server_config.get('auto_connect', False),
            category=server_config.get('category', 'General')
        )
        
        self.servers[server_id] = server
        self.save_config()
        
        return server_id
    
    def update_server(self, server_id: str, server_config: Dict) -> bool:
        """Update an existing MCP server configuration"""
        if server_id not in self.servers:
            return False
        
        server = self.servers[server_id]
        
        # Update fields
        server.name = server_config.get('name', server.name)
        server.description = server_config.get('description', server.description)
        server.command = server_config.get('command', server.command)
        server.args = server_config.get('args', server.args)
        server.env_vars = server_config.get('env_vars', server.env_vars)
        server.enabled = server_config.get('enabled', server.enabled)
        server.auto_connect = server_config.get('auto_connect', server.auto_connect)
        server.category = server_config.get('category', server.category)
        
        self.save_config()
        return True
    
    def remove_server(self, server_id: str):
        """Remove an MCP server"""
        if server_id in self.servers:
            # Disconnect if connected
            if server_id in self.active_connections:
                asyncio.create_task(self.disconnect_server(server_id))
            
            del self.servers[server_id]
            self.save_config()
    
    def get_server_status(self, server_id: str) -> Dict:
        """Get detailed status of a server"""
        if server_id not in self.servers:
            return {'error': 'Server not found'}
        
        server = self.servers[server_id]
        return {
            'id': server.id,
            'name': server.name,
            'description': server.description,
            'status': server.status,
            'category': server.category,
            'env_vars': server.env_vars,  # Include env vars in status
            'connected_at': server.connected_at.isoformat() if server.connected_at else None,
            'available_tools': server.available_tools,
            'last_error': server.last_error
        }
    
    def get_all_servers(self) -> List[Dict]:
        """Get status of all servers"""
        return [
            self.get_server_status(server_id)
            for server_id in self.servers.keys()
        ]
    
    def get_all_tools(self) -> List[Dict]:
        """Get all available tools from connected servers"""
        tools = []
        for server in self.servers.values():
            if server.status == "connected":
                for tool in server.available_tools:
                    tools.append({
                        'server_id': server.id,
                        'server_name': server.name,
                        'tool_name': tool['name'],
                        'description': tool['description'],
                        'inputSchema': tool.get('inputSchema', {})
                    })
        return tools
    
    def on_event(self, event_type: str, callback):
        """Register an event callback"""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    def _trigger_event(self, event_type: str, data: Any):
        """Trigger event callbacks"""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event callback error: {str(e)}")
    
    async def auto_connect_servers(self):
        """Auto-connect servers marked for auto-connection with timeout"""
        tasks = []
        for server_id, server in self.servers.items():
            if server.auto_connect and server.enabled:
                logger.info(f"Auto-connecting to {server.name}...")
                # Create task with timeout for each connection
                task = asyncio.create_task(self.connect_server(server_id, timeout=30.0))
                tasks.append((server_id, server.name, task))
        
        if tasks:
            # Wait for all connections with a global timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*[task for _, _, task in tasks], return_exceptions=True),
                    timeout=60.0  # Global timeout for all connections
                )
                
                for i, (server_id, server_name, _) in enumerate(tasks):
                    result = results[i]
                    if isinstance(result, Exception):
                        logger.error(f"Failed to auto-connect to {server_name}: {str(result)}")
                    elif result:
                        logger.info(f"Successfully auto-connected to {server_name}")
                    else:
                        logger.warning(f"Auto-connection to {server_name} returned False")
                        
            except asyncio.TimeoutError:
                logger.error("Auto-connection process timed out after 60 seconds")
                # Cancel remaining tasks
                for _, _, task in tasks:
                    if not task.done():
                        task.cancel()
    
    async def cleanup(self):
        """Clean up all connections"""
        for server_id in list(self.active_connections.keys()):
            await self.disconnect_server(server_id)

# Singleton instance
_mcp_manager = None

def get_mcp_manager() -> MCPClientManager:
    """Get or create the MCP client manager singleton"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager