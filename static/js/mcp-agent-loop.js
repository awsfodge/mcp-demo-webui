/**
 * Enhanced MCP Client with Agent Loop Visualization
 * Displays distinct UI components for each phase of the agent loop
 */

// Global state
let useTools = true;
let messageCount = 0;
let toolCallCount = 0;
let activeServers = 0;
let isStreaming = false;
let currentStreamContainer = null;
let currentReasoningBlock = null;
let currentToolSelectionBlock = null;
let currentToolExecutionBlock = null;
let currentResponseBlock = null;
let currentToolExecutionPopup = null;
let streamBuffer = '';
let systemPrompt = 'You are a helpful AI assistant with access to MCP tools.';
let serverConfigs = {}; // Store server configurations
let currentModel = 'amazon.nova-lite-v1:0'; // Current selected model
let strandsToolsConfig = {}; // Store Strands tools configuration
let pendingToolChanges = {}; // Track pending tool changes

// New state for frontend parsing
let fullMessageBuffer = ''; // Accumulates the complete message
let currentParseMode = 'normal'; // 'normal', 'thinking'
let thinkingBuffer = ''; // Accumulates thinking content
let responseBuffer = ''; // Accumulates response content

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    try {
        initializeMCPClient();
        loadServers();
        loadSystemPrompt();
        loadCurrentModel();
        loadStrandsTools();
        setupEventListeners();
        joinMCPRoom();
        updateStats();
    } catch (error) {
        console.error('Initialization error:', error);
    }
});

function initializeMCPClient() {
    fetch('/api/mcp/test')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.strands_connected) {
                updateConnectionStatus('connected');
            } else {
                updateConnectionStatus('error');
                showToast('Connection failed. Check configuration.', 'warning');
            }
        })
        .catch(error => {
            console.error('Connection test failed:', error);
            updateConnectionStatus('error');
        });
}

function loadCurrentModel() {
    fetch('/api/mcp/model')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.model) {
                currentModel = data.model;
                const modelSelector = document.getElementById('modelSelector');
                if (modelSelector) {
                    modelSelector.value = currentModel;
                }
            }
        })
        .catch(error => {
            console.error('Failed to load current model:', error);
        });
}

function loadSystemPrompt() {
    fetch('/api/mcp/system-prompt')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.system_prompt) {
                systemPrompt = data.system_prompt;
                document.getElementById('systemPromptText').textContent = systemPrompt.trim();
                // Update modal input if it exists
                const modalInput = document.getElementById('modalSystemPromptInput');
                if (modalInput) {
                    modalInput.value = systemPrompt;
                }
            }
        })
        .catch(error => {
            console.error('Failed to load system prompt:', error);
        });
}

// Strands Tools Functions
function loadStrandsTools() {
    fetch('/api/mcp/strands-tools')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.tools) {
                strandsToolsConfig = data.tools;
                updateStrandsToolsCount();
            }
        })
        .catch(error => {
            console.error('Failed to load Strands tools:', error);
        });
}

function updateStrandsToolsCount() {
    const badge = document.getElementById('strandsToolsCount');
    if (badge && strandsToolsConfig) {
        badge.textContent = strandsToolsConfig.total_enabled || 0;
    }
}

function showStrandsToolsModal() {
    const modal = document.getElementById('strandsToolsModal');
    if (modal) {
        modal.style.display = 'flex';
        loadStrandsToolsList();
    }
}

function hideStrandsToolsModal() {
    const modal = document.getElementById('strandsToolsModal');
    if (modal) {
        modal.style.display = 'none';
        // Reset pending changes
        pendingToolChanges = {};
    }
}

function loadStrandsToolsList() {
    fetch('/api/mcp/strands-tools')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.tools) {
                strandsToolsConfig = data.tools;
                renderStrandsToolsList();
            }
        })
        .catch(error => {
            console.error('Failed to load tools list:', error);
            const container = document.getElementById('strandsToolsList');
            if (container) {
                container.innerHTML = '<div class="alert alert-error">Failed to load tools</div>';
            }
        });
}

function renderStrandsToolsList() {
    const container = document.getElementById('strandsToolsList');
    if (!container || !strandsToolsConfig.categories) return;
    
    let html = '';
    let totalEnabled = 0;
    
    for (const [category, categoryInfo] of Object.entries(strandsToolsConfig.categories)) {
        const enabledCount = categoryInfo.enabled_count || 0;
        totalEnabled += enabledCount;
        
        html += `
            <div class="tool-category" data-category="${category}">
                <div class="tool-category-header" onclick="toggleCategoryCollapse('${category}')">
                    <div class="category-title">
                        <i class="bi bi-chevron-down" id="category-icon-${category.replace(/ /g, '-')}"></i>
                        ${category}
                    </div>
                    <div class="category-count">
                        ${enabledCount} / ${Object.keys(categoryInfo.tools || {}).length} enabled
                    </div>
                </div>
                <div class="tool-category-tools" id="category-tools-${category.replace(/ /g, '-')}" style="display: block;">
        `;
        
        for (const [toolId, toolInfo] of Object.entries(categoryInfo.tools || {})) {
            const toolKey = `${category}:${toolId}`;
            const isEnabled = pendingToolChanges[toolKey] !== undefined ? 
                             pendingToolChanges[toolKey] : 
                             toolInfo.enabled;
            
            html += `
                <div class="tool-item" data-tool="${toolId}">
                    <input type="checkbox" 
                           class="tool-checkbox" 
                           id="tool-${toolId}"
                           data-category="${category}"
                           data-tool-id="${toolId}"
                           ${isEnabled ? 'checked' : ''}
                           onchange="onToolToggle('${category}', '${toolId}', this.checked)">
                    <div class="tool-info">
                        <div class="tool-name">
                            <label for="tool-${toolId}">${toolInfo.name}</label>
                            ${toolInfo.loaded ? '<span class="tool-badge loaded">LOADED</span>' : ''}
                            ${toolInfo.requires_extra ? `<span class="tool-badge requires-extra" title="Requires: pip install 'strands-agents-tools[${toolInfo.requires_extra}]'">EXTRA</span>` : ''}
                        </div>
                        <div class="tool-description">
                            ${toolInfo.description}
                        </div>
                    </div>
                </div>
            `;
        }
        
        html += `
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    // Update enabled count
    const countElement = document.getElementById('enabledToolsCount');
    if (countElement) {
        const enabledCount = Object.values(pendingToolChanges).filter(v => v).length || totalEnabled;
        countElement.textContent = enabledCount;
    }
}

function toggleCategoryCollapse(category) {
    const toolsDiv = document.getElementById(`category-tools-${category.replace(/ /g, '-')}`);
    const icon = document.getElementById(`category-icon-${category.replace(/ /g, '-')}`);
    
    if (toolsDiv) {
        if (toolsDiv.style.display === 'none') {
            toolsDiv.style.display = 'block';
            if (icon) icon.className = 'bi bi-chevron-down';
        } else {
            toolsDiv.style.display = 'none';
            if (icon) icon.className = 'bi bi-chevron-right';
        }
    }
}

function onToolToggle(category, toolId, enabled) {
    const toolKey = `${category}:${toolId}`;
    pendingToolChanges[toolKey] = enabled;
    
    // Update enabled count
    const countElement = document.getElementById('enabledToolsCount');
    if (countElement) {
        let enabledCount = 0;
        
        // Count from existing config and apply pending changes
        for (const [cat, catInfo] of Object.entries(strandsToolsConfig.categories || {})) {
            for (const [tid, tInfo] of Object.entries(catInfo.tools || {})) {
                const key = `${cat}:${tid}`;
                if (pendingToolChanges[key] !== undefined) {
                    if (pendingToolChanges[key]) enabledCount++;
                } else if (tInfo.enabled) {
                    enabledCount++;
                }
            }
        }
        
        countElement.textContent = enabledCount;
    }
}

function toggleAllTools(enable) {
    const checkboxes = document.querySelectorAll('.tool-checkbox');
    checkboxes.forEach(checkbox => {
        const category = checkbox.dataset.category;
        const toolId = checkbox.dataset.toolId;
        if (category && toolId) {
            checkbox.checked = enable;
            onToolToggle(category, toolId, enable);
        }
    });
}

function filterStrandsTools() {
    const searchInput = document.getElementById('toolSearchInput');
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    
    const toolItems = document.querySelectorAll('.tool-item');
    toolItems.forEach(item => {
        const toolName = item.querySelector('.tool-name')?.textContent.toLowerCase() || '';
        const toolDesc = item.querySelector('.tool-description')?.textContent.toLowerCase() || '';
        
        if (toolName.includes(searchTerm) || toolDesc.includes(searchTerm)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

function saveStrandsToolsConfig() {
    if (Object.keys(pendingToolChanges).length === 0) {
        showToast('No changes to save', 'info');
        hideStrandsToolsModal();
        return;
    }
    
    fetch('/api/mcp/strands-tools/bulk-update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            updates: pendingToolChanges
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Tools configuration saved successfully', 'success');
            loadStrandsTools(); // Reload to get updated counts
            hideStrandsToolsModal();
        } else {
            showToast('Failed to save configuration: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error saving tools config:', error);
        showToast('Failed to save configuration', 'error');
    });
}

function setupEventListeners() {
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
        
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
}

function joinMCPRoom() {
    if (typeof socket !== 'undefined') {
        socket.emit('mcp_join', {});
        
        socket.on('mcp_server_connected', handleServerConnected);
        socket.on('mcp_server_disconnected', handleServerDisconnected);
        socket.on('mcp_server_error', handleServerError);
        socket.on('mcp_chat_chunk', handleChatChunk);
        socket.on('mcp_chat_error', handleChatError);
    }
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message || isStreaming) return;
    
    // Add user message
    addUserMessage(message);
    
    // Clear input
    input.value = '';
    input.style.height = 'auto';
    
    // Update stats
    messageCount++;
    updateStats();
    
    // Start streaming
    isStreaming = true;
    const sendButton = document.getElementById('sendButton');
    if (sendButton) sendButton.disabled = true;
    
    // Don't create agent response container yet - wait for actual response
    // It will be created when we receive text_delta events
    currentStreamContainer = null;
    
    // Reset state
    streamBuffer = '';
    fullMessageBuffer = '';
    currentParseMode = 'normal';
    thinkingBuffer = '';
    responseBuffer = '';
    currentReasoningBlock = null;
    currentToolSelectionBlock = null;
    currentToolExecutionBlock = null;
    currentResponseBlock = null;
    
    // Send via WebSocket
    if (typeof socket !== 'undefined') {
        socket.emit('mcp_chat_stream', {
            message: message,
            use_tools: useTools,
            system_prompt: systemPrompt,
            model: currentModel
        });
    } else {
        showToast('WebSocket connection not available', 'error');
        isStreaming = false;
        if (sendButton) sendButton.disabled = false;
    }
}

function addUserMessage(content) {
    const container = document.getElementById('chatContainer');
    
    // Remove welcome message if present
    const welcome = container.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'user-message-container slide-in';
    messageDiv.innerHTML = `
        <div class="user-message">
            <div class="message-content">
                <div class="message-text">${escapeHtml(content)}</div>
            </div>
            <div class="message-avatar">
                <div class="avatar-circle user">
                    <i class="bi bi-person"></i>
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function handleTextDelta(text, container) {
    // Add text to the full message buffer
    fullMessageBuffer += text;
    
    // Process the buffer to extract thinking blocks and regular text
    processMessageBuffer(container);
}

function processMessageBuffer(container) {
    // Process based on current mode
    if (currentParseMode === 'normal') {
        // Look for start of thinking block
        const thinkingStart = fullMessageBuffer.indexOf('<thinking>');
        
        if (thinkingStart !== -1) {
            // Extract any text before the thinking tag
            const beforeThinking = fullMessageBuffer.substring(0, thinkingStart);
            
            // If there's text before thinking, add it to response
            if (beforeThinking.trim()) {
                responseBuffer += beforeThinking;
                updateResponseDisplay(responseBuffer, container);
            }
            
            // Remove processed text from buffer
            fullMessageBuffer = fullMessageBuffer.substring(thinkingStart + '<thinking>'.length);
            
            // Switch to thinking mode
            currentParseMode = 'thinking';
            thinkingBuffer = '';
            
            // Create thinking card
            if (!currentReasoningBlock) {
                currentReasoningBlock = createReasoningBlock();
                
                // If we already have a response container, insert thinking card before it
                // This ensures thinking cards always appear before responses
                if (currentStreamContainer) {
                    container.insertBefore(currentReasoningBlock, currentStreamContainer);
                } else {
                    container.appendChild(currentReasoningBlock);
                }
                container.scrollTop = container.scrollHeight;
            }
            
            // Continue processing remaining buffer
            processMessageBuffer(container);
        } else {
            // No thinking tag found - check if we might be at the end of a partial tag
            const partialTagIndex = findPartialTag(fullMessageBuffer, '<thinking>');
            
            if (partialTagIndex !== -1) {
                // We might have a partial tag at the end - wait for more text
                const safeText = fullMessageBuffer.substring(0, partialTagIndex);
                if (safeText) {
                    responseBuffer += safeText;
                    updateResponseDisplay(responseBuffer, container);
                    fullMessageBuffer = fullMessageBuffer.substring(partialTagIndex);
                }
            } else {
                // No partial tag - safe to display all text
                if (fullMessageBuffer) {
                    responseBuffer += fullMessageBuffer;
                    updateResponseDisplay(responseBuffer, container);
                    fullMessageBuffer = '';
                }
            }
        }
    } else if (currentParseMode === 'thinking') {
        // Look for end of thinking block
        const thinkingEnd = fullMessageBuffer.indexOf('</thinking>');
        
        if (thinkingEnd !== -1) {
            // Extract thinking content
            const thinkingContent = fullMessageBuffer.substring(0, thinkingEnd);
            thinkingBuffer += thinkingContent;
            
            // Update thinking card with final content
            if (currentReasoningBlock) {
                updateThinkingCard(thinkingBuffer, true);
            }
            
            // Remove processed text from buffer
            fullMessageBuffer = fullMessageBuffer.substring(thinkingEnd + '</thinking>'.length);
            
            // Switch back to normal mode
            currentParseMode = 'normal';
            thinkingBuffer = '';
            
            // Continue processing remaining buffer
            processMessageBuffer(container);
        } else {
            // No end tag yet - check for partial tag
            const partialTagIndex = findPartialTag(fullMessageBuffer, '</thinking>');
            
            if (partialTagIndex !== -1) {
                // Partial end tag - display content up to partial tag
                const safeContent = fullMessageBuffer.substring(0, partialTagIndex);
                thinkingBuffer += safeContent;
                updateThinkingCard(thinkingBuffer, false);
                fullMessageBuffer = fullMessageBuffer.substring(partialTagIndex);
            } else {
                // No partial tag - display all accumulated thinking content
                thinkingBuffer += fullMessageBuffer;
                updateThinkingCard(thinkingBuffer, false);
                fullMessageBuffer = '';
            }
        }
    }
}

function findPartialTag(text, tag) {
    // Check if the end of the text could be the start of the tag
    for (let i = 1; i < tag.length; i++) {
        if (text.endsWith(tag.substring(0, i))) {
            return text.length - i;
        }
    }
    return -1;
}

function updateThinkingCard(content, isComplete) {
    if (!currentReasoningBlock) return;
    
    const contentEl = currentReasoningBlock.querySelector('.reasoning-content');
    const dots = currentReasoningBlock.querySelector('.thinking-dots');
    const status = currentReasoningBlock.querySelector('.thinking-status');
    
    if (dots && dots.style.display !== 'none') {
        dots.style.display = 'none';
    }
    
    if (contentEl) {
        contentEl.textContent = content;
    }
    
    if (isComplete) {
        currentReasoningBlock.classList.add('complete');
        
        // Store reference for timeout
        const blockToCollapse = currentReasoningBlock;
        
        // Auto-collapse after 5 seconds (increased from 3 for better readability)
        setTimeout(() => {
            if (blockToCollapse) {
                blockToCollapse.classList.add('collapsed');
            }
        }, 5000);
        
        currentReasoningBlock = null;
    } else {
        // Only scroll content if not complete (still updating)
        const cardContent = currentReasoningBlock?.querySelector('.thinking-card-content');
        if (cardContent) {
            cardContent.scrollTop = cardContent.scrollHeight;
        }
    }
}

function updateResponseDisplay(content, container) {
    // Ensure we have an agent response container
    if (!currentStreamContainer) {
        currentStreamContainer = createAgentResponseContainer();
    }
    
    const phasesContainer = currentStreamContainer.querySelector('.agent-loop-phases');
    
    // Ensure we have a response block
    if (!currentResponseBlock) {
        currentResponseBlock = createResponseBlock();
        phasesContainer.appendChild(currentResponseBlock);
        
        const statusElement = currentStreamContainer.querySelector('.agent-status');
        if (statusElement) {
            statusElement.innerHTML = '<i class="bi bi-pencil"></i> Responding...';
        }
    }
    
    // Update response content
    const responseContent = currentResponseBlock.querySelector('.response-text');
    if (responseContent) {
        // Clean the content - remove any remaining thinking tags that might have slipped through
        const cleanContent = content.replace(/<thinking>[\s\S]*?<\/thinking>/g, '').trim();
        responseContent.innerHTML = parseMarkdown(cleanContent);
    }
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function createAgentResponseContainer() {
    const container = document.getElementById('chatContainer');
    
    const responseContainer = document.createElement('div');
    responseContainer.className = 'agent-response-container slide-in';
    responseContainer.innerHTML = `
        <div class="agent-response-header">
            <div class="agent-avatar">
                <div class="avatar-circle assistant">
                    <i class="bi bi-cpu"></i>
                </div>
            </div>
            <div class="agent-info">
                <span class="agent-name">ROAS Agent</span>
                <span class="agent-status">
                    <span class="typing-dots">
                        <span></span><span></span><span></span>
                    </span>
                </span>
            </div>
        </div>
        <div class="agent-loop-phases">
            <!-- Agent loop phases will be added here -->
        </div>
    `;
    
    container.appendChild(responseContainer);
    container.scrollTop = container.scrollHeight;
    
    return responseContainer;
}

function handleChatChunk(data) {
    const container = document.getElementById('chatContainer');
    
    // Log all events for debugging
    console.log('MCP Event:', data.type, data);
    
    switch (data.type) {
        case 'text_delta':
            // Handle raw text stream with thinking tag detection
            handleTextDelta(data.text, container);
            break;
            
        // Removed old reasoning_text and reasoning_end cases - now handled by frontend parser
            
        case 'tool_selection':
            // Create a tool selection indicator in the chat
            const toolSelDiv = document.createElement('div');
            toolSelDiv.className = 'tool-indicator slide-in';
            toolSelDiv.innerHTML = `
                <div class="tool-indicator-content">
                    <i class="bi bi-tools"></i>
                    <span>${data.text || 'Selecting tool...'}</span>
                </div>
            `;
            // Insert before response container if it exists
            if (currentStreamContainer) {
                container.insertBefore(toolSelDiv, currentStreamContainer);
            } else {
                container.appendChild(toolSelDiv);
            }
            container.scrollTop = container.scrollHeight;
            break;
            
        case 'tool_execution':
            console.log('Tool execution event:', data);
            
            // Create a tool execution card in the chat
            const toolCard = document.createElement('div');
            toolCard.className = 'tool-execution-card slide-in';
            toolCard.innerHTML = `
                <div class="tool-card-header">
                    <div class="tool-card-icon">
                        <i class="bi bi-gear-fill spin"></i>
                    </div>
                    <div class="tool-card-info">
                        <div class="tool-card-title">Executing Tool</div>
                        <div class="tool-card-name">${data.tool_name || 'Unknown Tool'}</div>
                    </div>
                </div>
                ${data.input ? `
                <div class="tool-card-params">
                    <pre>${JSON.stringify(data.input, null, 2)}</pre>
                </div>
                ` : ''}
            `;
            // Insert before response container if it exists
            if (currentStreamContainer) {
                container.insertBefore(toolCard, currentStreamContainer);
            } else {
                container.appendChild(toolCard);
            }
            currentToolExecutionBlock = toolCard;
            
            // Show tool execution popup
            currentToolExecutionPopup = createToolExecutionPopup(data.tool_name || 'Tool');
            
            toolCallCount++;
            updateStats();
            container.scrollTop = container.scrollHeight;
            break;
            
        case 'tool_result':
            console.log('Tool result event:', data);
            
            if (currentToolExecutionBlock) {
                // Update the tool card to show it's complete
                const icon = currentToolExecutionBlock.querySelector('.tool-card-icon i');
                if (icon) {
                    icon.className = 'bi bi-check-circle-fill';
                }
                
                // Add result to the card
                const resultDiv = document.createElement('div');
                resultDiv.className = 'tool-card-result';
                resultDiv.innerHTML = `
                    <div class="result-label">Result:</div>
                    <pre>${formatToolResult(data.content)}</pre>
                `;
                currentToolExecutionBlock.appendChild(resultDiv);
            }
            
            // Update tool execution popup to show completion
            if (currentToolExecutionPopup) {
                updateToolExecutionPopup('complete', 'Tool completed');
            }
            break;
            
        // text_delta case is now at the top, handling all text parsing
            
        case 'message_complete':
            // Process any remaining buffer content
            if (fullMessageBuffer) {
                processMessageBuffer(container);
            }
            
            // Mark thinking card as complete if it exists
            if (currentReasoningBlock) {
                updateThinkingCard(thinkingBuffer, true);
            }
            
            // Update agent response status if it exists
            if (currentStreamContainer) {
                const statusElement = currentStreamContainer.querySelector('.agent-status');
                if (statusElement) {
                    statusElement.innerHTML = '<i class="bi bi-check-circle text-success"></i> Complete';
                    setTimeout(() => {
                        statusElement.innerHTML = `<span class="text-tertiary">${formatTime(new Date())}</span>`;
                    }, 2000);
                }
                
                const phasesContainer = currentStreamContainer.querySelector('.agent-loop-phases');
                const allBlocks = phasesContainer.querySelectorAll('.agent-phase-block');
                allBlocks.forEach(block => block.classList.add('complete'));
            }
            
            // Remove any remaining tool execution popup
            removeToolExecutionPopup();
            
            // Re-enable send button
            isStreaming = false;
            const sendBtn = document.getElementById('sendButton');
            if (sendBtn) sendBtn.disabled = false;
            
            // Reset all current tracking variables
            currentStreamContainer = null;
            currentReasoningBlock = null;
            currentToolExecutionBlock = null;
            currentResponseBlock = null;
            streamBuffer = '';
            fullMessageBuffer = '';
            currentParseMode = 'normal';
            thinkingBuffer = '';
            responseBuffer = '';
            
            // Update stats
            messageCount++;
            updateStats();
            break;
            
        case 'error':
            handleChatError(data);
            break;
    }
}

function createReasoningBlock() {
    const block = document.createElement('div');
    block.className = 'thinking-card animate-in';
    block.innerHTML = `
        <div class="thinking-card-header">
            <div class="thinking-card-icon">
                <i class="bi bi-tools"></i>
                <div class="thinking-pulse"></div>
            </div>
            <div class="thinking-card-title">
                <span class="thinking-label">Tool Use</span>
            </div>
            <button class="thinking-toggle" onclick="toggleThinkingCard(this)">
                <i class="bi bi-chevron-up"></i>
            </button>
        </div>
        <div class="thinking-card-progress">
            <div class="thinking-progress-bar"></div>
        </div>
        <div class="thinking-card-content">
            <div class="thinking-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <div class="reasoning-content"></div>
        </div>
        <div class="thinking-card-footer">
            <span class="thinking-timestamp">${formatTime(new Date())}</span>
        </div>
    `;
    return block;
}

function createToolSelectionBlock(text) {
    const block = document.createElement('div');
    block.className = 'agent-phase-block tool-selection-block';
    block.innerHTML = `
        <div class="phase-header">
            <div class="phase-icon">
                <i class="bi bi-tools"></i>
            </div>
            <div class="phase-title">
                <span class="phase-label">Tool Selection</span>
                <span class="phase-description">${escapeHtml(text)}</span>
            </div>
        </div>
    `;
    return block;
}

function createToolExecutionBlock(toolName, input) {
    const block = document.createElement('div');
    block.className = 'agent-phase-block tool-execution-block';
    block.innerHTML = `
        <div class="phase-header">
            <div class="phase-icon executing">
                <i class="bi bi-gear spin"></i>
            </div>
            <div class="phase-title">
                <span class="phase-label">Tool Execution</span>
                <span class="phase-description">${toolName}</span>
            </div>
        </div>
        <div class="phase-content">
            ${input && Object.keys(input).length > 0 ? `
            <div class="tool-parameters">
                <div class="param-label">Parameters:</div>
                <pre class="param-content">${JSON.stringify(input, null, 2)}</pre>
            </div>
            ` : ''}
            <div class="tool-result-placeholder">
                <div class="shimmer"></div>
            </div>
        </div>
    `;
    return block;
}

function updateToolExecutionResult(block, content) {
    const icon = block.querySelector('.phase-icon i');
    icon.className = 'bi bi-check-circle';
    icon.parentElement.classList.remove('executing');
    icon.parentElement.classList.add('success');
    
    const placeholder = block.querySelector('.tool-result-placeholder');
    if (placeholder) {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'tool-result';
        resultDiv.innerHTML = `
            <div class="result-label">Result:</div>
            <pre class="result-content">${formatToolResult(content)}</pre>
        `;
        placeholder.replaceWith(resultDiv);
    }
}

function createResponseBlock() {
    const block = document.createElement('div');
    block.className = 'agent-phase-block response-block';
    block.innerHTML = `
        <div class="phase-header">
            <div class="phase-icon">
                <i class="bi bi-chat-dots"></i>
            </div>
            <div class="phase-title">
                <span class="phase-label">Response</span>
            </div>
        </div>
        <div class="phase-content">
            <div class="response-text"></div>
        </div>
    `;
    return block;
}

function createToolExecutionPopup(toolName) {
    // Remove any existing popup first
    removeToolExecutionPopup();
    
    const popup = document.createElement('div');
    popup.className = 'tool-execution-popup slide-up';
    popup.id = 'toolExecutionPopup';
    popup.innerHTML = `
        <div class="tool-popup-icon">
            <i class="bi bi-gear-fill spin"></i>
        </div>
        <div class="tool-popup-content">
            <div class="tool-popup-title">Tool Executing</div>
            <div class="tool-popup-name">${escapeHtml(toolName)}</div>
        </div>
        <div class="tool-popup-progress">
            <div class="tool-popup-progress-bar"></div>
        </div>
    `;
    
    // Add to body for proper fixed positioning
    document.body.appendChild(popup);
    
    // Trigger animation after a brief delay
    setTimeout(() => {
        popup.classList.add('active');
    }, 10);
    
    return popup;
}

function updateToolExecutionPopup(status, message) {
    const popup = document.getElementById('toolExecutionPopup');
    if (popup) {
        const icon = popup.querySelector('.tool-popup-icon i');
        const title = popup.querySelector('.tool-popup-title');
        const name = popup.querySelector('.tool-popup-name');
        
        if (status === 'complete') {
            icon.className = 'bi bi-check-circle-fill';
            title.textContent = 'Tool Complete';
            popup.classList.add('complete');
            
            // Auto-remove after 2 seconds
            setTimeout(() => {
                removeToolExecutionPopup();
            }, 2000);
        } else if (status === 'error') {
            icon.className = 'bi bi-exclamation-triangle-fill';
            title.textContent = 'Tool Error';
            popup.classList.add('error');
            
            // Auto-remove after 3 seconds
            setTimeout(() => {
                removeToolExecutionPopup();
            }, 3000);
        }
        
        if (message) {
            name.textContent = message;
        }
    }
}

function removeToolExecutionPopup() {
    const popup = document.getElementById('toolExecutionPopup');
    if (popup) {
        popup.classList.remove('active');
        popup.classList.add('slide-down');
        setTimeout(() => {
            popup.remove();
        }, 300);
    }
    currentToolExecutionPopup = null;
}

function togglePhase(header) {
    const block = header.parentElement;
    block.classList.toggle('collapsed');
    const toggle = header.querySelector('.phase-toggle');
    if (toggle) {
        toggle.classList.toggle('bi-chevron-down');
        toggle.classList.toggle('bi-chevron-up');
    }
}

function toggleThinkingCard(button) {
    const card = button.closest('.thinking-card');
    card.classList.toggle('collapsed');
    const icon = button.querySelector('i');
    if (icon) {
        icon.classList.toggle('bi-chevron-up');
        icon.classList.toggle('bi-chevron-down');
    }
}

function handleChatError(data) {
    console.error('Chat error:', data.error);
    showToast('Chat error: ' + data.error, 'error');
    
    // Remove any tool execution popup on error
    removeToolExecutionPopup();
    
    isStreaming = false;
    const sendBtn = document.getElementById('sendButton');
    if (sendBtn) sendBtn.disabled = false;
    
    if (currentStreamContainer) {
        const phasesContainer = currentStreamContainer.querySelector('.agent-loop-phases');
        const statusElement = currentStreamContainer.querySelector('.agent-status');
        
        phasesContainer.innerHTML = `
            <div class="error-block">
                <i class="bi bi-exclamation-triangle"></i>
                <span>Error: ${data.error}</span>
            </div>
        `;
        statusElement.innerHTML = '<span class="text-error">Failed</span>';
        currentStreamContainer = null;
    }
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function parseMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

function formatToolResult(content) {
    if (Array.isArray(content)) {
        return content.map(item => {
            if (typeof item === 'object' && item.text) {
                return item.text;
            }
            return JSON.stringify(item, null, 2);
        }).join('\n');
    }
    if (typeof content === 'string') {
        try {
            const parsed = JSON.parse(content);
            return JSON.stringify(parsed, null, 2);
        } catch {
            return content;
        }
    }
    return JSON.stringify(content, null, 2);
}

function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function updateConnectionStatus(status) {
    const indicator = document.querySelector('.connection-indicator');
    if (indicator) {
        indicator.className = `connection-indicator ${status}`;
    }
}

function updateStats() {
    const messageCountEl = document.getElementById('messageCount');
    const toolCallCountEl = document.getElementById('toolCallCount');
    const activeServersEl = document.getElementById('activeServers');
    const serverCountEl = document.getElementById('serverCount');
    
    if (messageCountEl) messageCountEl.textContent = messageCount;
    if (toolCallCountEl) toolCallCountEl.textContent = toolCallCount;
    if (activeServersEl) activeServersEl.textContent = activeServers;
    if (serverCountEl) serverCountEl.textContent = `${activeServers} connected`;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} slide-in`;
    toast.innerHTML = `
        <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Server Management (keep existing functions)
async function loadServers() {
    try {
        const response = await fetch('/api/mcp/servers');
        const data = await response.json();
        
        if (data.success) {
            // Store server configurations for later use
            data.servers.forEach(server => {
                serverConfigs[server.id] = server;
            });
            
            displayServers(data.servers);
            activeServers = data.servers.filter(s => s.status === 'connected').length;
            updateStats();
            updateAvailableTools();
            
            // Also load full config details from the JSON file
            await loadServerConfigDetails();
        }
    } catch (error) {
        console.error('Failed to load servers:', error);
        showToast('Failed to load MCP servers', 'error');
    }
}

async function loadServerConfigDetails() {
    try {
        const response = await fetch('/api/mcp/server-configs');
        const data = await response.json();
        
        if (data.success && data.configs) {
            // Merge detailed configs with server info
            Object.keys(data.configs).forEach(serverId => {
                if (serverConfigs[serverId]) {
                    serverConfigs[serverId] = {
                        ...serverConfigs[serverId],
                        ...data.configs[serverId]
                    };
                }
            });
        }
    } catch (error) {
        console.error('Failed to load server config details:', error);
    }
}

async function connectServer(serverId) {
    const card = document.getElementById(`server-${serverId}`);
    if (card) {
        card.classList.add('connecting');
    }
    
    try {
        const response = await fetch(`/api/mcp/servers/${serverId}/connect`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Server connected successfully', 'success');
            await loadServers();
        } else {
            showToast(data.error || 'Failed to connect server', 'error');
        }
    } catch (error) {
        console.error('Failed to connect server:', error);
        showToast('Failed to connect server', 'error');
    }
}

async function disconnectServer(serverId) {
    try {
        const response = await fetch(`/api/mcp/servers/${serverId}/disconnect`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Server disconnected', 'info');
            await loadServers();
        }
    } catch (error) {
        console.error('Failed to disconnect server:', error);
    }
}

// Modal functions
function showAddServerModal() {
    document.getElementById('addServerModal').style.display = 'flex';
    document.getElementById('serverName').focus();
}

function hideAddServerModal() {
    document.getElementById('addServerModal').style.display = 'none';
    document.getElementById('addServerForm').reset();
}

function showEditServerModal() {
    document.getElementById('editServerModal').style.display = 'flex';
}

function hideEditServerModal() {
    document.getElementById('editServerModal').style.display = 'none';
    document.getElementById('editServerForm').reset();
}

async function editServer(serverId) {
    // Get the server configuration
    const server = serverConfigs[serverId];
    if (!server) {
        showToast('Server configuration not found', 'error');
        return;
    }
    
    // Populate the edit form with current values
    document.getElementById('editServerId').value = serverId;
    document.getElementById('editServerName').value = server.name || '';
    document.getElementById('editServerDescription').value = server.description || '';
    document.getElementById('editServerCommand').value = JSON.stringify(server.command || []);
    document.getElementById('editServerArgs').value = JSON.stringify(server.args || []);
    document.getElementById('editServerEnv').value = JSON.stringify(server.env_vars || {});
    document.getElementById('editServerCategory').value = server.category || 'General';
    document.getElementById('editAutoConnect').checked = server.auto_connect || false;
    
    // Show the modal
    showEditServerModal();
}

async function updateServer() {
    const serverId = document.getElementById('editServerId').value;
    
    // Get form values
    const name = document.getElementById('editServerName').value.trim();
    const description = document.getElementById('editServerDescription').value.trim();
    const commandStr = document.getElementById('editServerCommand').value.trim();
    const argsStr = document.getElementById('editServerArgs').value.trim();
    const envStr = document.getElementById('editServerEnv').value.trim();
    const category = document.getElementById('editServerCategory').value;
    const autoConnect = document.getElementById('editAutoConnect').checked;
    
    if (!name || !commandStr) {
        showToast('Please fill in required fields', 'error');
        return;
    }
    
    // Parse JSON arrays and objects
    let command, args = [], envVars = {};
    try {
        command = JSON.parse(commandStr);
        if (argsStr) {
            args = JSON.parse(argsStr);
        }
        if (envStr) {
            envVars = JSON.parse(envStr);
        }
    } catch (error) {
        showToast('Invalid JSON format for command, arguments, or environment variables', 'error');
        return;
    }
    
    // Send update request
    try {
        const response = await fetch(`/api/mcp/servers/${serverId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                description: description,
                command: command,
                args: args,
                env_vars: envVars,
                category: category,
                auto_connect: autoConnect
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message || 'Server updated successfully', 'success');
            hideEditServerModal();
            await loadServers();
        } else {
            showToast(data.error || 'Failed to update server', 'error');
        }
    } catch (error) {
        console.error('Error updating server:', error);
        showToast('Failed to update server', 'error');
    }
}

async function deleteServer(serverId) {
    const server = serverConfigs[serverId];
    if (!server) {
        showToast('Server not found', 'error');
        return;
    }
    
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete "${server.name}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/mcp/servers/${serverId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message || 'Server deleted successfully', 'success');
            await loadServers();
        } else {
            showToast(data.error || 'Failed to delete server', 'error');
        }
    } catch (error) {
        console.error('Error deleting server:', error);
        showToast('Failed to delete server', 'error');
    }
}

// UI Control functions
function changeModel(modelId) {
    currentModel = modelId;
    console.log('Model changed to:', modelId);
    
    // Send model change to backend
    fetch('/api/mcp/model', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model: modelId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(`Model changed to: ${modelId}`, 'success');
        } else {
            showToast('Failed to change model', 'error');
        }
    })
    .catch(error => {
        console.error('Error changing model:', error);
        showToast('Failed to change model', 'error');
    });
}

function clearChat() {
    fetch('/api/mcp/chat/clear', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const container = document.getElementById('chatContainer');
                container.innerHTML = `
                    <div class="chat-welcome">
                        <div class="chat-welcome-icon">
                            <i class="bi bi-plugin"></i>
                        </div>
                        <h3>MCP-Powered Chat</h3>
                        <p class="text-secondary">
                            Chat with Nova Lite while leveraging connected MCP servers
                        </p>
                    </div>
                `;
                messageCount = 0;
                updateStats();
                showToast('Chat cleared', 'info');
            }
        })
        .catch(error => {
            console.error('Failed to clear chat:', error);
            showToast('Failed to clear chat', 'error');
        });
}

function toggleToolUse() {
    useTools = !useTools;
    const button = document.getElementById('toolToggle');
    if (useTools) {
        button.classList.remove('btn-secondary');
        button.classList.add('btn-ghost');
        showToast('MCP tools enabled', 'success');
    } else {
        button.classList.remove('btn-ghost');
        button.classList.add('btn-secondary');
        showToast('MCP tools disabled', 'info');
    }
}

function showAgentInstructionsModal() {
    const modal = document.getElementById('agentInstructionsModal');
    const input = document.getElementById('modalSystemPromptInput');
    
    // Set current prompt value
    input.value = systemPrompt;
    
    // Show modal
    modal.style.display = 'flex';
    
    // Focus on textarea after a short delay
    setTimeout(() => {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    }, 100);
}

function hideAgentInstructionsModal() {
    const modal = document.getElementById('agentInstructionsModal');
    modal.style.display = 'none';
}

function saveAgentInstructions() {
    const input = document.getElementById('modalSystemPromptInput');
    const newPrompt = input.value.trim();
    
    if (!newPrompt) {
        showToast('Agent instructions cannot be empty', 'error');
        return;
    }
    
    // Update global variable
    systemPrompt = newPrompt;
    
    // Update preview text
    document.getElementById('systemPromptText').textContent = systemPrompt.trim();
    
    // Hide modal
    hideAgentInstructionsModal();
    
    // Save to backend (optional - for persistence across sessions)
    fetch('/api/mcp/system-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ system_prompt: systemPrompt })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Agent instructions updated', 'success');
        }
    })
    .catch(error => {
        console.error('Failed to save agent instructions:', error);
    });
}

// Legacy function - kept for compatibility but redirects to modal
function toggleSystemPromptEditor() {
    showAgentInstructionsModal();
}

// Legacy function - kept for compatibility
function saveSystemPrompt() {
    saveAgentInstructions();
}

// Legacy function - kept for compatibility
function cancelSystemPromptEdit() {
    hideAgentInstructionsModal();
}

function showServerConfig(serverId) {
    const server = serverConfigs[serverId];
    if (!server) {
        showToast('Server configuration not found', 'error');
        return;
    }
    
    const modal = document.getElementById('serverConfigModal');
    const content = document.getElementById('serverConfigContent');
    
    // Format the configuration display
    let configHtml = `
        <div class="config-section">
            <label class="config-label">Server Name</label>
            <div class="config-value">${server.name || 'Unnamed Server'}</div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Description</label>
            <div class="config-value ${!server.description ? 'empty' : ''}">${server.description || 'No description provided'}</div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Status</label>
            <div class="config-value">
                <span class="server-badge ${server.status}">
                    <i class="bi bi-circle-fill"></i>
                    ${server.status || 'unknown'}
                </span>
                ${server.tools_count ? ` - ${server.tools_count} tools available` : ''}
            </div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Command</label>
            <div class="config-value">${server.command ? JSON.stringify(server.command, null, 2) : 'Not specified'}</div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Arguments</label>
            <div class="config-value ${!server.args || server.args.length === 0 ? 'empty' : ''}">${server.args && server.args.length > 0 ? JSON.stringify(server.args, null, 2) : 'None'}</div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Environment Variables</label>
            <div class="config-value ${!server.env_vars || Object.keys(server.env_vars).length === 0 ? 'empty' : ''}">`;
    
    if (server.env_vars && Object.keys(server.env_vars).length > 0) {
        // Mask sensitive values
        const maskedEnv = {};
        Object.keys(server.env_vars).forEach(key => {
            const value = server.env_vars[key];
            // Mask tokens and secrets
            if (key.toLowerCase().includes('token') || 
                key.toLowerCase().includes('key') || 
                key.toLowerCase().includes('secret') ||
                key.toLowerCase().includes('password')) {
                maskedEnv[key] = value.substring(0, 4) + '****' + value.substring(value.length - 4);
            } else {
                maskedEnv[key] = value;
            }
        });
        configHtml += JSON.stringify(maskedEnv, null, 2);
    } else {
        configHtml += 'None';
    }
    
    configHtml += `</div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Category</label>
            <div class="config-value">${server.category || 'General'}</div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Auto-connect</label>
            <div class="config-value">${server.auto_connect ? 'Yes' : 'No'}</div>
        </div>
        
        <div class="config-section">
            <label class="config-label">Server ID</label>
            <div class="config-value" style="font-size: 0.75rem;">${serverId}</div>
        </div>`;
    
    content.innerHTML = configHtml;
    modal.style.display = 'flex';
}

function hideServerConfigModal() {
    document.getElementById('serverConfigModal').style.display = 'none';
}

function toggleActivityMonitor() {
    const monitor = document.getElementById('activityMonitor');
    monitor.style.display = monitor.style.display === 'none' ? 'block' : 'none';
}

async function addServer() {
    const form = document.getElementById('addServerForm');
    
    // Get form values
    const name = document.getElementById('serverName').value.trim();
    const description = document.getElementById('serverDescription').value.trim();
    const commandStr = document.getElementById('serverCommand').value.trim();
    const argsStr = document.getElementById('serverArgs').value.trim();
    const envStr = document.getElementById('serverEnv').value.trim();
    const category = document.getElementById('serverCategory').value;
    const autoConnect = document.getElementById('autoConnect').checked;
    
    if (!name || !commandStr) {
        showToast('Please fill in required fields', 'error');
        return;
    }
    
    // Parse JSON arrays and objects
    let command, args = [], envVars = {};
    try {
        command = JSON.parse(commandStr);
        if (argsStr) {
            args = JSON.parse(argsStr);
        }
        if (envStr) {
            envVars = JSON.parse(envStr);
        }
    } catch (error) {
        showToast('Invalid JSON format for command, arguments, or environment variables', 'error');
        return;
    }
    
    // Create server config
    const serverConfig = {
        name: name,
        description: description,
        command: command,
        args: args,
        env_vars: envVars,
        category: category,
        auto_connect: autoConnect,
        enabled: true
    };
    
    try {
        const response = await fetch('/api/mcp/servers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(serverConfig)
        });
        const data = await response.json();
        
        if (data.success) {
            showToast('Server added successfully', 'success');
            hideAddServerModal();
            await loadServers();
            
            // Auto-connect if requested
            if (autoConnect) {
                await connectServer(data.server_id);
            }
        } else {
            showToast(data.error || 'Failed to add server', 'error');
        }
    } catch (error) {
        console.error('Failed to add server:', error);
        showToast('Failed to add server', 'error');
    }
}

function handleServerConnected(data) {
    showToast(`Connected to ${data.server_name || 'server'}`, 'success');
    loadServers();
}

function handleServerDisconnected(data) {
    showToast(`Disconnected from server`, 'info');
    loadServers();
}

function handleServerError(data) {
    showToast(`Server error: ${data.error}`, 'error');
    loadServers();
}

function displayServers(servers) {
    const serverList = document.getElementById('serverList');
    if (!serverList) return;
    
    serverList.innerHTML = '';
    
    if (servers.length === 0) {
        serverList.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-plugin"></i>
                <p>No MCP servers configured</p>
                <small>Add servers to enable tools</small>
            </div>
        `;
        return;
    }
    
    servers.forEach(server => {
        const card = createServerCard(server);
        serverList.appendChild(card);
    });
}

function createServerCard(server) {
    const card = document.createElement('div');
    card.className = `server-card ${server.status}`;
    card.id = `server-${server.id}`;
    
    card.innerHTML = `
        <div class="server-header">
            <div class="server-info">
                <h4>${server.name}</h4>
                <p>${server.description || 'No description'}</p>
            </div>
            <span class="server-badge ${server.status}">
                <i class="bi bi-circle-fill"></i>
                ${server.status}
            </span>
        </div>
        
        <div class="server-tools">
            ${server.tools_count ? `<span class="tool-count">${server.tools_count} tools</span>` : ''}
        </div>
        
        <div class="server-actions">
            <button class="btn-ghost btn-sm" onclick="showServerConfig('${server.id}')" title="View Configuration">
                <i class="bi bi-info-circle"></i>
            </button>
            <button class="btn-ghost btn-sm" onclick="editServer('${server.id}')" title="Edit Server">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn-ghost btn-sm" onclick="deleteServer('${server.id}')" title="Delete Server">
                <i class="bi bi-trash"></i>
            </button>
            ${server.status === 'connected' ? `
                <button class="btn-secondary" onclick="disconnectServer('${server.id}')">
                    Disconnect
                </button>
            ` : `
                <button class="btn-primary" onclick="connectServer('${server.id}')">
                    Connect
                </button>
            `}
        </div>
    `;
    
    return card;
}

async function updateAvailableTools() {
    try {
        // Get MCP tools
        const mcpResponse = await fetch('/api/mcp/tools');
        const mcpData = await mcpResponse.json();
        
        // Get Strands tools count
        const strandsResponse = await fetch('/api/mcp/strands-tools');
        const strandsData = await strandsResponse.json();
        
        let totalTools = 0;
        if (mcpData.success && mcpData.tools) {
            totalTools += mcpData.tools.length;
        }
        if (strandsData.success && strandsData.tools) {
            totalTools += strandsData.tools.total_enabled || 0;
        }
        
        // Update the tool count in the chat input area
        const toolsCountEl = document.getElementById('connectedToolsCount');
        if (toolsCountEl) {
            toolsCountEl.textContent = totalTools;
        }
        
        if (mcpData.success && mcpData.tools) {
            
            const toolsContainer = document.getElementById('availableTools');
            if (toolsContainer) {
                if (mcpData.tools.length === 0) {
                    toolsContainer.innerHTML = '<p class="text-tertiary">No tools available</p>';
                } else {
                    toolsContainer.innerHTML = mcpData.tools.map(tool => `
                        <div class="tool-item">
                            <i class="bi bi-wrench"></i>
                            <span>${tool.name}</span>
                        </div>
                    `).join('');
                }
            }
        }
    } catch (error) {
        console.error('Failed to load tools:', error);
    }
}