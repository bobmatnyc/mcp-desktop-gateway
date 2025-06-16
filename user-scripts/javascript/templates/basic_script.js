#!/usr/bin/env node

/**
 * Task: [Brief description of what this script does]
 * Created: [YYYY-MM-DD]
 * Author: [Creator name/identifier]
 * 
 * Description:
 *   [Detailed description of the script's purpose, inputs, outputs, and behavior]
 * 
 * Usage:
 *   node basic_script.js [arguments]
 *   
 *   Arguments:
 *     --input, -i:   Input file or data source
 *     --output, -o:  Output file (default: stdout)
 *     --config, -c:  Configuration file path
 *     --verbose, -v: Enable verbose logging
 *     --dry-run:     Show what would be done without executing
 *     --help, -h:    Show this help message
 * 
 *   Examples:
 *     node basic_script.js --input data.json --output results.json
 *     node basic_script.js --input data.csv --verbose
 *     node basic_script.js --help
 * 
 * Dependencies:
 *   - Node.js 16+
 *   - Required packages: [list packages]
 * 
 * Notes:
 *   - [Any important notes or limitations]
 *   - [Performance considerations]
 *   - [Known issues or workarounds]
 */

const fs = require('fs').promises;
const path = require('path');
const { program } = require('commander');

// Configuration
const PROJECT_ROOT = path.resolve(__dirname, '../../../..');
const LOG_DIR = path.join(PROJECT_ROOT, 'user-scripts/shared/logs');

/**
 * Custom error class for script-specific errors
 */
class ScriptError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ScriptError';
    }
}

/**
 * Simple logging utility
 */
class Logger {
    constructor(verbose = false) {
        this.verbose = verbose;
        this.logFile = path.join(LOG_DIR, 'script.log');
    }

    async _writeLog(level, message) {
        const timestamp = new Date().toISOString();
        const logEntry = `${timestamp} - ${level} - ${message}\n`;
        
        // Write to console
        if (level === 'ERROR' || this.verbose || level === 'INFO') {
            console.log(`${timestamp} - ${level} - ${message}`);
        }
        
        // Write to file
        try {
            await fs.appendFile(this.logFile, logEntry);
        } catch (err) {
            console.error('Failed to write to log file:', err.message);
        }
    }

    async info(message) {
        await this._writeLog('INFO', message);
    }

    async debug(message) {
        if (this.verbose) {
            await this._writeLog('DEBUG', message);
        }
    }

    async error(message) {
        await this._writeLog('ERROR', message);
    }

    async warn(message) {
        await this._writeLog('WARN', message);
    }
}

/**
 * Load configuration from file or use defaults
 */
async function loadConfig(configPath = null) {
    const defaultConfig = {
        timeout: 30000,
        maxRetries: 3,
        batchSize: 100,
    };

    if (configPath) {
        try {
            const configData = await fs.readFile(configPath, 'utf8');
            const userConfig = JSON.parse(configData);
            Object.assign(defaultConfig, userConfig);
            logger.info(`Loaded configuration from ${configPath}`);
        } catch (err) {
            logger.warn(`Failed to load config from ${configPath}: ${err.message}`);
        }
    }

    return defaultConfig;
}

/**
 * Validate input arguments and files
 */
async function validateInputs(options) {
    try {
        await fs.access(options.input);
    } catch (err) {
        throw new ScriptError(`Input file does not exist: ${options.input}`);
    }

    if (options.output) {
        const outputDir = path.dirname(options.output);
        try {
            await fs.mkdir(outputDir, { recursive: true });
            logger.debug(`Ensured output directory exists: ${outputDir}`);
        } catch (err) {
            throw new ScriptError(`Failed to create output directory: ${err.message}`);
        }
    }
}

/**
 * Main data processing function
 */
async function processData(inputPath, config) {
    logger.info(`Processing data from ${inputPath}`);
    
    try {
        const results = [];
        
        // Read input file
        const inputData = await fs.readFile(inputPath, 'utf8');
        
        // Example processing: split by lines and process each
        const lines = inputData.split('\n').filter(line => line.trim());
        
        for (let i = 0; i < lines.length; i++) {
            try {
                const processedItem = {
                    lineNumber: i + 1,
                    content: lines[i].trim(),
                    processedAt: new Date().toISOString(),
                    // TODO: Add your processing logic here
                };
                
                results.push(processedItem);
                
                if ((i + 1) % config.batchSize === 0) {
                    logger.info(`Processed ${i + 1} items`);
                }
                
            } catch (err) {
                logger.error(`Error processing line ${i + 1}: ${err.message}`);
                continue;
            }
        }
        
        logger.info(`Successfully processed ${results.length} items`);
        return results;
        
    } catch (err) {
        throw new ScriptError(`Failed to process data: ${err.message}`);
    }
}

/**
 * Save results to file or stdout
 */
async function saveResults(results, outputPath = null) {
    const outputData = {
        timestamp: new Date().toISOString(),
        totalItems: results.length,
        data: results
    };
    
    const jsonOutput = JSON.stringify(outputData, null, 2);
    
    if (outputPath) {
        await fs.writeFile(outputPath, jsonOutput, 'utf8');
        logger.info(`Results saved to ${outputPath}`);
    } else {
        console.log(jsonOutput);
    }
}

/**
 * Main script execution function
 */
async function main() {
    let logger;
    
    try {
        // Setup command line interface
        program
            .name('basic_script.js')
            .description('[Script description]')
            .requiredOption('-i, --input <path>', 'Input file or data source')
            .option('-o, --output <path>', 'Output file (default: stdout)')
            .option('-c, --config <path>', 'Configuration file path')
            .option('-v, --verbose', 'Enable verbose logging')
            .option('--dry-run', 'Show what would be done without executing')
            .helpOption('-h, --help', 'Show this help message');

        program.parse();
        const options = program.opts();
        
        // Initialize logger
        logger = new Logger(options.verbose);
        
        // Ensure log directory exists
        await fs.mkdir(LOG_DIR, { recursive: true });
        
        logger.debug('Script started with options:', JSON.stringify(options, null, 2));
        
        // Load configuration
        const config = await loadConfig(options.config);
        logger.debug(`Using configuration: ${JSON.stringify(config, null, 2)}`);
        
        // Validate inputs
        await validateInputs(options);
        
        // Dry run check
        if (options.dryRun) {
            logger.info('DRY RUN: Would process data without making changes');
            logger.info(`Input: ${options.input}`);
            logger.info(`Output: ${options.output || 'stdout'}`);
            return 0;
        }
        
        // Process data
        const results = await processData(options.input, config);
        
        // Save results
        await saveResults(results, options.output);
        
        logger.info('Script completed successfully');
        return 0;
        
    } catch (err) {
        if (logger) {
            if (err instanceof ScriptError) {
                logger.error(`Script error: ${err.message}`);
            } else {
                logger.error(`Unexpected error: ${err.message}`);
                if (err.stack) {
                    logger.debug(`Stack trace: ${err.stack}`);
                }
            }
        } else {
            console.error('Error:', err.message);
        }
        return 1;
    }
}

// Handle process signals
process.on('SIGINT', async () => {
    if (logger) {
        logger.info('Script interrupted by user');
    }
    process.exit(1);
});

process.on('uncaughtException', async (err) => {
    if (logger) {
        logger.error(`Uncaught exception: ${err.message}`);
    }
    console.error('Uncaught Exception:', err);
    process.exit(1);
});

// Execute main function if script is run directly
if (require.main === module) {
    main().then(exitCode => {
        process.exit(exitCode);
    }).catch(err => {
        console.error('Fatal error:', err);
        process.exit(1);
    });
}

module.exports = {
    main,
    processData,
    saveResults,
    loadConfig,
    validateInputs,
    ScriptError,
    Logger
};