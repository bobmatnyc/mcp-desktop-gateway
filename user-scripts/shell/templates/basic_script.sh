#!/bin/bash

#------------------------------------------------------------------------------
# Task: [Brief description of what this script does]
# Created: [YYYY-MM-DD]
# Author: [Creator name/identifier]
#
# Description:
#   [Detailed description of the script's purpose, inputs, outputs, and behavior]
#
# Usage:
#   ./basic_script.sh [OPTIONS] <input>
#   
#   Options:
#     -i, --input FILE     Input file or data source (required)
#     -o, --output FILE    Output file (default: stdout)
#     -c, --config FILE    Configuration file path
#     -v, --verbose        Enable verbose logging
#     -n, --dry-run        Show what would be done without executing
#     -h, --help           Show this help message
#
#   Examples:
#     ./basic_script.sh --input data.txt --output results.txt
#     ./basic_script.sh --input data.csv --verbose
#     ./basic_script.sh --help
#
# Dependencies:
#   - bash 4.0+
#   - Required tools: [list tools]
#
# Notes:
#   - [Any important notes or limitations]
#   - [Performance considerations]
#   - [Known issues or workarounds]
#------------------------------------------------------------------------------

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

# Global variables
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
readonly LOG_DIR="$PROJECT_ROOT/user-scripts/shared/logs"
readonly LOG_FILE="$LOG_DIR/script.log"

# Default values
INPUT_FILE=""
OUTPUT_FILE=""
CONFIG_FILE=""
VERBOSE=false
DRY_RUN=false

# Colors for output (if terminal supports it)
if [[ -t 1 ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly NC='\033[0m' # No Color
else
    readonly RED=""
    readonly GREEN=""
    readonly YELLOW=""
    readonly BLUE=""
    readonly NC=""
fi

#------------------------------------------------------------------------------
# Logging functions
#------------------------------------------------------------------------------

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    
    # Ensure log directory exists
    mkdir -p "$LOG_DIR"
    
    # Write to log file
    echo "$timestamp - $level - $message" >> "$LOG_FILE"
    
    # Write to console based on level and verbosity
    case "$level" in
        ERROR)
            echo -e "${RED}ERROR: $message${NC}" >&2
            ;;
        WARN)
            echo -e "${YELLOW}WARN: $message${NC}" >&2
            ;;
        INFO)
            echo -e "${GREEN}INFO: $message${NC}"
            ;;
        DEBUG)
            if [[ "$VERBOSE" == true ]]; then
                echo -e "${BLUE}DEBUG: $message${NC}"
            fi
            ;;
    esac
}

log_error() { log "ERROR" "$@"; }
log_warn() { log "WARN" "$@"; }
log_info() { log "INFO" "$@"; }
log_debug() { log "DEBUG" "$@"; }

#------------------------------------------------------------------------------
# Error handling
#------------------------------------------------------------------------------

cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Script failed with exit code $exit_code"
    fi
    # Add any cleanup tasks here
    exit $exit_code
}

trap cleanup EXIT
trap 'log_error "Script interrupted by user"; exit 1' INT TERM

#------------------------------------------------------------------------------
# Utility functions
#------------------------------------------------------------------------------

show_help() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] 

[Brief description of what this script does]

OPTIONS:
    -i, --input FILE     Input file or data source (required)
    -o, --output FILE    Output file (default: stdout)
    -c, --config FILE    Configuration file path
    -v, --verbose        Enable verbose logging
    -n, --dry-run        Show what would be done without executing
    -h, --help           Show this help message

EXAMPLES:
    $SCRIPT_NAME --input data.txt --output results.txt
    $SCRIPT_NAME --input data.csv --verbose
    $SCRIPT_NAME --help

For more information, see the README.md file in the user-scripts directory.
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--input)
                INPUT_FILE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

validate_inputs() {
    local errors=0
    
    # Check required arguments
    if [[ -z "$INPUT_FILE" ]]; then
        log_error "Input file is required. Use --input to specify."
        ((errors++))
    fi
    
    # Check input file exists
    if [[ -n "$INPUT_FILE" && ! -f "$INPUT_FILE" ]]; then
        log_error "Input file does not exist: $INPUT_FILE"
        ((errors++))
    fi
    
    # Check input file is readable
    if [[ -n "$INPUT_FILE" && ! -r "$INPUT_FILE" ]]; then
        log_error "Input file is not readable: $INPUT_FILE"
        ((errors++))
    fi
    
    # Create output directory if needed
    if [[ -n "$OUTPUT_FILE" ]]; then
        local output_dir
        output_dir="$(dirname "$OUTPUT_FILE")"
        if [[ ! -d "$output_dir" ]]; then
            if mkdir -p "$output_dir"; then
                log_debug "Created output directory: $output_dir"
            else
                log_error "Failed to create output directory: $output_dir"
                ((errors++))
            fi
        fi
    fi
    
    # Check config file if specified
    if [[ -n "$CONFIG_FILE" && ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file does not exist: $CONFIG_FILE"
        ((errors++))
    fi
    
    if [[ $errors -gt 0 ]]; then
        log_error "Validation failed with $errors error(s)"
        exit 1
    fi
}

load_config() {
    # Default configuration
    local timeout=30
    local max_retries=3
    local batch_size=100
    
    # Load from config file if provided
    if [[ -n "$CONFIG_FILE" && -f "$CONFIG_FILE" ]]; then
        log_info "Loading configuration from $CONFIG_FILE"
        
        # Source the config file (assuming it's a bash script with variables)
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
        
        log_debug "Configuration loaded successfully"
    fi
    
    # Export variables for use in other functions
    export TIMEOUT="$timeout"
    export MAX_RETRIES="$max_retries"
    export BATCH_SIZE="$batch_size"
    
    log_debug "Using configuration: timeout=$TIMEOUT, max_retries=$MAX_RETRIES, batch_size=$BATCH_SIZE"
}

#------------------------------------------------------------------------------
# Main processing functions
#------------------------------------------------------------------------------

process_data() {
    local input_file="$1"
    local total_lines
    local processed_lines=0
    
    log_info "Processing data from $input_file"
    
    # Count total lines for progress tracking
    total_lines=$(wc -l < "$input_file")
    log_debug "Total lines to process: $total_lines"
    
    # Process the file line by line
    while IFS= read -r line || [[ -n "$line" ]]; do
        ((processed_lines++))
        
        # Skip empty lines
        if [[ -z "$(echo "$line" | tr -d '[:space:]')" ]]; then
            continue
        fi
        
        # TODO: Add your processing logic here
        # Example: process each line
        local processed_line
        processed_line="$(echo "$line" | tr '[:lower:]' '[:upper:]')"  # Example transformation
        
        # Output the processed line
        if [[ -n "$OUTPUT_FILE" ]]; then
            echo "$processed_line" >> "$OUTPUT_FILE"
        else
            echo "$processed_line"
        fi
        
        # Progress reporting
        if (( processed_lines % BATCH_SIZE == 0 )); then
            log_info "Processed $processed_lines/$total_lines lines"
        fi
        
    done < "$input_file"
    
    log_info "Successfully processed $processed_lines lines"
}

#------------------------------------------------------------------------------
# Main function
#------------------------------------------------------------------------------

main() {
    log_info "Starting $SCRIPT_NAME"
    log_debug "Script arguments: $*"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Load configuration
    load_config
    
    # Validate inputs
    validate_inputs
    
    # Show what would be done in dry-run mode
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN: Would process data without making changes"
        log_info "Input: $INPUT_FILE"
        log_info "Output: ${OUTPUT_FILE:-stdout}"
        log_info "Config: ${CONFIG_FILE:-default}"
        return 0
    fi
    
    # Process the data
    process_data "$INPUT_FILE"
    
    log_info "Script completed successfully"
}

#------------------------------------------------------------------------------
# Script execution
#------------------------------------------------------------------------------

# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi