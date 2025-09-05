"""
MCP (Model Context Protocol) API Routes
Handles WebSocket and REST endpoints for MCP client functionality
"""
import asyncio
import json
import logging
from flask import Blueprint, request, jsonify, session
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.mcp_client import MCPClientManager
from utils.strands_mcp_agent import StrandsMCPAgent

logger = logging.getLogger(__name__)

# Singleton pattern for managers
_mcp_manager = None
_strands_agent = None

def get_mcp_manager():
    """Get or create MCP manager singleton"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager

def get_strands_mcp_agent():
    """Get or create Strands MCP agent singleton"""
    global _strands_agent
    if _strands_agent is None:
        _strands_agent = StrandsMCPAgent()
    return _strands_agent

def run_async_safely(coro, timeout=30.0):
    """Safely run async coroutine in sync context"""
    try:
        return asyncio.run(asyncio.wait_for(coro, timeout=timeout))
    except asyncio.TimeoutError:
        logger.error(f"Async operation timed out after {timeout} seconds")
        raise
    except Exception as e:
        logger.error(f"Async operation failed: {str(e)}")
        raise

# Create Blueprint
mcp_bp = Blueprint('mcp', __name__)

# Initialize Strands MCP agent
strands_agent = get_strands_mcp_agent()

# Keep original MCP manager for compatibility
mcp_manager = get_mcp_manager()

# REST API Routes

@mcp_bp.route('/servers', methods=['GET'])
def get_servers():
    """Get all MCP servers and their status from Strands agent"""
    try:
        status = strands_agent.get_server_status()
        # Convert to expected format for backward compatibility
        servers_list = []
        
        # Load full configuration details from file
        config_path = Path("data/mcp_servers.json")
        full_configs = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                full_configs = config_data.get('active_servers', {})
        
        for server_id, server_info in status.get('servers', {}).items():
            # Merge status with full config
            server_data = {
                'id': server_id,
                'name': server_info.get('name', server_id),
                'status': server_info.get('status', 'unknown'),
                'tools_count': server_info.get('tools_count', 0),
                'error': server_info.get('error')
            }
            
            # Add full config details if available
            if server_id in full_configs:
                server_data.update({
                    'description': full_configs[server_id].get('description'),
                    'command': full_configs[server_id].get('command'),
                    'args': full_configs[server_id].get('args'),
                    'env_vars': full_configs[server_id].get('env_vars'),
                    'category': full_configs[server_id].get('category'),
                    'auto_connect': full_configs[server_id].get('auto_connect')
                })
            
            servers_list.append(server_data)
        
        return jsonify({
            'success': True,
            'servers': servers_list
        })
    except Exception as e:
        logger.error(f"Error getting servers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/server-configs', methods=['GET'])
def get_server_configs():
    """Get detailed configuration for all servers"""
    try:
        config_path = Path("data/mcp_servers.json")
        if not config_path.exists():
            return jsonify({
                'success': True,
                'configs': {}
            })
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return jsonify({
            'success': True,
            'configs': config_data.get('active_servers', {})
        })
    except Exception as e:
        logger.error(f"Error getting server configs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/available-servers', methods=['GET'])
def get_available_servers():
    """Get available MCP servers for agent builder (without connecting)"""
    try:
        # Load server configurations from file
        from pathlib import Path
        config_path = Path("data/mcp_servers.json")
        
        if not config_path.exists():
            return jsonify({
                'success': True,
                'servers': []
            })
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        servers_list = []
        for server_id, server_info in config.get('active_servers', {}).items():
            if server_info.get('enabled', True):
                servers_list.append({
                    'id': server_id,
                    'name': server_info.get('name', 'Unnamed Server'),
                    'description': server_info.get('description', ''),
                    'category': server_info.get('category', 'General'),
                    'command': server_info.get('command', []),
                    'auto_connect': server_info.get('auto_connect', False)
                })
        
        return jsonify({
            'success': True,
            'servers': servers_list
        })
    except Exception as e:
        logger.error(f"Error getting available servers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/servers', methods=['POST'])
def add_server():
    """Add a new MCP server"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'command']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f"Missing required field: {field}"
                }), 400
        
        # Add the server to configuration
        server_id = mcp_manager.add_server(data)
        
        # Reload configurations in Strands agent
        strands_agent.load_mcp_server_configs()
        
        # Don't auto-connect - let the UI handle connection
        return jsonify({
            'success': True,
            'server_id': server_id,
            'message': f"Server '{data['name']}' added successfully"
        })
        
    except Exception as e:
        logger.error(f"Error adding server: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/servers/<server_id>', methods=['PUT'])
def update_server(server_id):
    """Update an MCP server configuration"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'command']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f"Missing required field: {field}"
                }), 400
        
        # Update the server configuration
        success = mcp_manager.update_server(server_id, data)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Server not found'
            }), 404
        
        # Reload configurations in Strands agent
        strands_agent.load_mcp_server_configs()
        
        return jsonify({
            'success': True,
            'message': f"Server '{data['name']}' updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating server: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/servers/<server_id>', methods=['DELETE'])
def remove_server(server_id):
    """Remove an MCP server"""
    try:
        # Disconnect first if connected
        if server_id in strands_agent.mcp_clients:
            run_async_safely(strands_agent.disconnect_server(server_id))
        
        # Remove from configuration
        mcp_manager.remove_server(server_id)
        
        # Reload configurations
        strands_agent.load_mcp_server_configs()
        
        return jsonify({
            'success': True,
            'message': 'Server removed successfully'
        })
    except Exception as e:
        logger.error(f"Error removing server: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/servers/<server_id>/connect', methods=['POST'])
def connect_server(server_id):
    """Connect to an MCP server"""
    try:
        # Connect using Strands agent
        connected = run_async_safely(strands_agent.connect_server(server_id), timeout=30.0)
        
        if connected:
            # Get updated status
            status = strands_agent.get_server_status(server_id)
            return jsonify({
                'success': True,
                'message': 'Server connected successfully',
                'status': status
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to connect to server'
            }), 500
            
    except asyncio.TimeoutError:
        return jsonify({
            'success': False,
            'error': 'Connection timed out after 30 seconds'
        }), 408
    except Exception as e:
        logger.error(f"Error connecting to server: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/servers/<server_id>/disconnect', methods=['POST'])
def disconnect_server(server_id):
    """Disconnect from an MCP server"""
    try:
        # Disconnect using Strands agent
        disconnected = run_async_safely(strands_agent.disconnect_server(server_id))
        
        if disconnected:
            return jsonify({
                'success': True,
                'message': 'Server disconnected successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to disconnect from server'
            }), 500
            
    except Exception as e:
        logger.error(f"Error disconnecting from server: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/servers/<server_id>/status', methods=['GET'])
def get_server_status(server_id):
    """Get detailed status of a specific server from Strands agent"""
    try:
        status = strands_agent.get_server_status(server_id)
        if 'error' in status:
            return jsonify({
                'success': False,
                'error': status['error']
            }), 404
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"Error getting server status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/tools', methods=['GET'])
def get_tools():
    """Get all available tools from Strands agent"""
    try:
        # Get tools asynchronously
        tools = run_async_safely(strands_agent.get_available_tools())
        return jsonify({
            'success': True,
            'tools': tools
        })
    except Exception as e:
        logger.error(f"Error getting tools: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/tools/execute', methods=['POST'])
def execute_tool():
    """Execute a tool via chat with Strands agent (tools are executed automatically)"""
    try:
        data = request.json
        tool_name = data.get('tool_name')
        arguments = data.get('arguments', {})
        timeout = data.get('timeout', 60.0)
        
        if not tool_name:
            return jsonify({
                'success': False,
                'error': 'Missing tool_name'
            }), 400
        
        # Create a message that will trigger the tool execution
        tool_message = f"Please use the {tool_name} tool with these parameters: {json.dumps(arguments)}"
        
        # Execute via chat (Strands will handle tool execution automatically)
        result = run_async_safely(
            strands_agent.chat(
                message=tool_message,
                use_tools=True
            ),
            timeout=timeout
        )
        
        return jsonify({
            'success': result.get('success', False),
            'result': result
        })
        
    except asyncio.TimeoutError:
        return jsonify({
            'success': False,
            'error': f'Tool execution timed out after {timeout} seconds'
        }), 408
    except Exception as e:
        logger.error(f"Error executing tool: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/chat', methods=['POST'])
def chat():
    """Send a chat message to Strands agent with MCP tool support"""
    try:
        data = request.json
        message = data.get('message')
        use_tools = data.get('use_tools', True)
        system_prompt = data.get('system_prompt')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 32768)
        timeout = data.get('timeout', 120.0)
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Missing message'
            }), 400
        
        # Send message to Strands agent
        response = run_async_safely(
            strands_agent.chat(
                message=message,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                use_tools=use_tools
            ),
            timeout=timeout
        )
        
        return jsonify(response)
        
    except asyncio.TimeoutError:
        return jsonify({
            'success': False,
            'error': f'Chat request timed out after {timeout} seconds'
        }), 408
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/chat/clear', methods=['POST'])
def clear_chat():
    """Clear the chat history"""
    try:
        strands_agent.clear_history()
        return jsonify({
            'success': True,
            'message': 'Chat history cleared'
        })
    except Exception as e:
        logger.error(f"Error clearing chat: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/chat/stats', methods=['GET'])
def get_chat_stats():
    """Get chat conversation statistics"""
    try:
        stats = strands_agent.get_conversation_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting chat stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/strands-tools', methods=['GET'])
def get_strands_tools():
    """Get all available Strands tools with their status"""
    try:
        status = strands_agent.get_strands_tools_status()
        return jsonify({
            'success': True,
            'tools': status
        })
    except Exception as e:
        logger.error(f"Error getting Strands tools: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/strands-tools/enabled', methods=['GET'])
def get_enabled_strands_tools():
    """Get currently enabled Strands tools"""
    try:
        status = strands_agent.get_strands_tools_status()
        enabled_tools = []
        
        for category, cat_info in status.get('categories', {}).items():
            for tool_id, tool_info in cat_info.get('tools', {}).items():
                if tool_info.get('enabled', False):
                    enabled_tools.append({
                        'id': tool_id,
                        'category': category,
                        'name': tool_info.get('name'),
                        'loaded': tool_info.get('loaded')
                    })
        
        return jsonify({
            'success': True,
            'enabled_tools': enabled_tools,
            'count': len(enabled_tools)
        })
    except Exception as e:
        logger.error(f"Error getting enabled tools: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/strands-tools/toggle', methods=['POST'])
def toggle_strands_tool():
    """Enable or disable a specific Strands tool"""
    try:
        data = request.json
        tool_id = data.get('tool_id')
        category = data.get('category')
        enabled = data.get('enabled', False)
        
        if not tool_id or not category:
            return jsonify({
                'success': False,
                'error': 'Missing tool_id or category'
            }), 400
        
        success = strands_agent.toggle_strands_tool(tool_id, category, enabled)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Tool {tool_id} {'enabled' if enabled else 'disabled'}"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to toggle tool'
            }), 500
            
    except Exception as e:
        logger.error(f"Error toggling tool: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/strands-tools/bulk-update', methods=['POST'])
def bulk_update_strands_tools():
    """Update multiple Strands tools at once"""
    try:
        data = request.json
        updates = data.get('updates', {})
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No updates provided'
            }), 400
        
        results = strands_agent.bulk_update_strands_tools(updates)
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'Updated {len(results)} tools'
        })
        
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/history', methods=['GET'])
def get_tool_history():
    """Get tool execution history"""
    try:
        history = mcp_manager.tool_call_history
        # Limit to last 50 calls
        recent_history = history[-50:] if len(history) > 50 else history
        
        return jsonify({
            'success': True,
            'history': recent_history,
            'total_calls': len(history)
        })
    except Exception as e:
        logger.error(f"Error getting tool history: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/model', methods=['GET', 'POST'])
def handle_model():
    """Get or set the model ID"""
    global strands_agent
    
    if request.method == 'POST':
        data = request.get_json()
        model_id = data.get('model', 'amazon.nova-lite-v1:0')
        
        try:
            # Update the model in Strands agent
            if strands_agent:
                strands_agent.update_model(model_id)
            
            # Store in session
            session['selected_model'] = model_id
            
            return jsonify({
                'success': True,
                'model': model_id
            })
        except Exception as e:
            logger.error(f"Error updating model: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    else:
        # GET request - return current model
        model_id = session.get('selected_model', 'amazon.nova-lite-v1:0')
        return jsonify({
            'success': True,
            'model': model_id
        })

@mcp_bp.route('/system-prompt', methods=['GET', 'POST'])
def handle_system_prompt():
    """Get or set the system prompt for the MCP agent"""
    if request.method == 'GET':
        # Get current system prompt from session
        current_prompt = session.get('mcp_system_prompt', 
                                    'You are a helpful AI assistant with access to MCP tools.')
        return jsonify({
            'success': True,
            'system_prompt': current_prompt
        })
    
    elif request.method == 'POST':
        # Update system prompt in session
        data = request.json
        new_prompt = data.get('system_prompt', '').strip()
        
        if not new_prompt:
            return jsonify({
                'success': False,
                'error': 'System prompt cannot be empty'
            }), 400
        
        session['mcp_system_prompt'] = new_prompt
        
        return jsonify({
            'success': True,
            'message': 'System prompt updated',
            'system_prompt': new_prompt
        })

@mcp_bp.route('/test', methods=['GET'])
def test_connection():
    """Test the connection to Strands agent"""
    try:
        connected = run_async_safely(strands_agent.test_connection(), timeout=15.0)
        server_status = strands_agent.get_server_status()
        
        return jsonify({
            'success': True,
            'strands_connected': connected,
            'mcp_servers': server_status.get('total_servers', 0),
            'connected_servers': server_status.get('connected_servers', 0),
            'available_tools': server_status.get('total_tools', 0)
        })
    except asyncio.TimeoutError:
        return jsonify({
            'success': False,
            'error': 'Connection test timed out after 15 seconds'
        }), 408
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# WebSocket handlers for real-time features
def register_socketio_handlers(socketio):
    """Register Socket.IO event handlers for MCP client"""
    
    @socketio.on('mcp_join')
    def handle_mcp_join(data):
        """Join the MCP room for real-time updates"""
        room = 'mcp_client'
        join_room(room)
        emit('mcp_joined', {'message': 'Joined MCP client room'}, room=room)
    
    @socketio.on('mcp_leave')
    def handle_mcp_leave(data):
        """Leave the MCP room"""
        room = 'mcp_client'
        leave_room(room)
        emit('mcp_left', {'message': 'Left MCP client room'}, room=room)
    
    @socketio.on('mcp_chat_stream')
    def handle_chat_stream(data):
        """Stream chat responses with Strands agent MCP support"""
        message = data.get('message')
        use_tools = data.get('use_tools', True)
        system_prompt = data.get('system_prompt')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 32768)
        model = data.get('model', 'amazon.nova-lite-v1:0')
        room = request.sid
        
        # Update model if different
        if model and strands_agent and model != strands_agent.current_model_id:
            strands_agent.update_model(model)
        
        async def stream_response():
            try:
                # Stream using Strands agent
                async for chunk in strands_agent.stream_chat(
                    message=message,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_tools=use_tools
                ):
                    socketio.emit('mcp_chat_chunk', chunk, room=room)
                    
            except Exception as e:
                logger.error(f"Error in chat stream: {str(e)}")
                socketio.emit('mcp_chat_error', {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }, room=room)
        
        # Run async function safely
        def run_stream():
            try:
                asyncio.run(stream_response())
            except Exception as e:
                logger.error(f"Error running stream: {str(e)}")
        
        # Run in background thread
        socketio.start_background_task(run_stream)
    
    @socketio.on('mcp_connect_server')
    def handle_connect_server(data):
        """Connect to MCP server via WebSocket"""
        server_id = data.get('server_id')
        room = request.sid
        
        async def connect_async():
            try:
                connected = await strands_agent.connect_server(server_id)
                
                if connected:
                    status = strands_agent.get_server_status(server_id)
                    socketio.emit('mcp_server_connected', {
                        'server_id': server_id,
                        'status': status,
                        'timestamp': datetime.now().isoformat()
                    }, room=room)
                else:
                    socketio.emit('mcp_server_error', {
                        'server_id': server_id,
                        'error': 'Failed to connect to server',
                        'timestamp': datetime.now().isoformat()
                    }, room=room)
                    
            except Exception as e:
                socketio.emit('mcp_server_error', {
                    'server_id': server_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }, room=room)
        
        # Run async function
        def run_connect():
            try:
                asyncio.run(connect_async())
            except Exception as e:
                logger.error(f"Error connecting server: {str(e)}")
        
        socketio.start_background_task(run_connect)
    
    @socketio.on('mcp_disconnect_server')
    def handle_disconnect_server(data):
        """Disconnect from MCP server via WebSocket"""
        server_id = data.get('server_id')
        room = request.sid
        
        async def disconnect_async():
            try:
                disconnected = await strands_agent.disconnect_server(server_id)
                
                if disconnected:
                    socketio.emit('mcp_server_disconnected', {
                        'server_id': server_id,
                        'timestamp': datetime.now().isoformat()
                    }, room=room)
                else:
                    socketio.emit('mcp_server_error', {
                        'server_id': server_id,
                        'error': 'Failed to disconnect from server',
                        'timestamp': datetime.now().isoformat()
                    }, room=room)
                    
            except Exception as e:
                socketio.emit('mcp_server_error', {
                    'server_id': server_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }, room=room)
        
        # Run async function
        def run_disconnect():
            try:
                asyncio.run(disconnect_async())
            except Exception as e:
                logger.error(f"Error disconnecting server: {str(e)}")
        
        socketio.start_background_task(run_disconnect)

# No auto-initialization - servers will be connected manually via UI
def initialize_mcp_servers():
    """Initialize Strands MCP agent (servers NOT auto-connected)"""
    try:
        # Just log the status - no auto-connection
        server_status = strands_agent.get_server_status()
        logger.info(f"Strands MCP agent initialized with {server_status.get('total_servers', 0)} server configurations")
    except Exception as e:
        logger.error(f"Failed to get Strands agent status: {str(e)}")