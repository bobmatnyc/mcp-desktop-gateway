#!/usr/bin/env node
/**
 * MCP Gateway CLI
 * NPM wrapper for Python MCP Gateway
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Check if Python is installed
function checkPython() {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const check = spawn(pythonCmd, ['--version']);
    
    check.on('close', (code) => {
      resolve(code === 0);
    });
    
    check.on('error', () => {
      resolve(false);
    });
  });
}

// Get Python executable path
function getPythonPath() {
  // Check common Python locations (prioritize homebrew)
  const candidates = [
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3', 
    '/usr/bin/python3',
    'python3',
    'python'
  ];
  
  for (const candidate of candidates) {
    try {
      const result = require('child_process').execSync(`${candidate} --version`, { 
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore']
      });
      if (result.includes('Python 3')) {
        return candidate;
      }
    } catch (e) {
      // Continue to next candidate
    }
  }
  
  return null;
}

// Setup virtual environment
async function setupVirtualEnv() {
  const venvPath = path.join(__dirname, '..', 'venv');
  const pythonPath = getPythonPath();
  
  if (!pythonPath) {
    console.error('Python 3 is required but not found. Please install Python 3.8 or later.');
    process.exit(1);
  }
  
  console.log(`Setting up Python virtual environment...`);
  console.log(`Using Python: ${pythonPath}`);
  
  // Create venv if it doesn't exist
  if (!fs.existsSync(venvPath)) {
    await new Promise((resolve, reject) => {
      const venv = spawn(pythonPath, ['-m', 'venv', venvPath], {
        stdio: 'inherit'
      });
      venv.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error('Failed to create virtual environment'));
      });
    });
  }
  
  // Install dependencies
  const pipPath = path.join(venvPath, process.platform === 'win32' ? 'Scripts' : 'bin', 'pip');
  const requirementsPath = path.join(__dirname, '..', 'requirements.txt');
  
  console.log('Installing Python dependencies...');
  await new Promise((resolve, reject) => {
    const pip = spawn(pipPath, ['install', '-r', requirementsPath], {
      stdio: 'inherit'
    });
    pip.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error('Failed to install dependencies'));
    });
  });
  
  // Compile bytecode for faster startup
  console.log('Compiling Python bytecode...');
  const venvPythonPath = path.join(venvPath, process.platform === 'win32' ? 'Scripts' : 'bin', 'python');
  await new Promise((resolve, reject) => {
    const compile = spawn(venvPythonPath, [path.join(__dirname, '..', 'compile_bytecode.py')], {
      stdio: 'inherit',
      cwd: path.join(__dirname, '..')
    });
    compile.on('close', (code) => {
      if (code === 0) resolve();
      else {
        console.warn('Bytecode compilation failed, continuing without optimization');
        resolve(); // Don't fail setup if compilation fails
      }
    });
  });
  
  console.log('Setup complete!');
}

// Run the MCP Gateway
async function runGateway(args = []) {
  const venvPath = path.join(__dirname, '..', 'venv');
  const pythonPath = path.join(venvPath, process.platform === 'win32' ? 'Scripts' : 'bin', 'python');
  const scriptPath = path.join(__dirname, '..', 'run_mcp_gateway.py');
  
  // Check if venv exists
  if (!fs.existsSync(venvPath)) {
    console.log('Virtual environment not found. Running setup...');
    await setupVirtualEnv();
  }
  
  // Set up environment
  const env = { ...process.env };
  env.PYTHONPATH = path.join(__dirname, '..', 'src');
  env.PYTHONUNBUFFERED = '1'; // Ensure Python doesn't buffer output
  
  // Run the gateway
  // Use 'pipe' for stdio if MCP_TEST_MODE is set to allow testing
  const stdioMode = process.env.MCP_TEST_MODE === '1' ? 'pipe' : 'inherit';
  
  const gateway = spawn(pythonPath, [scriptPath, ...args], {
    stdio: stdioMode,
    env: env,
    cwd: path.join(__dirname, '..')
  });
  
  // If in test mode, pipe stdio with proper flushing
  if (process.env.MCP_TEST_MODE === '1') {
    gateway.stdout.on('data', (data) => {
      process.stdout.write(data);
    });
    gateway.stderr.on('data', (data) => {
      process.stderr.write(data);
    });
    process.stdin.on('data', (data) => {
      gateway.stdin.write(data);
    });
  }
  
  gateway.on('close', (code) => {
    process.exit(code);
  });
  
  // Handle signals
  process.on('SIGINT', () => {
    gateway.kill('SIGINT');
  });
  
  process.on('SIGTERM', () => {
    gateway.kill('SIGTERM');
  });
}

// CLI commands
const command = process.argv[2];

async function main() {
  switch (command) {
    case 'setup':
      await setupVirtualEnv();
      break;
    
    case 'config':
      // Show config location
      const configPath = path.join(os.homedir(), 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json');
      console.log(`Claude Desktop config location: ${configPath}`);
      console.log('\nAdd this to your config:');
      console.log(JSON.stringify({
        "mcp-gateway": {
          "command": "npx",
          "args": ["mcp-gateway"],
          "env": {
            "NODE_PATH": process.execPath
          }
        }
      }, null, 2));
      break;
    
    case 'help':
    case '--help':
    case '-h':
      console.log(`
MCP Gateway - Universal bridge for Claude Desktop

Usage: mcp-gateway [command]

Commands:
  (none)    Run the MCP Gateway server
  setup     Set up Python environment and dependencies
  config    Show Claude Desktop configuration
  help      Show this help message

Examples:
  mcp-gateway              # Run the gateway
  mcp-gateway setup        # Install dependencies
  mcp-gateway config       # Show config for Claude Desktop
`);
      break;
    
    default:
      // Run gateway with any args
      await runGateway(process.argv.slice(2));
  }
}

// Check if Python is available
checkPython().then(hasPython => {
  if (!hasPython && command !== 'help') {
    console.error('Python 3 is required but not found. Please install Python 3.8 or later.');
    process.exit(1);
  }
  main().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
  });
});