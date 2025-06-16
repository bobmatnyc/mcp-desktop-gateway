#!/usr/bin/env python3
"""
Example HTTP Connector for MCP Gateway
Demonstrates tools, resources, and prompts implementation
"""

from flask import Flask, jsonify, request
from datetime import datetime
import os

app = Flask(__name__)

# Simulated data store
NOTES = {}
COUNTER = 0


@app.route('/info')
def get_info():
    """Connector information endpoint"""
    return jsonify({
        "name": "example-connector",
        "version": "1.0.0",
        "description": "Example connector demonstrating MCP Gateway integration",
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": True
        }
    })


@app.route('/tools')
def list_tools():
    """List available tools"""
    return jsonify({
        "tools": [
            {
                "name": "add_note",
                "description": "Add a note to the collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Note title"
                        },
                        "content": {
                            "type": "string",
                            "description": "Note content"
                        }
                    },
                    "required": ["title", "content"]
                }
            },
            {
                "name": "list_notes",
                "description": "List all notes",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "increment_counter",
                "description": "Increment the counter and return new value",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "by": {
                            "type": "integer",
                            "description": "Amount to increment by",
                            "default": 1
                        }
                    }
                }
            }
        ]
    })


@app.route('/tools/<tool_name>/execute', methods=['POST'])
def execute_tool(tool_name):
    """Execute a specific tool"""
    global COUNTER
    
    try:
        data = request.get_json() or {}
        arguments = data.get('arguments', {})
        
        if tool_name == 'add_note':
            note_id = f"note_{len(NOTES) + 1}"
            NOTES[note_id] = {
                "id": note_id,
                "title": arguments.get('title'),
                "content": arguments.get('content'),
                "created": datetime.now().isoformat()
            }
            
            return jsonify({
                "content": [{
                    "type": "text",
                    "text": f"Note added successfully with ID: {note_id}"
                }]
            })
            
        elif tool_name == 'list_notes':
            if not NOTES:
                return jsonify({
                    "content": [{
                        "type": "text",
                        "text": "No notes found"
                    }]
                })
                
            notes_text = "\\n".join([
                f"- {note['title']} (ID: {note['id']})"
                for note in NOTES.values()
            ])
            
            return jsonify({
                "content": [{
                    "type": "text",
                    "text": f"Notes:\\n{notes_text}"
                }]
            })
            
        elif tool_name == 'increment_counter':
            by = arguments.get('by', 1)
            COUNTER += by
            
            return jsonify({
                "content": [{
                    "type": "text",
                    "text": f"Counter incremented by {by}. New value: {COUNTER}"
                }]
            })
            
        else:
            return jsonify({
                "error": f"Tool not found: {tool_name}"
            }), 404
            
    except Exception as e:
        return jsonify({
            "content": [{
                "type": "text",
                "text": f"Error executing tool: {str(e)}"
            }],
            "isError": True
        }), 500


@app.route('/resources')
def list_resources():
    """List available resources"""
    resources = []
    
    # Add notes as resources
    for note_id, note in NOTES.items():
        resources.append({
            "uri": f"note://{note_id}",
            "name": note['title'],
            "description": f"Note created at {note['created']}",
            "mimeType": "text/plain"
        })
        
    # Add a static resource
    resources.append({
        "uri": "file://example.txt",
        "name": "example.txt",
        "description": "Example text file",
        "mimeType": "text/plain"
    })
    
    return jsonify({"resources": resources})


@app.route('/resources/<path:resource_uri>')
def read_resource(resource_uri):
    """Read a specific resource"""
    
    if resource_uri.startswith('note://'):
        note_id = resource_uri.replace('note://', '')
        note = NOTES.get(note_id)
        
        if note:
            return jsonify({
                "uri": resource_uri,
                "mimeType": "text/plain",
                "text": f"{note['title']}\\n\\n{note['content']}"
            })
        else:
            return jsonify({"error": "Note not found"}), 404
            
    elif resource_uri == 'file://example.txt':
        return jsonify({
            "uri": resource_uri,
            "mimeType": "text/plain",
            "text": "This is an example text file content.\\nIt demonstrates resource reading."
        })
        
    else:
        return jsonify({"error": "Resource not found"}), 404


@app.route('/prompts')
def list_prompts():
    """List available prompts"""
    return jsonify({
        "prompts": [
            {
                "name": "summarize_notes",
                "description": "Generate a summary of all notes",
                "arguments": []
            },
            {
                "name": "analyze_text",
                "description": "Analyze the provided text",
                "arguments": [
                    {
                        "name": "text",
                        "description": "Text to analyze",
                        "required": True
                    },
                    {
                        "name": "style",
                        "description": "Analysis style (brief/detailed)",
                        "required": False
                    }
                ]
            }
        ]
    })


@app.route('/prompts/<prompt_name>')
def get_prompt(prompt_name):
    """Get a specific prompt"""
    
    if prompt_name == 'summarize_notes':
        notes_content = ""
        for note in NOTES.values():
            notes_content += f"\\n\\nTitle: {note['title']}\\nContent: {note['content']}"
            
        return jsonify({
            "name": "summarize_notes",
            "description": "Generate a summary of all notes",
            "arguments": [],
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes notes."
                },
                {
                    "role": "user",
                    "content": f"Please summarize the following notes:{notes_content}"
                }
            ]
        })
        
    elif prompt_name == 'analyze_text':
        return jsonify({
            "name": "analyze_text",
            "description": "Analyze the provided text",
            "arguments": [
                {
                    "name": "text",
                    "description": "Text to analyze",
                    "required": True
                },
                {
                    "name": "style",
                    "description": "Analysis style (brief/detailed)",
                    "required": False
                }
            ],
            "messages": [
                {
                    "role": "system",
                    "content": "You are a text analysis expert."
                },
                {
                    "role": "user",
                    "content": "Analyze the following text in a {{style|detailed}} manner:\\n\\n{{text}}"
                }
            ]
        })
        
    else:
        return jsonify({"error": "Prompt not found"}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)