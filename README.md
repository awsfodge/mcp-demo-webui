# MCP Demo - Model Context Protocol Standalone Application

A sophisticated standalone web application demonstrating the power of Model Context Protocol (MCP) with AWS Bedrock integration. This demo showcases how AI agents can interact with external tools and services through MCP servers, providing a complete implementation of agent-tool orchestration.

## 🌟 Features

### Core Capabilities
- 🤖 **Multi-Model AI Chat Interface** - Interactive chat with AWS Bedrock models including:
  - Amazon Nova (Lite & Pro variants)
  - Anthropic Claude (Sonnet 3.5 & Opus 3)
  - DeepSeek R1 Distilled
  - Meta Llama 3.3 Maverick
- 🔌 **Dynamic MCP Server Management** - Connect, disconnect, and manage multiple MCP servers simultaneously
- 🛠️ **Real-time Tool Execution** - Execute tools provided by MCP servers with streaming feedback
- 🎯 **Agent Loop Visualization** - Transparent display of the agent's reasoning and tool execution process
- 🌓 **Adaptive Theme Support** - Seamless dark and light mode switching
- ⚡ **WebSocket Streaming** - Real-time bidirectional communication for responsive interactions
- 💾 **Session Management** - Persistent chat history within sessions
- 📊 **Performance Monitoring** - Built-in metrics for response times and tool execution

## 📋 Prerequisites

### Required Software
- **Python 3.8+** (3.10+ recommended for optimal performance)
- **Node.js 18+** and npm (for npx-based MCP servers)
- **AWS Account** with:
  - Bedrock service access enabled
  - Appropriate IAM permissions for Bedrock model invocation
- **AWS CLI** configured with valid credentials

### AWS Bedrock Setup
1. Enable Bedrock in your AWS account (if not already enabled)
2. Request access to required models through the AWS Console:
   - Navigate to Bedrock → Model access
   - Request access to Nova, Claude, DeepSeek, and Llama models
3. Ensure your IAM user/role has the following permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream",
           "bedrock:ListFoundationModels"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

## 🚀 Installation

### 1. Clone or Extract Repository
```bash
git clone <repository-url>  # Or extract the provided archive
cd mcp-demo-standalone
```

### 2. Python Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
# On Windows PowerShell:
venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import flask; import boto3; print('Dependencies installed successfully')"
```

### 4. Environment Configuration
```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your configuration
# Use your preferred editor: vim, nano, code, etc.
nano .env
```

### 5. AWS Credentials Setup
Choose one of the following methods:

#### Option A: AWS CLI Configuration
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (e.g., us-east-1)
# Enter output format (json recommended)
```

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

#### Option C: AWS Profile
```bash
export AWS_PROFILE=your-profile-name
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# === Flask Configuration ===
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True                        # Set to False in production
FLASK_ENV=development            # Options: development, production
HOST=0.0.0.0                     # Bind address
PORT=5000                        # Port number

# === AWS Configuration ===
AWS_DEFAULT_REGION=us-east-1    # Primary AWS region for Bedrock
AWS_PROFILE=default              # AWS profile name (optional)
AWS_RETRY_ATTEMPTS=3             # Number of retry attempts for AWS calls
AWS_RETRY_MODE=adaptive          # Retry mode: legacy, standard, adaptive

# === Model Configuration ===
DEFAULT_MODEL_ID=amazon.nova-lite-v1:0  # Default AI model
DEFAULT_TEMPERATURE=0.7                  # Model temperature (0.0-1.0)
DEFAULT_MAX_TOKENS=9500                 # Maximum response tokens
DEFAULT_TOP_P=0.95                       # Nucleus sampling parameter
DEFAULT_TOP_K=250                        # Top-k sampling parameter

# === MCP Configuration ===
MCP_CONNECTION_TIMEOUT=30.0      # Timeout for MCP server connections (seconds)
MCP_TOOL_TIMEOUT=60.0            # Timeout for tool execution (seconds)
MCP_MAX_RETRIES=3                # Maximum retry attempts for failed connections
MCP_HEARTBEAT_INTERVAL=10.0      # Heartbeat interval for connection monitoring

# === System Prompt ===
DEFAULT_SYSTEM_PROMPT=You are a helpful AI assistant with access to MCP tools. Use available tools to help users accomplish their tasks efficiently.

# === Logging Configuration ===
LOG_LEVEL=INFO                   # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE=app.log                 # Log file path (optional)
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# === Security Configuration ===
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000  # CORS origins
SESSION_COOKIE_SECURE=False      # Set to True with HTTPS
SESSION_COOKIE_HTTPONLY=True     # Prevent JS access to session cookies
SESSION_COOKIE_SAMESITE=Lax      # CSRF protection
```

### MCP Server Configuration

The application integrates with various MCP servers to provide extended functionality. Below are configuration examples for popular MCP servers:

#### AWS Cloud Control API (CCAPI) MCP Server

Standard installation:
```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Windows installation:
```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.ccapi-mcp-server@latest",
        "awslabs.ccapi-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

#### AWS DynamoDB MCP Server

Standard installation:
```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "DDB-MCP-READONLY": "true",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Windows installation:
```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.dynamodb-mcp-server@latest",
        "awslabs.dynamodb-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

#### PostgreSQL MCP Server

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://localhost/mydb"
      ]
    }
  }
}
```

## 🏃 Running the Application

### Development Mode
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the Flask application
python app.py

# The application will be available at:
# http://localhost:5000
```

### Production Mode
```bash
# Using Gunicorn (recommended for production)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app

# Using uWSGI (alternative)
pip install uwsgi
uwsgi --http :5000 --module app:app --processes 4
```

### Docker Deployment (Optional)
```dockerfile
# Dockerfile example
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
# Build and run
docker build -t mcp-demo .
docker run -p 5000:5000 --env-file .env mcp-demo
```

## 📚 Architecture Overview

### Application Structure
```
mcp-demo-standalone/
├── app.py                      # Flask application entry point & WebSocket handlers
├── config.py                   # Configuration management and environment loading
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
│
├── api/                       # API endpoints
│   └── mcp_routes.py         # MCP-specific REST API routes
│
├── utils/                     # Core utilities
│   ├── strands_mcp_agent.py # MCP agent implementation with tool orchestration
│   └── mcp_client.py        # MCP client manager for server connections
│
├── static/                    # Frontend assets
│   ├── css/
│   │   └── style.css        # Main stylesheet with theme support
│   ├── js/
│   │   ├── app.js          # Main application logic
│   │   ├── chat.js         # Chat interface management
│   │   ├── websocket.js    # WebSocket communication
│   │   └── mcp-manager.js  # MCP server management
│   └── images/             # Icons and images
│
├── templates/               # HTML templates
│   ├── index.html          # Main application page
│   └── components/         # Reusable UI components
│
└── data/                    # Application data
    ├── mcp_servers.json    # MCP server configurations
    └── logs/               # Application logs (created at runtime)
```

### Component Interactions
```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Browser   │────▶│  Flask App   │────▶│  AWS Bedrock  │
│  (Frontend) │◀────│  (Backend)   │◀────│   (AI Models) │
└─────────────┘     └──────────────┘     └───────────────┘
       │                    │                      
       │                    ▼                      
       │            ┌──────────────┐              
       └───────────▶│  WebSocket   │              
                    │   Handler    │              
                    └──────────────┘              
                           │                       
                           ▼                       
                    ┌──────────────┐              
                    │  MCP Client  │              
                    │   Manager    │              
                    └──────────────┘              
                           │                       
                    ┌──────┴──────┐               
                    ▼             ▼               
              ┌──────────┐  ┌──────────┐         
              │   MCP    │  │   MCP    │         
              │ Server 1 │  │ Server 2 │         
              └──────────┘  └──────────┘         
```

## 🎯 Usage Guide

### Basic Chat Operations

#### Starting a Conversation
1. Open the application in your browser
2. Select your preferred AI model from the dropdown
3. Adjust temperature and max tokens if needed
4. Type your message and press Enter or click Send

#### Model Selection Tips
- **Nova Lite**: Fast responses, good for simple queries
- **Nova Pro**: Better reasoning, suitable for complex tasks
- **Claude Sonnet**: Excellent for coding and analysis
- **Claude Opus**: Most capable, best for challenging problems
- **DeepSeek R1**: Strong reasoning capabilities
- **Llama Maverick**: Good balance of speed and capability

### Working with MCP Tools

#### Connecting to MCP Servers
1. Navigate to the MCP Servers section
2. Click "Connect" on desired server cards
3. Wait for connection confirmation
4. Available tools will appear in the tools panel

#### Using Tools in Conversations
1. Enable tools with the toggle button (🛠️)
2. Ask questions that require tool usage
3. Examples:
   - "Search for recent news about AI"
   - "Read the contents of config.py"
   - "Store this information for later: [data]"

#### Agent Loop Visualization
- Watch real-time tool execution in the agent loop panel
- See the agent's reasoning process
- Monitor tool inputs and outputs
- Track execution time and status

### Advanced Features

#### Custom MCP Server Integration
1. Click "Add MCP Server" button
2. Configure server details:
   ```json
   {
     "name": "My Custom Server",
     "command": ["python3", "my_server.py"],
     "args": ["--port", "8080"],
     "env_vars": {
       "API_KEY": "my-api-key"
     }
   }
   ```
3. Test connection before saving
4. Enable auto-connect for frequently used servers

#### Session Management
- Sessions persist during browser session
- Chat history is maintained per session
- Clear chat with the Clear button
- Export chat history (coming soon)

#### Keyboard Shortcuts
- `Enter`: Send message
- `Shift+Enter`: New line in message
- `Ctrl+/`: Toggle tools
- `Ctrl+K`: Clear chat
- `Ctrl+D`: Toggle dark mode

## 🔧 Available MCP Servers

### AWS MCP Servers

#### 1. AWS Cloud Control API (CCAPI) MCP Server
```bash
uvx awslabs.ccapi-mcp-server@latest
```
**Capabilities**: Unified interface to AWS services through Cloud Control API
**Use Cases**: 
- Creating and managing AWS resources
- Infrastructure provisioning and management
- Automated deployment workflows
- Resource tagging and compliance

**Configuration Options**:
- `AWS_PROFILE`: AWS named profile to use
- `DEFAULT_TAGS`: Enable default tagging for resources
- `SECURITY_SCANNING`: Enable security scanning features
- `FASTMCP_LOG_LEVEL`: Control logging verbosity

#### 2. AWS DynamoDB MCP Server
```bash
uvx awslabs.dynamodb-mcp-server@latest
```
**Capabilities**: Direct interaction with DynamoDB tables
**Use Cases**: 
- Database queries and operations
- Data migration and backup
- Table management and monitoring
- Item-level CRUD operations

**Configuration Options**:
- `DDB-MCP-READONLY`: Set to "true" for read-only access
- `AWS_PROFILE`: AWS named profile to use
- `AWS_REGION`: AWS region for DynamoDB operations
- `FASTMCP_LOG_LEVEL`: Control logging verbosity

### Database MCP Servers

#### 3. PostgreSQL Server
```bash
npx -y @modelcontextprotocol/server-postgres postgresql://localhost/mydb
```
**Capabilities**: Full PostgreSQL database access
**Use Cases**: 
- SQL query execution
- Database schema management
- Data analysis and reporting
- Transaction management

**Connection String Format**:
```
postgresql://[user[:password]@][hostname][:port][/database][?param1=value1&...]
```

### Custom Server Development

#### Basic Python MCP Server Template
```python
# my_mcp_server.py
import asyncio
from mcp import Server, Tool, Resource

server = Server("my-server")

@server.tool()
async def my_tool(param: str) -> str:
    """Tool description"""
    return f"Processed: {param}"

@server.resource()
async def my_resource(path: str) -> str:
    """Resource description"""
    return f"Resource at {path}"

if __name__ == "__main__":
    asyncio.run(server.run())
```

#### Server Configuration
```json
{
  "my-custom-server": {
    "name": "My Custom Server",
    "command": ["python3", "my_mcp_server.py"],
    "args": [],
    "env_vars": {},
    "enabled": true
  }
}
```

## 🐛 Troubleshooting

### Common Issues and Solutions

#### AWS Bedrock Connection Issues
```
Error: Could not connect to Bedrock endpoint
```
**Solutions**:
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check region availability: Ensure Bedrock is available in your region
3. Verify model access: Check model access in AWS Console
4. Check IAM permissions: Ensure proper Bedrock permissions

#### MCP Server Connection Failures
```
Error: Failed to connect to MCP server
```
**Solutions**:
1. Check server command exists: `which npx` or `which python3`
2. Verify Node.js installation: `node --version`
3. Test server manually: Run command directly in terminal
4. Check environment variables in server configuration
5. Review server logs in browser console

#### WebSocket Connection Issues
```
Error: WebSocket connection failed
```
**Solutions**:
1. Check firewall settings for port 5000
2. Disable browser extensions (ad blockers, privacy tools)
3. Try different browser
4. Check for proxy settings
5. Verify Flask is running: `curl http://localhost:5000`

#### Tool Execution Timeouts
```
Error: Tool execution timed out
```
**Solutions**:
1. Increase `MCP_TOOL_TIMEOUT` in .env
2. Check server resource usage
3. Optimize tool implementation
4. Break complex operations into smaller steps

### Debugging Tips

#### Enable Debug Logging
```python
# In .env
DEBUG=True
LOG_LEVEL=DEBUG
```

#### Check Application Logs
```bash
# Flask logs
tail -f app.log

# Browser console
# Open Developer Tools → Console
```

#### Monitor WebSocket Traffic
```javascript
// In browser console
window.ws.addEventListener('message', (event) => {
  console.log('WebSocket message:', event.data);
});
```

#### Test MCP Server Directly
```bash
# Test server connection
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}' | \
  npx -y @modelcontextprotocol/server-memory
```

## 🔒 Security Best Practices

### Production Deployment

1. **Environment Variables**
   - Never commit .env files to version control
   - Use secrets management services (AWS Secrets Manager, HashiCorp Vault)
   - Rotate keys regularly

2. **Authentication & Authorization**
   - Implement user authentication (OAuth, SAML)
   - Add rate limiting to prevent abuse
   - Use HTTPS in production

3. **MCP Server Security**
   - Restrict filesystem access to specific directories
   - Validate all tool inputs
   - Implement sandboxing for untrusted servers
   - Monitor tool execution logs

4. **AWS Security**
   - Use IAM roles instead of access keys when possible
   - Apply least privilege principle
   - Enable CloudTrail for audit logging
   - Use VPC endpoints for Bedrock access

5. **Input Validation**
   - Sanitize user inputs
   - Implement content filtering
   - Set reasonable message length limits
   - Validate file paths and URLs

### Security Checklist
- [ ] Change default SECRET_KEY
- [ ] Disable DEBUG in production
- [ ] Configure HTTPS/TLS
- [ ] Implement authentication
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Enable security headers
- [ ] Regular dependency updates
- [ ] Implement logging and monitoring
- [ ] Set up backup and recovery

## 🚀 Performance Optimization

### Backend Optimizations

1. **Connection Pooling**
```python
# Reuse AWS client connections
bedrock_client = boto3.client(
    'bedrock-runtime',
    config=Config(
        max_pool_connections=50
    )
)
```

2. **Caching Strategy**
```python
# Implement response caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_response(prompt_hash):
    return cached_responses.get(prompt_hash)
```

3. **Async Operations**
```python
# Use async for I/O operations
async def process_tools_async(tools):
    tasks = [process_tool(tool) for tool in tools]
    return await asyncio.gather(*tasks)
```

### Frontend Optimizations

1. **Lazy Loading**
   - Load MCP servers on demand
   - Implement virtual scrolling for chat history
   - Defer non-critical JavaScript

2. **WebSocket Management**
   - Implement reconnection logic
   - Buffer messages during disconnection
   - Use compression for large payloads

3. **Resource Optimization**
   - Minify CSS and JavaScript
   - Enable gzip compression
   - Implement browser caching

## 📊 Monitoring and Logging

### Application Metrics
- Response time tracking
- Tool execution duration
- Model usage statistics
- Error rate monitoring
- Active connection count

### Logging Configuration
```python
# config.py
LOGGING = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'default',
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
}
```

### Monitoring Tools Integration
- **CloudWatch**: AWS metrics and logs
- **Prometheus**: Time-series metrics
- **Grafana**: Visualization dashboards
- **Sentry**: Error tracking and monitoring

## 🔄 API Documentation

### REST Endpoints

#### GET /api/models
Returns available AI models
```json
{
  "models": [
    {
      "id": "amazon.nova-lite-v1:0",
      "name": "Amazon Nova Lite",
      "category": "nova"
    }
  ]
}
```

#### POST /api/mcp/connect
Connect to an MCP server
```json
{
  "server_id": "filesystem",
  "config": {
    "args": ["/path/to/directory"]
  }
}
```

#### POST /api/mcp/disconnect
Disconnect from an MCP server
```json
{
  "server_id": "filesystem"
}
```

#### GET /api/mcp/tools
Get available tools from connected servers
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read contents of a file",
      "server_id": "filesystem"
    }
  ]
}
```

### WebSocket Events

#### Client → Server

**message**
```json
{
  "type": "message",
  "content": "User message",
  "model_id": "amazon.nova-lite-v1:0",
  "use_tools": true
}
```

**tool_response**
```json
{
  "type": "tool_response",
  "tool_id": "call_123",
  "result": "Tool execution result"
}
```

#### Server → Client

**response**
```json
{
  "type": "response",
  "content": "AI response",
  "tool_calls": []
}
```

**tool_request**
```json
{
  "type": "tool_request",
  "tool_name": "read_file",
  "tool_args": {"path": "/file.txt"},
  "tool_id": "call_123"
}
```

**error**
```json
{
  "type": "error",
  "message": "Error description"
}
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Run tests:
   ```bash
   pytest tests/
   ```
5. Submit a pull request

### Code Style
- Follow PEP 8 for Python code
- Use ESLint for JavaScript
- Add type hints where applicable
- Write comprehensive docstrings

### Testing Guidelines
- Write unit tests for new features
- Maintain >80% code coverage
- Test edge cases and error handling
- Include integration tests for MCP servers

## 📝 License

This project is provided as-is for demonstration purposes. See LICENSE file for details.

## 🆘 Support

### Getting Help
- **Documentation**: Review this README thoroughly
- **Logs**: Check application and browser console logs
- **Issues**: Search existing issues before creating new ones
- **Community**: Join our Discord server (coming soon)

### Reporting Issues
When reporting issues, include:
1. Environment details (OS, Python version, Node version)
2. Error messages and stack traces
3. Steps to reproduce
4. Relevant configuration files (sanitized)
5. Browser console logs

### Contact
- **GitHub Issues**: [Report bugs and request features]
- **Email**: support@example.com
- **Documentation**: [Online documentation]

## 🎉 Acknowledgments

- Built on the Model Context Protocol specification
- Powered by AWS Bedrock and various AI models
- Uses Flask, Socket.IO, and modern web technologies
- Inspired by the Strands Agent Builder project

---

**Version**: 1.0.0  
**Last Updated**: January 2025  
**Status**: Active Development

For the latest updates and announcements, check the repository's releases page.