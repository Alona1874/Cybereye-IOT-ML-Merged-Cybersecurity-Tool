# ================== CyberEye Backend + Dashboard ==================
import os
import json
import logging
import csv
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, url_for, flash, session, send_file
# Note: session and send_file are imported for feature support

# ================== Flask App Setup ==================
app = Flask(__name__)
app.secret_key = "supersecretkey" # Required for using flash and session

DATA_FILE = "cyber_logs.json"
AUTHORIZED_CODES = {"ABC123", "XYZ789"}
DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Ensure JSON file exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        # Initial log structure for testing visualizations
        initial_logs = [
            {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "direction": "OUT", "tag": "LOGIN", "sender": "user1", "receiver": "ext-server", "ip": "192.168.1.5", "length": 512, "status": "OK", "class": "NORMAL"},
            {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "direction": "IN", "tag": "ACCESS_DENIED", "sender": "attacker", "receiver": "api", "ip": "10.0.0.10", "length": 1024, "status": "FAIL", "class": "CRITICAL"},
        ]
        json.dump(initial_logs, f, indent=2)

# ================== Data Processing Helper ==================

def calculate_log_metrics(logs):
    """Calculates status counts and percentages for the dashboard widgets."""
    total = len(logs)
    counts = {'CRITICAL': 0, 'WARNING': 0, 'NORMAL': 0}
    
    for log in logs:
        log_class = log.get('class', 'NORMAL')
        if log_class in counts:
            counts[log_class] += 1
        
    # Calculate percentages
    metrics = {k: {'count': v, 'percent': (v / total * 100) if total > 0 else 0} for k, v in counts.items()}
    
    return metrics

# ================== Backend API ==================
@app.route("/get-data", methods=["GET"])
def get_data():
    with open(DATA_FILE, "r") as f:
        dataset = json.load(f)
    app.logger.info("✅ Dataset requested by ESP or dashboard")
    return jsonify(dataset)

@app.route("/update-log", methods=["POST"])
def update_log():
    try:
        new_log = request.get_json()
        if not new_log:
            return jsonify({"error": "Invalid JSON"}), 400

        new_log["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(DATA_FILE, "r") as f:
            logs = json.load(f)

        logs.append(new_log)

        # Keep only latest 15 logs
        if len(logs) > 15:
            logs = logs[-15:]

        with open(DATA_FILE, "w") as f:
            json.dump(logs, f, indent=2)

        app.logger.info(f"✅ New log appended: {new_log.get('tag', '')} from {new_log.get('sender', '')}")
        return jsonify({"message": "Log updated successfully"}), 200
    except Exception as e:
        app.logger.error(f"❌ Failed to update log: {e}")
        return jsonify({"error": str(e)}), 500

# ================== Dashboard Export Feature ==================
@app.route("/download-logs")
def download_logs():
    # Load data
    with open(DATA_FILE, "r") as f:
        logs = json.load(f)

    if not logs:
        flash("No logs to export.", "warning")
        return redirect(url_for("dashboard"))

    # Create temporary CSV file path
    csv_filename = f"cybereye_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_filepath = os.path.join(DATA_FOLDER, csv_filename)
    
    # Use keys from the first log entry as field names
    fieldnames = logs[0].keys() 

    with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(logs)

    # Send the CSV file
    return send_file(csv_filepath, 
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=csv_filename)

# ================== Dashboard HTML (Light Theme) ==================
dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>CyberEye Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        /* Light Theme Styling */
        body { background-color: #f8f9fa; color: #343a40; font-family: 'Segoe UI', sans-serif; }
        .dashboard-container { max-width: 1200px; margin: 40px auto; padding: 30px; border-radius: 12px; background-color: #ffffff; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); border: 1px solid #dee2e6; }
        
        /* Metrics Cards */
        .metric-card { background-color: #f1f3f5; border-radius: 8px; padding: 15px; border-left: 5px solid; transition: transform 0.2s; }
        .metric-card:hover { transform: translateY(-3px); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08); }
        .metric-card h3 { font-size: 2em; margin-bottom: 0.1em; }
        
        .critical-border { border-left-color: #dc3545 !important; }
        .warning-border { border-left-color: #ffc107 !important; }
        .normal-border { border-left-color: #28a745 !important; }

        /* Table Styling */
        .table { --bs-table-bg: #ffffff; --bs-table-color: #343a40; --bs-table-border-color: #e9ecef; }
        .table-striped>tbody>tr:nth-of-type(odd)>* { --bs-table-bg-type: #f8f9fa; }
        .table thead th { background-color: #e9ecef; color: #495057; border-bottom: 2px solid #adb5bd; font-weight: bold; }
        .badge { padding: 5px 10px; border-radius: 4px; font-weight: 700; }
        
        /* Status Badge Styling */
        .NORMAL { background-color: #28a745; color: white; } 
        .WARNING { background-color: #ffc107; color: #343a40; } 
        .CRITICAL { background-color: #dc3545; color: white; } 
        
        .text-primary-header { color: #007bff; font-weight: 600; }
        
        /* Responsive Table Adjustments */
        @media (max-width: 800px) {
            .table thead { display: none; }
            .table tbody td { 
                display: block; text-align: right; padding-left: 50%; position: relative; border-top: none; border-bottom: 1px solid #e9ecef;
            }
            .table tbody td::before {
                content: attr(data-label); position: absolute; left: 10px; width: 45%; text-align: left; font-weight: bold; color: #adb5bd;
            }
        }
    </style>
</head>
<body>
    <div class="container dashboard-container">
        <h2 class="text-center mb-5 text-primary-header"><i class="fas fa-desktop me-2"></i> CyberEye Security Operations Dashboard</h2>
        
        {# Flashed Messages #}
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'success' if category == 'success' else 'warning' if category == 'error' else 'info' }} mt-3" role="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {# Metrics and Controls Row #}
        <div class="row mb-4 align-items-center">
            
            {# Status Breakdown Widgets #}
            <div class="col-md-7">
                <div class="row">
                    <h5 class="text-secondary border-bottom border-light-subtle pb-2 mb-3"><i class="fas fa-chart-pie me-2"></i> Current Status Breakdown</h5>
                    <div class="col-4 p-1">
                        <div class="metric-card critical-border">
                            <p class="text-danger mb-0 small fw-bold">CRITICAL</p>
                            <h3 class="text-danger">{{ metrics.CRITICAL.count }}</h3>
                            <small class="text-muted">{{ "%.1f"|format(metrics.CRITICAL.percent) }}%</small>
                        </div>
                    </div>
                    <div class="col-4 p-1">
                        <div class="metric-card warning-border">
                            <p class="text-warning mb-0 small fw-bold">WARNING</p>
                            <h3 class="text-warning">{{ metrics.WARNING.count }}</h3>
                            <small class="text-muted">{{ "%.1f"|format(metrics.WARNING.percent) }}%</small>
                        </div>
                    </div>
                    <div class="col-4 p-1">
                        <div class="metric-card normal-border">
                            <p class="text-success mb-0 small fw-bold">NORMAL</p>
                            <h3 class="text-success">{{ metrics.NORMAL.count }}</h3>
                            <small class="text-muted">{{ "%.1f"|format(metrics.NORMAL.percent) }}%</small>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-5">
                <div class="card p-3 bg-light">
                    <h5 class="text-secondary border-bottom border-light-subtle pb-2"><i class="fas fa-cogs me-2"></i> System Controls</h5>
                    <p class="text-dark mb-2">Total Log Records: {{ logs|length }}.</p>
                    <div class="d-flex justify-content-end">
                         <a href="{{ url_for('download_logs') }}" class="btn btn-outline-primary me-2"><i class="fas fa-file-download me-2"></i> Export Logs (CSV)</a>
                         <a href="{{ url_for('login') }}" class="btn btn-outline-secondary"><i class="fas fa-sign-out-alt me-2"></i> Logout</a>
                    </div>
                </div>
            </div>
        </div>
        
        <h5 class="text-secondary border-bottom border-light-subtle pb-2 mb-3"><i class="fas fa-list me-2"></i> Detailed Log Feed</h5>
        <div class="table-responsive">
            <table class="table table-striped table-hover align-middle">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Direction</th>
                        <th>Code</th>
                        <th>From</th>
                        <th>To</th>
                        <th>IP</th>
                        <th>Length (B)</th>
                        <th>Status</th>
                        <th>Classifier</th>
                    </tr>
                </thead>
                <tbody>
                {% for log in logs %}
                    <tr>
                        <td data-label="Timestamp">{{ log.timestamp }}</td>
                        <td data-label="Direction">OUT</td>
                        <td data-label="Code">{{ log.tag }}</td>
                        <td data-label="From">{{ log.sender }}</td>
                        <td data-label="To">{{ log.receiver }}</td>
                        <td data-label="IP">{{ log.ip }}</td>
                        <td data-label="Length (B)">{{ log.length }}</td>
                        <td data-label="Status">
                            <span class="badge {{ log.class }}">{{ log.status }}</span>
                        </td>
                        <td data-label="Classifier">
                            <span class="badge {{ log.class }}">{{ log.class }}</span>
                        </td>
                    </tr>
                {% else %}
                    <tr>
                        <td colspan="9" class="text-center text-secondary">No logs available in the system. Check API connection.</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route("/dashboard")
def dashboard():
    # Session check is omitted as it was removed in the base code.
        
    with open(DATA_FILE, "r") as f:
        logs = json.load(f)
        # Reverse logs so the table shows the newest logs first (standard dashboard practice)
        logs.reverse() 

    # Calculate metrics
    metrics = calculate_log_metrics(logs)
    
    return render_template_string(dashboard_html, logs=logs, metrics=metrics)

# ================== Portal Login HTML (Light Theme) ==================
login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>CyberEye Portal - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; color: #343a40; }
        .login-container { max-width: 400px; margin-top: 100px; padding: 30px; border-radius: 8px; box-shadow: 0 0 15px rgba(0, 0, 0, 0.1); background-color: #ffffff; border: 1px solid #dee2e6; }
        .text-primary-header { color: #007bff !important; text-shadow: 0 0 1px rgba(0, 123, 255, 0.2); }
        .form-control { background-color: #ffffff; border-color: #ced4da; color: #495057; }
        .form-control:focus { border-color: #007bff; box-shadow: 0 0 0 0.25rem rgba(0, 123, 255, 0.25); }
    </style>
</head>
<body>
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-6 login-container">
            <h2 class="text-center mb-4 text-primary-header"><i class="fas fa-lock me-2"></i> CyberEye Access Portal</h2>
            
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="alert alert-danger" role="alert">{% for message in messages %} {{ message }} {% endfor %}</div>
              {% endif %}
            {% endwith %}
            
            <form method="post">
                <div class="mb-3">
                    <label for="auth_code" class="form-label">Enter Authorization Code:</label>
                    <input type="text" class="form-control" id="auth_code" name="auth_code" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">Access Dashboard</button>
            </form>
        </div>
    </div>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form.get("auth_code")
        if code in AUTHORIZED_CODES:
            session["logged_in"] = True 
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Unauthorized code!")
    return render_template_string(login_html)

# ================== Main ==================
if __name__ == "__main__":
    HOST_IP = "0.0.0.0"
    PORT = 5000
    dashboard_url = f"http://localhost:{PORT}/dashboard" 

    print(f"🚀 Flask backend + dashboard running at {dashboard_url}")
    app.logger.info(f"🚀 Flask backend + dashboard running at {dashboard_url}")
    app.run(host=HOST_IP, port=PORT, debug=True)
