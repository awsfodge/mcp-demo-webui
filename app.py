"""
MCP Demo Standalone Application
A minimal Flask app for demonstrating Model Context Protocol capabilities
"""
import os
import sys
import logging
from pathlib import Path
from flask import Flask, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_session import Session

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress verbose SocketIO logging
logging.getLogger('socketio.server').setLevel(logging.WARNING)
logging.getLogger('engineio.server').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Create Flask app
app = Flask(__name__)

# Load configuration
config = get_config()
config.init_app(app)

# Initialize extensions
CORS(app)
Session(app)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=False
)

# Import API blueprints
from api.mcp_routes import mcp_bp, register_socketio_handlers, initialize_mcp_servers

# Register blueprints
app.register_blueprint(mcp_bp, url_prefix='/api/mcp')

# Register socketio handlers
register_socketio_handlers(socketio)

# Main routes
@app.route('/')
def index():
    """Main MCP Demo interface"""
    return render_template('index.html')

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to MCP Demo'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {error}")
    return render_template('error.html', error="Internal server error"), 500

if __name__ == '__main__':
    # Initialize MCP servers on startup
    with app.app_context():
        try:
            initialize_mcp_servers()
        except Exception as e:
            logger.warning(f"Failed to initialize MCP servers on startup: {e}")
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting MCP Demo on port {port} (debug={debug})")
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug
    )
