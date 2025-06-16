#!/usr/bin/env node
/**
 * Example HTTP Connector for MCP Gateway (Node.js)
 * Demonstrates tools, resources, and prompts implementation
 */

const express = require('express');
const app = express();

// Middleware
app.use(express.json());

// Simulated data store
const notes = new Map();
let counter = 0;

// Connector info endpoint
app.get('/info', (req, res) => {
    res.json({
        name: 'example-connector-nodejs',
        version: '1.0.0',
        description: 'Example Node.js connector for MCP Gateway',
        capabilities: {
            tools: true,
            resources: true,
            prompts: true
        }
    });
});

// List tools
app.get('/tools', (req, res) => {
    res.json({
        tools: [
            {
                name: 'echo',
                description: 'Echo back the input message',
                inputSchema: {
                    type: 'object',
                    properties: {
                        message: {
                            type: 'string',
                            description: 'Message to echo'
                        }
                    },
                    required: ['message']
                }
            },
            {
                name: 'random_number',
                description: 'Generate a random number',
                inputSchema: {
                    type: 'object',
                    properties: {
                        min: {
                            type: 'number',
                            description: 'Minimum value',
                            default: 0
                        },
                        max: {
                            type: 'number',
                            description: 'Maximum value',
                            default: 100
                        }
                    }
                }
            },
            {
                name: 'save_data',
                description: 'Save data with a key',
                inputSchema: {
                    type: 'object',
                    properties: {
                        key: {
                            type: 'string',
                            description: 'Data key'
                        },
                        value: {
                            type: 'string',
                            description: 'Data value'
                        }
                    },
                    required: ['key', 'value']
                }
            }
        ]
    });
});

// Execute tool
app.post('/tools/:toolName/execute', (req, res) => {
    const { toolName } = req.params;
    const { arguments: args = {} } = req.body;
    
    try {
        switch (toolName) {
            case 'echo':
                res.json({
                    content: [{
                        type: 'text',
                        text: `Echo: ${args.message || 'No message provided'}`
                    }]
                });
                break;
                
            case 'random_number':
                const min = args.min || 0;
                const max = args.max || 100;
                const randomNum = Math.floor(Math.random() * (max - min + 1)) + min;
                
                res.json({
                    content: [{
                        type: 'text',
                        text: `Random number between ${min} and ${max}: ${randomNum}`
                    }]
                });
                break;
                
            case 'save_data':
                notes.set(args.key, {
                    key: args.key,
                    value: args.value,
                    timestamp: new Date().toISOString()
                });
                
                res.json({
                    content: [{
                        type: 'text',
                        text: `Data saved with key: ${args.key}`
                    }]
                });
                break;
                
            default:
                res.status(404).json({
                    error: `Tool not found: ${toolName}`
                });
        }
    } catch (error) {
        res.status(500).json({
            content: [{
                type: 'text',
                text: `Error: ${error.message}`
            }],
            isError: true
        });
    }
});

// List resources
app.get('/resources', (req, res) => {
    const resources = [];
    
    // Add saved data as resources
    for (const [key, data] of notes.entries()) {
        resources.push({
            uri: `data://${key}`,
            name: key,
            description: `Data saved at ${data.timestamp}`,
            mimeType: 'application/json'
        });
    }
    
    // Add static resources
    resources.push({
        uri: 'config://settings.json',
        name: 'settings.json',
        description: 'Connector settings',
        mimeType: 'application/json'
    });
    
    res.json({ resources });
});

// Read resource
app.get('/resources/:uri', (req, res) => {
    const { uri } = req.params;
    
    if (uri.startsWith('data://')) {
        const key = uri.replace('data://', '');
        const data = notes.get(key);
        
        if (data) {
            res.json({
                uri,
                mimeType: 'application/json',
                text: JSON.stringify(data, null, 2)
            });
        } else {
            res.status(404).json({ error: 'Data not found' });
        }
    } else if (uri === 'config://settings.json') {
        res.json({
            uri,
            mimeType: 'application/json',
            text: JSON.stringify({
                connector: 'example-nodejs',
                version: '1.0.0',
                environment: process.env.NODE_ENV || 'development'
            }, null, 2)
        });
    } else {
        res.status(404).json({ error: 'Resource not found' });
    }
});

// List prompts
app.get('/prompts', (req, res) => {
    res.json({
        prompts: [
            {
                name: 'code_review',
                description: 'Review code for best practices',
                arguments: [
                    {
                        name: 'code',
                        description: 'Code to review',
                        required: true
                    },
                    {
                        name: 'language',
                        description: 'Programming language',
                        required: false
                    }
                ]
            },
            {
                name: 'explain_concept',
                description: 'Explain a technical concept',
                arguments: [
                    {
                        name: 'concept',
                        description: 'Concept to explain',
                        required: true
                    },
                    {
                        name: 'level',
                        description: 'Explanation level (beginner/intermediate/advanced)',
                        required: false
                    }
                ]
            }
        ]
    });
});

// Get prompt
app.get('/prompts/:promptName', (req, res) => {
    const { promptName } = req.params;
    
    switch (promptName) {
        case 'code_review':
            res.json({
                name: 'code_review',
                description: 'Review code for best practices',
                arguments: [
                    {
                        name: 'code',
                        description: 'Code to review',
                        required: true
                    },
                    {
                        name: 'language',
                        description: 'Programming language',
                        required: false
                    }
                ],
                messages: [
                    {
                        role: 'system',
                        content: 'You are an experienced code reviewer. Analyze code for best practices, potential bugs, and improvements.'
                    },
                    {
                        role: 'user',
                        content: 'Please review the following {{language|code}}:\n\n{{code}}'
                    }
                ]
            });
            break;
            
        case 'explain_concept':
            res.json({
                name: 'explain_concept',
                description: 'Explain a technical concept',
                arguments: [
                    {
                        name: 'concept',
                        description: 'Concept to explain',
                        required: true
                    },
                    {
                        name: 'level',
                        description: 'Explanation level',
                        required: false
                    }
                ],
                messages: [
                    {
                        role: 'system',
                        content: 'You are a patient teacher who explains technical concepts clearly.'
                    },
                    {
                        role: 'user',
                        content: 'Explain {{concept}} at a {{level|beginner}} level.'
                    }
                ]
            });
            break;
            
        default:
            res.status(404).json({ error: 'Prompt not found' });
    }
});

// Start server
const PORT = process.env.PORT || 8081;
app.listen(PORT, () => {
    console.log(`Example Node.js connector running on port ${PORT}`);
});