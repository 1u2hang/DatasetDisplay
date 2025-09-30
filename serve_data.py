#!/usr/bin/env python3
"""
HTTP server to serve CSV data for the CSV visualizer.
Handles CSV serving, label updates, and labeled CSV creation.
"""

import http.server
import socketserver
import os
import sys
import csv
import json
import shutil
from pathlib import Path

def start_server(port=8000, csv_file="data.csv"):
    """
    Start a simple HTTP server to serve the CSV file.
    
    Args:
        port (int): Port number to serve on
        csv_file (str): Name of the CSV file to serve
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    # Support absolute or relative csv path
    csv_path = Path(csv_file) if os.path.isabs(csv_file) else (script_dir / csv_file)
    served_name = csv_path.name
    
    if not csv_path.exists():
        print(f"❌ Error: CSV file '{csv_file}' not found")
        print(f"   Please make sure the CSV file exists")
        sys.exit(1)
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Create a custom handler that serves the CSV file
    class CSVHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Add CORS headers to allow cross-origin requests
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
        
        def do_OPTIONS(self):
            # Handle CORS preflight
            self.send_response(200)
            self.end_headers()

        def do_GET(self):
            # If requesting the CSV file, serve it with proper headers
            if self.path == f'/{served_name}' or self.path == '/csv':
                try:
                    with open(csv_path, 'rb') as f:
                        content = f.read()
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/csv')
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception as e:
                    self.send_error(500, f"Error reading CSV file: {e}")
                    return
            
            # For all other requests, use default behavior
            super().do_GET()

        def do_POST(self):
            # Endpoint: /update_label
            if self.path == '/update_label':
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    raw = self.rfile.read(length) if length > 0 else b''
                    payload = json.loads(raw.decode('utf-8')) if raw else {}

                    row_index = payload.get('row')
                    column = payload.get('column')
                    label_name = payload.get('labelName')
                    value = payload.get('value')

                    if row_index is None or column is None or label_name is None or value is None:
                        self.send_error(400, 'Missing required parameters')
                        return

                    # Read CSV into memory
                    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        rows = list(reader)

                    if not rows:
                        self.send_error(500, 'CSV is empty')
                        return

                    header = rows[0]
                    
                    # Add label column if it doesn't exist
                    if label_name not in header:
                        header.append(label_name)
                        # Initialize existing rows with empty value
                        for i in range(1, len(rows)):
                            rows[i].append('')
                        label_col = len(header) - 1
                    else:
                        label_col = header.index(label_name)

                    # CSV row index provided is 0-based relative to data rows
                    data_row_idx = row_index + 1  # account for header
                    if data_row_idx < 1 or data_row_idx >= len(rows):
                        self.send_error(400, f'Row index out of range: {row_index}')
                        return

                    # Ensure the row has enough columns
                    while len(rows[data_row_idx]) < len(header):
                        rows[data_row_idx].append('')

                    rows[data_row_idx][label_col] = str(value)

                    # Write back to CSV atomically
                    tmp_path = csv_path.with_suffix('.csv.tmp')
                    with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(rows)
                    os.replace(tmp_path, csv_path)

                    # Create labeled CSV if in label mode
                    labeled_csv_path = csv_path.parent / f"{csv_path.stem}_labeled.csv"
                    shutil.copy2(csv_path, labeled_csv_path)

                    # Success response
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'ok': True,
                        'row': row_index,
                        'column': column,
                        'labelName': label_name,
                        'value': value,
                        'labeledCsvPath': str(labeled_csv_path)
                    }).encode('utf-8'))
                    return
                    
                except json.JSONDecodeError:
                    self.send_error(400, 'Invalid JSON payload')
                    return
                except Exception as e:
                    self.send_error(500, f'Failed to update CSV: {e}')
                    return
            
            # Endpoint: /add_column
            if self.path == '/add_column':
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    raw = self.rfile.read(length) if length > 0 else b''
                    payload = json.loads(raw.decode('utf-8')) if raw else {}

                    column_name = payload.get('column')

                    if not column_name or not isinstance(column_name, str):
                        self.send_error(400, 'Missing or invalid column name')
                        return

                    # Read CSV into memory
                    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        rows = list(reader)

                    if not rows:
                        self.send_error(500, 'CSV is empty')
                        return

                    header = rows[0]

                    # If column already exists, no-op
                    if column_name in header:
                        # Still copy to labeled CSV for consistency
                        labeled_csv_path = csv_path.parent / f"{csv_path.stem}_labeled.csv"
                        shutil.copy2(csv_path, labeled_csv_path)

                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            'ok': True,
                            'message': 'Column already exists',
                            'column': column_name,
                        }).encode('utf-8'))
                        return

                    # Append the new column to header
                    header.append(column_name)
                    # Ensure every existing row has an empty value for this new column
                    for i in range(1, len(rows)):
                        rows[i].append('')

                    # Write back to CSV atomically
                    tmp_path = csv_path.with_suffix('.csv.tmp')
                    with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(rows)
                    os.replace(tmp_path, csv_path)

                    # Update labeled CSV snapshot
                    labeled_csv_path = csv_path.parent / f"{csv_path.stem}_labeled.csv"
                    shutil.copy2(csv_path, labeled_csv_path)

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'ok': True,
                        'message': 'Column added',
                        'column': column_name,
                    }).encode('utf-8'))
                    return

                except json.JSONDecodeError:
                    self.send_error(400, 'Invalid JSON payload')
                    return
                except Exception as e:
                    self.send_error(500, f'Failed to add column: {e}')
                    return
            
            # Unknown POST path
            self.send_error(404, 'Not Found')
    
    try:
        with socketserver.TCPServer(("", port), CSVHandler) as httpd:
            print(f"🚀 CSV Data Visualizer Server")
            print(f"=" * 40)
            print(f"📁 Serving from: {script_dir}")
            print(f"📊 CSV file: {csv_path}")
            print(f"🌐 Server running at: http://localhost:{port}")
            print(f"📱 Open in browser: http://localhost:{port}/csv_visualizer.html")
            print(f"🔗 CSV URL: http://localhost:{port}/{served_name} (alias: /csv)")
            print(f"⏹️  Press Ctrl+C to stop the server")
            print(f"=" * 40)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ Error: Port {port} is already in use")
            print(f"   Try a different port: python serve_data.py --port 8001")
        else:
            print(f"❌ Error starting server: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Serve CSV data for the visualizer")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port number to serve on (default: 8000)"
    )
    parser.add_argument(
        "--csv", "-c",
        default="data.csv",
        help="CSV file to serve (default: data.csv)"
    )
    
    args = parser.parse_args()
    
    start_server(port=args.port, csv_file=args.csv)

if __name__ == "__main__":
    main()

