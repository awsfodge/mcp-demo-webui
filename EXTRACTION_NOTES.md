# MCP Demo Extraction Notes

This standalone application was extracted from the Strands Web UI project on 2025-08-27.

## What Was Extracted

### Core Functionality Preserved
- ✅ Complete MCP chat interface with streaming responses
- ✅ MCP server management (add, edit, delete, connect, disconnect)
- ✅ Tool execution through connected MCP servers
- ✅ System prompt customization
- ✅ Model selection (all AWS Bedrock models)
- ✅ WebSocket real-time communication
- ✅ Theme switching (dark/light mode)
- ✅ Connection status indicators
- ✅ Agent loop visualization with thinking cards

### Files Extracted
- **Backend**: `app.py`, `config.py`, `api/mcp_routes.py`
- **Utilities**: `utils/strands_mcp_agent.py`, `utils/mcp_client.py`
- **Frontend**: `templates/index.html`, `templates/base.html`, `templates/error.html`
- **Assets**: `static/css/main.css`, `static/css/mcp-agent-loop.css`, `static/js/mcp-agent-loop.js`
- **Data**: `data/mcp_servers.json`

### What Was Removed
- ❌ Agent builder functionality
- ❌ Custom tools management
- ❌ Sample dataset features
- ❌ Database management (SQLite)
- ❌ Containerization features
- ❌ Agent pool management
- ❌ Multi-agent support
- ❌ Tool creation interface
- ❌ Redis session storage (using filesystem instead)

## Key Changes Made

1. **Simplified Navigation**: Removed links to other pages, kept only MCP demo
2. **Reduced Dependencies**: Removed Docker, testing frameworks, and unnecessary libraries
3. **Standalone Configuration**: Created minimal `config.py` with only MCP-related settings
4. **Direct Initialization**: Added singleton pattern for MCP managers in `mcp_routes.py`
5. **Simplified Templates**: Removed navigation to non-existent pages in `base.html`
6. **Focused Functionality**: All code now specifically serves the MCP demo purpose

## Directory Structure
```
mcp-demo-standalone/
├── app.py                # Minimal Flask application
├── config.py            # MCP-focused configuration
├── requirements.txt     # Minimal dependencies
├── run.sh              # Unix/Mac run script
├── run.bat             # Windows run script
├── .env.example        # Environment template
├── api/
│   └── mcp_routes.py   # MCP API endpoints
├── utils/
│   ├── __init__.py
│   ├── strands_mcp_agent.py
│   └── mcp_client.py
├── static/
│   ├── css/
│   │   ├── main.css
│   │   └── mcp-agent-loop.css
│   └── js/
│       └── mcp-agent-loop.js
├── templates/
│   ├── base.html
│   ├── index.html
│   └── error.html
└── data/
    └── mcp_servers.json
```

## Dependencies Reduced From
- Original: 40+ packages including Docker, Redis, testing frameworks
- Standalone: 12 essential packages for MCP functionality

## Quick Start
```bash
# Unix/Mac
./run.sh

# Windows
run.bat

# Or manually
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Important Notes
1. AWS credentials must be configured for Bedrock access
2. The `.env` file needs to be created from `.env.example`
3. MCP server configurations in `data/mcp_servers.json` may need path adjustments
4. Port 5000 is used by default (configurable via PORT env variable)

## Future Enhancements (Not Implemented)
- Add Docker support for easier deployment
- Implement user authentication
- Add conversation persistence to database
- Create MCP server marketplace/registry
- Add export functionality for conversations
- Implement rate limiting and usage tracking

## Testing Checklist
- [ ] Application starts without errors
- [ ] WebSocket connection establishes
- [ ] Theme switching works
- [ ] MCP servers can be added/edited/deleted
- [ ] Servers can connect/disconnect
- [ ] Chat messages send and receive responses
- [ ] Tool execution works with connected servers
- [ ] Agent loop visualization displays correctly
- [ ] System prompt can be customized
- [ ] Model selection changes take effect

This extraction preserves the core MCP demonstration functionality while removing complexity from the broader Strands agent builder platform.