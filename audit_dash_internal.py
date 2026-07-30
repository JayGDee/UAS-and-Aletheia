"""
Audit Dashboard Generator
Generates an HTML viewer for ALL UAS/Aletheia/AER JSON files in a directory.
Automatically pairs UAS decisions with Aletheia UBOs.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import List, Dict, Optional

def find_all_json_files(directory: str = ".") -> Dict[str, List[str]]:
    """
    Categorize all JSON files in directory.
    Returns dict with keys: 'uas', 'aletheia', 'aer', 'other'
    """
    files = {
        'uas': [],
        'aletheia': [],
        'aer': [],
        'other': []
    }
    
    for filename in os.listdir(directory):
        if not filename.endswith('.json'):
            continue
            
        if filename.startswith('uas_decision_'):
            files['uas'].append(filename)
        elif filename.startswith('aletheia_ubo_'):
            files['aletheia'].append(filename)
        elif filename.startswith('AER_'):
            files['aer'].append(filename)
        else:
            files['other'].append(filename)
    
    return files

def load_json_safe(filepath: str) -> Optional[Dict]:
    """Load JSON file safely, return None if fails"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def find_matching_aletheia(uas_data: Dict, aletheia_files: List[str], directory: str) -> Optional[tuple]:
    """
    Find Aletheia UBO that matches a UAS decision.
    Returns (filename, ubo_data, hash_valid, seal_valid) or None
    """
    # Compute hash of UAS decision
    uas_json = json.dumps(uas_data, sort_keys=True, separators=(',', ':'))
    uas_hash = hashlib.sha256(uas_json.encode('ascii')).hexdigest()
    
    for afile in aletheia_files:
        ubo_data = load_json_safe(os.path.join(directory, afile))
        if not ubo_data:
            continue
        
        # Check if decision_data_hash matches
        if ubo_data.get("decision_data_hash") == uas_hash:
            # Validate seal
            seal_input = json.dumps({
                "decision_hash": ubo_data["decision_data_hash"],
                "structure": ubo_data["decision_structure"],
                "constraints": sorted(ubo_data.get("constraint_hashes", [])),
                "result": ubo_data["verification_result"],
                "verdict": ubo_data["verdict"],
                "timestamp": ubo_data["timestamp"],
                "version": ubo_data.get("protocol_version", "v2.0")
            }, sort_keys=True, separators=(',', ':'))
            computed_seal = hashlib.sha256(seal_input.encode('ascii')).hexdigest()
            seal_valid = computed_seal == ubo_data.get("seal")
            
            return (afile, ubo_data, True, seal_valid)
    
    return None

def generate_dashboard(directory: str = ".", output_html: str = "audit_dashboard.html") -> None:
    """
    Scan directory for ALL JSON files and generate comprehensive HTML dashboard.
    """
    print(f"🔍 Scanning directory: {directory}")
    
    # Find and categorize all JSON files
    files = find_all_json_files(directory)
    
    print(f"   Found {len(files['uas'])} UAS decision files")
    print(f"   Found {len(files['aletheia'])} Aletheia UBO files")
    print(f"   Found {len(files['aer'])} AER files")
    print(f"   Found {len(files['other'])} other JSON files\n")
    
    pairs = []
    unpaired_uas = []
    unpaired_aletheia = list(files['aletheia'])
    
    # Try to pair UAS decisions with Aletheia UBOs
    for uas_file in files['uas']:
        uas_data = load_json_safe(os.path.join(directory, uas_file))
        if not uas_data:
            continue
        
        match_result = find_matching_aletheia(uas_data, files['aletheia'], directory)
        
        if match_result:
            aletheia_file, ubo_data, hash_valid, seal_valid = match_result
            unpaired_aletheia.remove(aletheia_file)
            
            pairs.append({
                "id": uas_data.get("proposal_hash", "unknown")[:8],
                "timestamp": uas_data.get("timestamp", "unknown"),
                "verdict": ubo_data["verdict"],
                "uas_file": uas_file,
                "uas_data": uas_data,
                "aletheia_file": aletheia_file,
                "ubo_data": ubo_data,
                "hash_valid": hash_valid,
                "seal_valid": seal_valid,
                "paired": True
            })
        else:
            # UAS decision without matching Aletheia
            unpaired_uas.append({
                "id": uas_data.get("proposal_hash", "unknown")[:8],
                "timestamp": uas_data.get("timestamp", "unknown"),
                "verdict": uas_data.get("verdict", "unknown"),
                "uas_file": uas_file,
                "uas_data": uas_data,
                "paired": False
            })
    
    # Sort by timestamp descending
    pairs.sort(key=lambda p: p["timestamp"], reverse=True)
    unpaired_uas.sort(key=lambda p: p["timestamp"], reverse=True)
    
    # Generate HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audit Dashboard</title>
        <meta charset="utf-8">
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 20px; 
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; }}
            .stats {{
                display: flex;
                gap: 20px;
                margin: 20px 0;
            }}
            .stat-box {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                flex: 1;
            }}
            .stat-number {{
                font-size: 2em;
                font-weight: bold;
                color: #0066cc;
            }}
            table {{ 
                border-collapse: collapse; 
                width: 100%; 
                margin-top: 20px;
            }}
            th, td {{ 
                border: 1px solid #ddd; 
                padding: 12px; 
                text-align: left; 
            }}
            th {{ 
                background-color: #0066cc; 
                color: white;
                font-weight: 600;
            }}
            .pass {{ background-color: #d4edda; color: #155724; }}
            .fail {{ background-color: #f8d7da; color: #721c24; }}
            .refuse {{ background-color: #fff3cd; color: #856404; }}
            .unpaired {{ background-color: #e2e3e5; color: #383d41; }}
            .details {{ 
                display: none; 
                background-color: #f9f9f9; 
                padding: 15px;
            }}
            .details h3 {{
                margin-top: 0;
                color: #0066cc;
            }}
            pre {{ 
                white-space: pre-wrap; 
                background: #f4f4f4;
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
            }}
            .clickable {{ cursor: pointer; }}
            .clickable:hover {{ background-color: #f0f0f0; }}
            .badge {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 0.85em;
                font-weight: bold;
            }}
            .badge-success {{ background-color: #28a745; color: white; }}
            .badge-danger {{ background-color: #dc3545; color: white; }}
            .section {{
                margin-top: 40px;
            }}
            .refresh-btn {{
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 1em;
            }}
            .refresh-btn:hover {{
                background-color: #0052a3;
            }}
        </style>
        <script>
            function toggleDetails(id) {{
                var details = document.getElementById(id);
                details.style.display = (details.style.display === 'none') ? 'block' : 'none';
            }}
            async function refreshDashboard() {{
                // Show loading state
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '🔄 Refreshing...';
                btn.disabled = true;
                
                try {{
                    // Call regenerate endpoint
                    const response = await fetch('/regenerate');
                    if (response.ok) {{
                        // Reload page after regeneration
                        location.reload();
                    }} else {{
                        alert('Refresh failed. Please run: python audit_dash.py');
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }}
                }} catch (error) {{
                    // If no server, just reload (manual regeneration needed)
                    alert('No server running. Please run: python audit_dash.py');
                    btn.textContent = originalText;
                    btn.disabled = false;
                }}
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Audit Dashboard</h1>
            <p><strong>Generated:</strong> {now}</p>
            <button class="refresh-btn" onclick="refreshDashboard()">🔄 Refresh Dashboard</button>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">{paired_count}</div>
                    <div>Paired Records (UAS + Aletheia)</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{unpaired_count}</div>
                    <div>Unpaired UAS Decisions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{aer_count}</div>
                    <div>AER Files</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{other_count}</div>
                    <div>Other JSON Files</div>
                </div>
            </div>
            
            <div class="section">
                <h2>📋 Paired Records (UAS + Aletheia)</h2>
                <p>Click a row to view details</p>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Timestamp</th>
                        <th>Verdict</th>
                        <th>Hash Valid</th>
                        <th>Seal Valid</th>
                        <th>Files</th>
                    </tr>
    """.format(
        now=datetime.now().isoformat(),
        paired_count=len(pairs),
        unpaired_count=len(unpaired_uas),
        aer_count=len(files['aer']),
        other_count=len(files['other'])
    )
    
    # Add paired records
    for pair in pairs:
        verdict_class = pair["verdict"].lower()
        details_id = f"details_paired_{pair['id']}"
        hash_status = "✅" if pair['hash_valid'] else "❌"
        seal_status = "✅" if pair['seal_valid'] else "❌"
        
        html += f"""
            <tr onclick="toggleDetails('{details_id}')" class="clickable {verdict_class}">
                <td>{pair['id']}</td>
                <td>{pair['timestamp']}</td>
                <td><strong>{pair['verdict']}</strong></td>
                <td>{hash_status}</td>
                <td>{seal_status}</td>
                <td><small>{pair['uas_file']}<br>{pair['aletheia_file']}</small></td>
            </tr>
            <tr>
                <td colspan="6" id="{details_id}" class="details">
                    <h3>📄 Files</h3>
                    <p><strong>UAS Decision:</strong> <code>{pair['uas_file']}</code></p>
                    <p><strong>Aletheia UBO:</strong> <code>{pair['aletheia_file']}</code></p>
                    
                    <h3>📥 Inputs (Proposal)</h3>
                    <pre>{json.dumps(pair['uas_data'].get('original_proposal', {}), indent=2)}</pre>
                    
                    <h3>📜 Applied Rules (Constraints)</h3>
                    <pre>{json.dumps(pair['uas_data'].get('applied_constraints', []), indent=2)}</pre>
                    
                    <h3>⚖️ Decision</h3>
                    <p><strong>Verdict:</strong> {pair['verdict']}</p>
                    <p><strong>Reason:</strong> {pair['uas_data'].get('reason', 'N/A')}</p>
                    
                    <h3>🔐 Hash/Seal Confirmation</h3>
                    <p><strong>Hash Valid:</strong> {pair['hash_valid']}</p>
                    <p><strong>Seal Valid:</strong> {pair['seal_valid']}</p>
                    <p><strong>Proposal Hash:</strong> <code>{pair['uas_data'].get('proposal_hash', 'N/A')}</code></p>
                    <p><strong>Decision Hash:</strong> <code>{pair['ubo_data'].get('decision_data_hash', 'N/A')}</code></p>
                    <p><strong>Seal:</strong> <code>{pair['ubo_data'].get('seal', 'N/A')}</code></p>
                    
                    <h3>📋 Full UAS Decision</h3>
                    <pre>{json.dumps(pair['uas_data'], indent=2)}</pre>
                    
                    <h3>🔏 Full Aletheia UBO</h3>
                    <pre>{json.dumps(pair['ubo_data'], indent=2)}</pre>
                </td>
            </tr>
        """
    
    if not pairs:
        html += """
            <tr>
                <td colspan="6" style="text-align: center; padding: 20px; color: #666;">
                    No paired records found
                </td>
            </tr>
        """
    
    html += """
                </table>
            </div>
    """
    
    # Add unpaired UAS decisions section
    if unpaired_uas:
        html += """
            <div class="section">
                <h2>⚠️ Unpaired UAS Decisions (No Matching Aletheia UBO)</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Timestamp</th>
                        <th>Verdict</th>
                        <th>File</th>
                    </tr>
        """
        
        for item in unpaired_uas:
            verdict_class = item["verdict"].lower()
            details_id = f"details_unpaired_{item['id']}"
            
            html += f"""
                <tr onclick="toggleDetails('{details_id}')" class="clickable unpaired">
                    <td>{item['id']}</td>
                    <td>{item['timestamp']}</td>
                    <td>{item['verdict']}</td>
                    <td><small>{item['uas_file']}</small></td>
                </tr>
                <tr>
                    <td colspan="4" id="{details_id}" class="details">
                        <h3>📄 File</h3>
                        <p><code>{item['uas_file']}</code></p>
                        <h3>📋 Full UAS Decision</h3>
                        <pre>{json.dumps(item['uas_data'], indent=2)}</pre>
                    </td>
                </tr>
            """
        
        html += """
                </table>
            </div>
        """
    
    # Add AER files section
    if files['aer']:
        html += """
            <div class="section">
                <h2>📑 Audit Evidence Records (AER)</h2>
                <table>
                    <tr>
                        <th>Filename</th>
                        <th>Context</th>
                        <th>Verdict</th>
                    </tr>
        """
        
        for aer_file in files['aer']:
            aer_data = load_json_safe(os.path.join(directory, aer_file))
            if aer_data:
                details_id = f"details_aer_{aer_file.replace('.', '_')}"
                verdict = aer_data.get('verdict', 'unknown')
                context = aer_data.get('context', 'N/A')
                
                html += f"""
                    <tr onclick="toggleDetails('{details_id}')" class="clickable">
                        <td><code>{aer_file}</code></td>
                        <td>{context}</td>
                        <td>{verdict}</td>
                    </tr>
                    <tr>
                        <td colspan="3" id="{details_id}" class="details">
                            <pre>{json.dumps(aer_data, indent=2)}</pre>
                        </td>
                    </tr>
                """
        
        html += """
                </table>
            </div>
        """
    
    # Add other JSON files section
    if files['other']:
        html += """
            <div class="section">
                <h2>📎 Other JSON Files</h2>
                <table>
                    <tr>
                        <th>Filename</th>
                    </tr>
        """
        
        for other_file in files['other']:
            other_data = load_json_safe(os.path.join(directory, other_file))
            if other_data:
                details_id = f"details_other_{other_file.replace('.', '_')}"
                
                html += f"""
                    <tr onclick="toggleDetails('{details_id}')" class="clickable">
                        <td><code>{other_file}</code></td>
                    </tr>
                    <tr>
                        <td id="{details_id}" class="details">
                            <pre>{json.dumps(other_data, indent=2)}</pre>
                        </td>
                    </tr>
                """
        
        html += """
                </table>
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Dashboard generated: {output_html}")
    print(f"   {len(pairs)} paired records")
    print(f"   {len(unpaired_uas)} unpaired UAS decisions")
    print(f"   {len(files['aer'])} AER files")
    print(f"   {len(files['other'])} other JSON files")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        # Start web server with auto-refresh
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        import threading
        
        class DashboardHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/regenerate':
                    # Regenerate dashboard
                    print("🔄 Regenerating dashboard...")
                    generate_dashboard()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Dashboard regenerated')
                else:
                    # Serve files normally
                    super().do_GET()
        
        # Generate initial dashboard
        generate_dashboard()
        
        # Start server
        PORT = 8000
        server = HTTPServer(('', PORT), DashboardHandler)
        print(f"\n✅ Dashboard server running at http://localhost:{PORT}/audit_dashboard.html")
        print(f"   Click 'Refresh Dashboard' button to reload with new files")
        print(f"   Press Ctrl+C to stop\n")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped")
    else:
        # Just generate dashboard
        generate_dashboard()
        print("\n💡 To enable auto-refresh, run: python audit_dash.py --serve")