#!/bin/bash

# CSV Data Visualizer Launch Script
# This script helps you easily start the CSV visualizer with your data

echo "🚀 CSV Data Visualizer Launcher"
echo "================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "   Please install Python 3 and try again"
    exit 1
fi

# Default values
PORT=8000
CSV_FILE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -c|--csv)
            CSV_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -p, --port PORT    Port number to serve on (default: 8000)"
            echo "  -c, --csv FILE     CSV file to visualize (required)"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 -c data.csv"
            echo "  $0 -c /path/to/data.csv -p 8001"
            echo "  $0 --csv my_data.csv --port 8080"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "   Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Check if CSV file is provided
if [ -z "$CSV_FILE" ]; then
    echo "❌ Error: CSV file is required"
    echo "   Use: $0 -c your_file.csv"
    echo "   Or: $0 --csv your_file.csv"
    exit 1
fi

# Check if CSV file exists
if [ ! -f "$CSV_FILE" ]; then
    echo "❌ Error: CSV file '$CSV_FILE' not found"
    echo "   Please check the file path and try again"
    exit 1
fi

# Check if required files exist
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HTML_FILE="$SCRIPT_DIR/csv_visualizer.html"
SERVER_FILE="$SCRIPT_DIR/serve_data.py"

if [ ! -f "$HTML_FILE" ]; then
    echo "❌ Error: csv_visualizer.html not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$SERVER_FILE" ]; then
    echo "❌ Error: serve_data.py not found in $SCRIPT_DIR"
    exit 1
fi

# Make server script executable
chmod +x "$SERVER_FILE"

echo "📊 CSV File: $CSV_FILE"
echo "🌐 Port: $PORT"
echo "📁 Working Directory: $SCRIPT_DIR"
echo ""

# Start the server
echo "🚀 Starting CSV Data Visualizer Server..."
echo "   Open your browser and go to: http://localhost:$PORT/csv_visualizer.html"
echo "   Press Ctrl+C to stop the server"
echo ""

python3 "$SERVER_FILE" --port "$PORT" --csv "$CSV_FILE"

