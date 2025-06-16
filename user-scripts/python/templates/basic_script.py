#!/usr/bin/env python3
"""
Task: [Brief description of what this script does]
Created: [YYYY-MM-DD]
Author: [Creator name/identifier]

Description:
    [Detailed description of the script's purpose, inputs, outputs, and behavior]

Usage:
    python basic_script.py [arguments]
    
    Arguments:
        arg1: Description of first argument
        arg2: Description of second argument
    
    Examples:
        python basic_script.py --input data.csv --output results.json
        python basic_script.py --help

Dependencies:
    - Python 3.8+
    - Required packages: [list packages]
    
Notes:
    - [Any important notes or limitations]
    - [Performance considerations]
    - [Known issues or workarounds]
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add the project root to Python path for importing MCP modules if needed
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "user-scripts/shared/logs/script.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ScriptError(Exception):
    """Custom exception for script-specific errors."""
    pass


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="[Script description]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python basic_script.py --input data.csv
    python basic_script.py --input data.csv --output results.json --verbose
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Input file or data source'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file (default: stdout)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )
    
    return parser.parse_args()


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults."""
    default_config = {
        'timeout': 30,
        'max_retries': 3,
        'batch_size': 100,
    }
    
    if config_path and os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            default_config.update(user_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    return default_config


def validate_inputs(args: argparse.Namespace) -> None:
    """Validate input arguments and files."""
    if not os.path.exists(args.input):
        raise ScriptError(f"Input file does not exist: {args.input}")
    
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")


def process_data(input_path: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Main data processing function.
    
    Args:
        input_path: Path to input file
        config: Configuration dictionary
        
    Returns:
        List of processed data items
        
    Raises:
        ScriptError: If processing fails
    """
    logger.info(f"Processing data from {input_path}")
    
    try:
        # TODO: Implement your data processing logic here
        results = []
        
        # Example processing loop
        with open(input_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    # Process each line/item
                    processed_item = {
                        'line_number': line_num,
                        'content': line.strip(),
                        'processed_at': str(logger.handlers[0].formatter.formatTime(
                            logging.LogRecord('', 0, '', 0, '', (), None)
                        ))
                    }
                    results.append(processed_item)
                    
                    if line_num % config['batch_size'] == 0:
                        logger.info(f"Processed {line_num} items")
                        
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        logger.info(f"Successfully processed {len(results)} items")
        return results
        
    except Exception as e:
        raise ScriptError(f"Failed to process data: {e}")


def save_results(results: List[Dict[str, Any]], output_path: Optional[str] = None) -> None:
    """Save results to file or stdout."""
    import json
    
    output_data = {
        'timestamp': str(logger.handlers[0].formatter.formatTime(
            logging.LogRecord('', 0, '', 0, '', (), None)
        )),
        'total_items': len(results),
        'data': results
    }
    
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    else:
        print(json.dumps(output_data, indent=2))


def main() -> int:
    """Main script execution function."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Set log level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Verbose logging enabled")
        
        # Load configuration
        config = load_config(args.config)
        logger.debug(f"Using configuration: {config}")
        
        # Validate inputs
        validate_inputs(args)
        
        # Dry run check
        if args.dry_run:
            logger.info("DRY RUN: Would process data without making changes")
            logger.info(f"Input: {args.input}")
            logger.info(f"Output: {args.output or 'stdout'}")
            return 0
        
        # Process data
        results = process_data(args.input, config)
        
        # Save results
        save_results(results, args.output)
        
        logger.info("Script completed successfully")
        return 0
        
    except ScriptError as e:
        logger.error(f"Script error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)