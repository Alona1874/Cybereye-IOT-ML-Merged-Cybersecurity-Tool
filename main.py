# ================== CyberEye Core Logic ==================
# NOTE: This class contains the logic for generating guidance (chatbot)
class CyberEye:
    def __init__(self, portal_url="http://localhost:5000/login", auth_key="ABC123"):
        self.DELETE_LINK = portal_url
        self.auth_key = auth_key
        self.predefined_responses = {
            "protected file": (
                "Alert Meaning: You received a protected file that belongs to the company.\n"
                "Why this matters: This is unauthorized data under your possession.\n"
                f"Next Step: Review the questions carefully. Use the key sent to your email to access the delete portal: {portal_url}"
            ),
            "accidental file": (
                "Alert Meaning: You received a sensitive file by mistake.\n"
                "Why this matters: Holding unauthorized data may breach company policy.\n"
                f"Next Step: Use the key sent to your email to access the secure portal to decline/remove the data: {portal_url}"
            ),
            "shared by mistake": (
                "Alert Meaning: Confidential project files were shared with you unintentionally.\n"
                "Why this matters: You are holding data outside of encryption standards.\n"
                f"Next Step: Use the key sent to your email to access the secure portal to delete the data: {portal_url}"
            )
        }

    def get_guidance(self, alert_text):
        """Generates guidance based on keywords in the alert text."""
        alert_lower = alert_text.lower()
        
        # Check for specific, high-priority keywords
        if "protected file" in alert_lower or "confidential" in alert_lower:
            return self.predefined_responses.get("protected file")
        elif "accidental file" in alert_lower or "mistake" in alert_lower:
            return self.predefined_responses.get("accidental file")
        elif "shared by mistake" in alert_lower:
            return self.predefined_responses.get("shared by mistake")

        # Default response for other alerts
        return (
            f"Alert Meaning: This alert indicates a general risk of unauthorized data possession. \n"
            f"Next Step: Complete the email authorization below to receive your secure deletion key."
        )

# ================== CyberEye Backend + Dashboard ==================
import os
import json
import logging
import csv
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, url_for, flash, session, send_file, send_from_directory
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import webbrowser 
import threading 

# ================== Flask App Setup ==================
app = Flask(__name__)
app.secret_key = "supersecretkey" 

# Mock SMTP Configuration (replace with your actual details)
SENDER_EMAIL = "cybereye047@gmail.com"
SENDER_PASSWORD = "enxb uqyc ejhv ofre" 

DATA_FILE = "cyber_logs.json"
# Separating codes: ABC123 for Portal User, XYZ789 for Security Analyst
PORTAL_USER_CODE = "ABC123" 
ANALYST_CODE = "XYZ789"
AUTHORIZED_CODES = {PORTAL_USER_CODE, ANALYST_CODE}

# FIX 1: Updated AUTH_KEY to ABC123 as requested by the user
AUTH_KEY = "ABC123" 

DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# Define the absolute path for the image serving route
IMAGE_PATH = 'C:/Users/anusa/OneDrive/Pictures'

# Initialize CyberEye instance for guidance (will be properly initialized in __main__)
CYBER_TOOL = CyberEye() 

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

# ================== Email Functionality (FIXED) ==================
def send_authorization_email(user_email, portal_url, auth_key):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    subject = "🔒 CyberEye Security Notification & Authorization Key"
    body = f"""
🔒 Security Notification

We have detected that the dataset assosiated wuth your account does not meet required encryption standards.Our system requires verification for sensitive data possession.Please review and deactivate the data set immediately using the secure link below

Your CyberEye portal authorization key:

👉 {auth_key}

Access the secure portal (for key verification or further action):

👉 {portal_url}

Thank you,
CyberEye Security Team
"""
    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL
    message["To"] = user_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        # --- FIX: ENABLED LIVE SMTP CONNECTION ---
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(message)
        server.quit()
        app.logger.info(f"✅ Authorization key sent to {user_email}. Portal URL: {portal_url}")
        return True
    except Exception as e:
        app.logger.error(f"❌ Failed to send email: {e}")
        return False

# ================== Backend API & Logging ==================
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

# ROUTE: Securely serves the image from the user's Pictures folder
@app.route("/image/<filename>")
def serve_image(filename):
    return send_from_directory(IMAGE_PATH, filename)

# ================== Dashboard Data Processing ==================

def calculate_log_metrics(logs):
    """Calculates status counts and percentages for the dashboard widgets."""
    total = len(logs)
    counts = {'CRITICAL': 0, 'WARNING': 0, 'NORMAL': 0}
    
    for log in logs:
        log_class = log.get('class', 'NORMAL')
        if log_class in counts:
            counts[log_class] += 1
        
    metrics = {k: {'count': v, 'percent': (v / total * 100) if total > 0 else 0} for k, v in counts.items()}
    
    return metrics

# ================== Dashboard Export Feature ==================
@app.route("/download-logs")
def download_logs():
    if session.get('user_role') != 'analyst':
        flash("Access denied. Analyst privileges required.", "error")
        return redirect(url_for("login"))

    with open(DATA_FILE, "r") as f:
        logs = json.load(f)

    if not logs:
        flash("No logs to export.", "warning")
        return redirect(url_for("dashboard"))

    from flask import make_response # Must be imported or defined globally
    output = io.StringIO()
    fieldnames = logs[0].keys() 
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    
    writer.writeheader()
    writer.writerows(logs)
    
    response = make_response(output.getvalue())
    output.close()
    
    # Set headers for CSV download
    csv_filename = f"cybereye_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={csv_filename}"
    response.headers["Content-type"] = "text/csv"
    
    return response

# ================== USER PORTAL ROUTES ==================

# Verification HTML (Deep Dark Theme - Best Professional)
verification_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>CyberEye Verification</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #1a1a1a; color: #e0e0e0; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; padding-top: 40px;}
        .container { max-width: 900px; background-color: #242424; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.8); border: 1px solid #333; }
        .text-primary-header { color: #00bcd4 !important; font-weight: 700; text-shadow: 0 0 5px rgba(0, 188, 212, 0.4); }
        
        /* Cards and Contrast */
        .phase-card { background-color: #2c2c2c; border: 1px solid #444; border-radius: 8px; padding: 25px; margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5); transition: all 0.3s ease-in-out; }
        .phase-card:hover { border-color: #00bcd4; transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.6); }
        .phase-header { display: flex; align-items: center; border-bottom: 2px solid #00bcd4; padding-bottom: 10px; margin-bottom: 20px; color: #00bcd4; font-weight: 700; font-size: 1.4rem; }
        .phase-header img { height: 30px; margin-right: 10px; filter: drop-shadow(0 0 3px #00bcd4); } /* Logo Style */

        /* Form Elements - High Contrast */
        .form-control, .form-select { 
            background-color: #3a3a3a; 
            border-color: #555; 
            color: #e0e0e0; 
            font-weight: 400; 
            transition: border-color 0.3s; 
        }
        .form-control:focus, .form-select:focus { border-color: #00bcd4; box-shadow: 0 0 0 0.25rem rgba(0, 188, 212, 0.4); }
        
        /* Labels and Text Visibility */
        .form-label, .question-list label, .text-secondary { color: #bdbec1 !important; font-weight: 600; }
        
        /* Question List */
        .question-list .list-group-item { background-color: #2c2c2c; border-color: #444; margin-bottom: 12px; padding: 15px; border-radius: 6px; }
        
        /* Guidance Box (Warning/Alert Style) */
        .guidance-box { border: 2px solid #ffc107; padding: 20px; background-color: #4a422a; color: #ffebcc; border-radius: 8px; box-shadow: 0 0 10px rgba(255, 193, 7, 0.3); }
        
        /* Final Actions */
        .final-actions { padding-top: 30px; margin-top: 30px; border-top: 3px solid #dc3545; }
        
        .btn { border-radius: 6px; font-weight: 600; }
    </style>
</head>
<body>
<div class="container">
    <h2 class="text-center mb-5 text-primary-header">User Portal: Compliance Verification Terminal 🛡️</h2>
    
    <div class="text-end mb-3">
        {# Analyst Shortcut Link #}
        {% if session.get('user_role') == 'analyst' %}
        <a href="{{ url_for('dashboard') }}" class="btn btn-warning btn-sm me-2"><i class="fas fa-chart-line me-2"></i> Analyst Dashboard</a>
        {% endif %}
        <a href="{{ url_for('logout') }}" class="btn btn-outline-secondary btn-sm"><i class="fas fa-sign-out-alt me-2"></i> Logout</a>
    </div>
    
    <form method="post">
        
        {% if not session.get('deletion_ready') %}
        
            <div class="phase-card">
                <h5 class="phase-header"><img src="{{ url_for('serve_image', filename='cyberlohochatbot.jpg') }}" alt="Logo"> Phase 1: Incident Review & Verification</h5>
                
                <div class="mb-4">
                    <label for="alert_description" class="form-label fw-bold">Alert Description:</label>
                    
                    {# Logic to persist the description and disable the field after Phase 1 #}
                    {% set is_disabled = session.get('verification_complete') %}
                    {% set description_value = saved_desc %}
                    
                    <textarea class="form-control" id="alert_description" name="alert_description" rows="3" required placeholder="Briefly describe the file/data that triggered the alert..." {{ 'disabled' if is_disabled }} autofocus>{{ description_value }}</textarea>
                    
                    {# If the field is disabled, we need a hidden field to pass the value #}
                    {% if is_disabled %}
                        <input type="hidden" name="alert_description" value="{{ description_value }}">
                    {% endif %}
                </div>

                <h6 class="text-secondary mb-3"><i class="fas fa-exclamation-triangle me-2"></i> Compliance Review:</h6>
                <ul class="question-list list-unstyled">
                    <li class="list-group-item">
                        <label class="mb-2">Q1. How did you receive this sensitive data?</label>
                        <select name="q1" class="form-select">
                            <option value="A">Colleague accidentally forwarded/shared it</option>
                            <option value="B">Found in a shared folder/email but not meant for me</option>
                            <option value="C">Requested access but received more than I should have</option>
                            <option value="D">I don’t know / suspicious source</option>
                        </select>
                    </li>
                    <li class="list-group-item">
                        <label class="mb-2">Q2. What is your intention regarding this data?</label>
                        <select name="q2" class="form-select">
                            <option value="A">Delete safely / report</option>
                            <option value="B">Just understand, not keep</option>
                            <option value="C">Was planning to use it, now unsure</option>
                            <option value="D">Unsure / suspicious source</option>
                        </select>
                    </li>
                    <li class="list-group-item">
                        <label class="mb-2">Q3. What do you think you gain by accessing this data?</label>
                        <select name="q3" class="form-select">
                            <option value="A">Nothing — sent by mistake</option>
                            <option value="B">Thought it was general info</option>
                            <option value="C">Personal/work advantage</option>
                            <option value="D">Curious / don’t know</option>
                            <option value="E">Benefit from sharing/using outside role</option>
                        </select>
                    </li>
                    <li class="list-group-item">
                        <label class="mb-2">Q4. Have you already shared this data with anyone?</label>
                        <select name="q4" class="form-select">
                            <option value="A">No</option>
                            <option value="B">Yes, inside company only</option>
                            <option value="C">Yes, outside company</option>
                            <option value="D">Not sure</option>
                        </select>
                    </li>
                    <li class="list-group-item">
                        <label class="mb-2">Q5. Is the data stored on any other devices/accounts?</label>
                        <select name="q5" class="form-select">
                            <option value="A">No, only here</option>
                            <option value="B">Yes, on another work device/account</option>
                            <option value="C">Yes, on personal/external device</option>
                            <option value="D">Not sure</option>
                        </select>
                    </li>
                </ul>
                
                <button type="submit" name="action" value="get_guidance" class="btn btn-primary w-100 mt-3"><i class="fas fa-arrow-right me-2"></i> Proceed to Guidance (Phase 1/3)</button>
            </div>
        {% endif %} 
        
        {% if guidance and not session.get('deletion_ready') %}
            <div class="phase-card">
                <h5 class="phase-header border-success border-bottom-0"><img src="{{ url_for('serve_image', filename='cyberlohochatbot.jpg') }}" alt="Logo"> Phase 2: Authorization & Secure Key Delivery</h5>
                
                <div class="guidance-box">
                    <p class="fw-bold text-decoration-underline mb-2">🤖 SYSTEM GUIDANCE:</p>
                    {{ guidance }}
                </div>
                
                <div class="email-section">
                    <h6 class="text-success mt-4"><i class="fas fa-envelope me-2"></i> 3. Final Authorization (Receive Deletion Key)</h6>
                    <p class="text-secondary">Enter your corporate email below to receive the secure authorization key required for final action.</p>
                    <label for="email" class="form-label fw-bold">Enter Email:</label>
                    <input type="email" class="form-control" id="email" name="email" required placeholder="your.email@company.com">
                    <button type="submit" name="action" value="send_email" class="btn btn-success w-100 mt-3">Send Authorization Key (Phase 2/3)</button>
                </div>
            </div>
        {% endif %}

        {% if session.get('deletion_ready') %}
            <div class="phase-card final-actions text-center border-danger">
                <h4 class="text-danger mt-4"><i class="fas fa-skull-crossbones me-2"></i> Phase 3: Initiate Critical Deletion 🚨</h4>
                <p class="text-secondary">The authorization key has been verified/sent. Click below to confirm and **initiate the secure deletion process.**</p>
                
                <a href="{{ url_for('initiate_deletion') }}" class="btn btn-danger btn-lg me-3 mt-3">INITIATE DELETION</a>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-secondary btn-lg mt-3">Logout</a>
            </div>
        {% endif %}

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <div class="alert alert-info mt-3" role="alert">{% for message in messages %} {{ message }} {% endfor %}</div>
            {% endif %}
        {% endwith %}

    </form>
</div>
</body>
</html>
"""

@app.route("/verification", methods=["GET", "POST"])
def verification():
    # Only authenticated users can access the verification portal
    if not session.get("logged_in"):
        flash("Please log in to access the verification tool.")
        return redirect(url_for("login"))

    guidance_output = None
    alert_desc_data = session.get('alert_desc_data', '')
    
    if 'guidance_result' in session:
        guidance_output = session['guidance_result']
    
    if request.method == "POST":
        action = request.form.get('action')
        alert_desc = request.form.get("alert_description", "No description provided")
        
        # --- PHASE 1: GET GUIDANCE ---
        if action == "get_guidance":
            if not alert_desc or alert_desc == "No description provided":
                flash("Please enter an alert description.")
            else:
                answers = [request.form.get(f"q{i}", "A") for i in range(1,6)] 
                suspicious = any([
                    answers[0] in ["C","D"], answers[1] in ["C","D"], answers[2] in ["C","D","E"], 
                    answers[3] in ["C","D"], answers[4] in ["B","C","D"]
                ])
                if suspicious:
                    with open("security_alerts.log","a",encoding="utf-8") as f:
                        f.write(f"{datetime.now()} - ⚠️ Potential risk detected. Desc: {alert_desc}. Answers: {answers}\n")

                guidance_output = CYBER_TOOL.get_guidance(alert_desc)
                session['guidance_result'] = guidance_output
                session['alert_desc_data'] = alert_desc 
                session['verification_complete'] = True 
                
            return redirect(url_for("verification"))

        # --- PHASE 2: SEND EMAIL (and prepare for deletion) ---
        elif action == "send_email" and session.get('verification_complete'):
            email = request.form.get("email")
            if email:
                if send_authorization_email(email, CYBER_TOOL.DELETE_LINK, AUTH_KEY):
                    flash(f"✅ Authorization key sent to {email}. Proceed to the final step below.", "success")
                    session['deletion_ready'] = True 
                else:
                    flash("❌ Failed to send authorization key. Check SMTP credentials.", "error")
                
            return redirect(url_for("verification"))
        
    return render_template_string(verification_html, guidance=guidance_output, saved_desc=alert_desc_data)

@app.route("/initiate-deletion")
def initiate_deletion():
    if not session.get("deletion_ready"):
        flash("Deletion cannot be initiated without completing verification and receiving the key.", "error")
        return redirect(url_for("verification"))
    
    desc = session.pop('alert_desc_data', 'Unknown Data')
    
    session.pop('guidance_result', None)
    session.pop('verification_complete', None)
    session.pop('deletion_ready', None)

    flash(f"✅ Deletion Initiated! Sensitive data '{desc[:30]}...' is now being securely removed. Check the dashboard for logs.", "success")
    return redirect(url_for("dashboard"))


# ================== ANALYST DASHBOARD HTML ==================
dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>CyberEye Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        /* Typography: Use Inter, Segoe UI for crispness */
        body { background-color: #1a1a1a; color: #e0e0e0; font-family: 'Inter', 'Segoe UI', sans-serif; }
        .dashboard-container { max-width: 1200px; margin: 40px auto; padding: 30px; border-radius: 12px; background-color: #242424; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.8); border: 1px solid #333; }
        
        /* Metrics Cards */
        .metric-card { 
            background-color: #2c2c2c; 
            border-radius: 8px; 
            padding: 15px; 
            border-left: 5px solid; 
            transition: transform 0.2s; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.5);
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.6); }
        .metric-card h3 { font-size: 2em; margin-bottom: 0.1em; font-weight: 700; }
        
        .critical-border { border-left-color: #dc3545 !important; }
        .warning-border { border-left-color: #ffc107 !important; }
        .normal-border { border-left-color: #28a745 !important; }

        /* Table Styling */
        .table { --bs-table-bg: #2c2c2c; --bs-table-color: #f0f0f0; --bs-table-border-color: #333; }
        .table-striped>tbody>tr:nth-of-type(odd)>* { background-color: #333; }
        .table thead th { background-color: #1a1a1a; color: #00bcd4; border-bottom: 2px solid #00bcd4; font-weight: 700; }
        .badge { padding: 5px 10px; border-radius: 4px; font-weight: 700; }
        
        /* Status Badge Styling */
        .NORMAL { background-color: #28a745; color: white; } 
        .WARNING { background-color: #ffc107; color: #343a40; } 
        .CRITICAL { background-color: #dc3545; color: white; } 
        
        .text-primary-header { color: #00bcd4; font-weight: 700; text-shadow: 0 0 5px rgba(0, 188, 212, 0.4); }
        
        /* System Controls Card */
        .control-card {
            background-color: #3a404b;
            border: 1px solid #00bcd4;
            box-shadow: 0 0 10px rgba(0, 188, 212, 0.3);
            transition: all 0.3s;
        }
        .control-card:hover {
            box-shadow: 0 0 15px rgba(0, 188, 212, 0.6);
        }

        /* General Font and Text Clarity */
        .text-muted { color: #bdbec1 !important; }
        .text-secondary { color: #bdbec1 !important; }
        
        /* Responsive Table Adjustments */
        @media (max-width: 800px) {
            .table thead { display: none; }
            .table tbody td { display: block; text-align: right; padding-left: 50%; position: relative; border-top: none; border-bottom: 1px solid #454c57;}
            .table tbody td::before { content: attr(data-label); position: absolute; left: 10px; width: 45%; text-align: left; font-weight: bold; color: #a1a1a1;}
        }
    </style>
</head>
<body>
    <div class="container dashboard-container">
        <h2 class="text-center mb-5 text-primary-header"><i class="fas fa-desktop me-2"></i> Analyst Dashboard: Security Operations</h2>
        
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
                <div class="card p-3 control-card">
                    <h5 class="text-primary-header border-bottom border-light-subtle pb-2"><i class="fas fa-cogs me-2"></i> System Controls</h5>
                    <p class="text-white-50 mb-3">Total Log Records: {{ logs|length }}. Initiate reporting actions here.</p>
                    <div class="d-flex justify-content-end">
                         <a href="{{ url_for('download_logs') }}" class="btn btn-success me-2"><i class="fas fa-file-download me-2"></i> Export Logs (CSV)</a>
                         <a href="{{ url_for('logout') }}" class="btn btn-outline-light"><i class="fas fa-sign-out-alt me-2"></i> Logout</a>
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
    # Only allow analyst to view the dashboard
    if session.get('user_role') != 'analyst':
        flash("Access denied. Analyst privileges required.", "error")
        # Direct the user back to verification if they somehow landed here
        return redirect(url_for("verification"))
        
    with open(DATA_FILE, "r") as f:
        logs = json.load(f)
        logs.reverse() 

    metrics = calculate_log_metrics(logs)
    
    return render_template_string(dashboard_html, logs=logs, metrics=metrics)

# ================== Portal Login ==================
login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>CyberEye Portal - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: 'Inter', 'Segoe UI', sans-serif; position: relative; z-index: 1; }

        /* --- Image Background Setup --- */
        .background-logo {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            /* Uses Flask route to serve the image, assuming the file is named cybereyelogo.jpg */
            background-image: url("{{ url_for('serve_image', filename='cybereyelogo.jpg') }}");
            background-size: cover;
            background-position: center 20%; 
            background-repeat: no-repeat;
            z-index: -1; 
            /* Soft blur and dimming for high contrast */
            filter: grayscale(80%) brightness(0.18) blur(1px); 
            opacity: 0.9;
            transition: all 0.5s;
        }
        
        .login-container { 
            max-width: 450px; 
            margin-top: 100px; 
            padding: 40px; 
            border-radius: 10px; 
            background-color: rgba(30, 30, 30, 0.98); /* Almost opaque overlay */
            border: 1px solid #333;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.9);
            z-index: 10;
        }

        .logo-box {
            display: flex; /* Horizontal alignment */
            justify-content: center;
            align-items: center; /* Center items vertically */
            margin-bottom: 20px;
        }
        .logo-box img {
            width: 80px;
            height: 80px;
            filter: drop-shadow(0 0 5px #00bcd4);
            margin-right: 15px; /* Space between logo and text */
        }
        
        .text-primary-header { 
            color: #00bcd4 !important; 
            font-weight: 800; 
            font-size: 2.2rem;
            text-shadow: 0 0 5px rgba(0, 188, 212, 0.4); 
            letter-spacing: 0.1em;
            margin-bottom: 0 !important; 
        }

        /* Mission Statement Style */
        .mission-statement {
            color: #bdbec1;
            font-size: 0.9rem;
            margin-bottom: 2rem;
            padding-bottom: 10px;
            border-bottom: 1px solid #333;
        }

        .form-control { 
            background-color: #333; 
            border-color: #555; 
            color: #f0f0f0;
            font-size: 1.1rem;
            padding: 0.8rem 1rem;
        }
        .form-control:focus { 
            border-color: #00bcd4; 
            box-shadow: 0 0 0 0.25rem rgba(0, 188, 212, 0.4); 
            background-color: #3a3a3a;
        }
        
        .btn-primary {
            font-size: 1.15rem;
            font-weight: 700;
            padding: 0.6rem 0;
            background-color: #00bcd4; 
            border-color: #00bcd4;
            transition: background-color 0.3s;
        }
        .btn-primary:hover {
            background-color: #00a0b2;
            border-color: #00a0b2;
        }
        
        .auth-hint { color: #888; font-size: 0.85em; margin-top: 10px; }
    </style>
</head>
<body>
<div class="background-logo"></div>
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-8 login-container">
            <div class="logo-box">
                <img src="{{ url_for('serve_image', filename='cybereyelogo.jpg') }}" alt="CyberEye Logo" class="logo-image">
                <h2 class="text-primary-header">CYBEREYE</h2>
            </div>
            <p class="mission-statement text-center">
                Access required for security verification and administration.
            </p>
            
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="alert alert-danger" role="alert">{% for message in messages %} {{ message }} {% endfor %}</div>
              {% endif %}
            {% endwith %}
            
            <form method="post">
                <div class="mb-3">
                    <label for="auth_code" class="form-label fw-bold">Authorization Key:</label>
                    <input type="text" class="form-control" id="auth_code" name="auth_code" required autofocus>
                </div>
                <button type="submit" class="btn btn-primary w-100">AUTHENTICATE</button>
                <p class="auth-hint text-center">Analyst Code: **XYZ789** | User Code: **ABC123**</p>
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
        session["logged_in"] = True 

        if code == ANALYST_CODE:
            session['user_role'] = 'analyst'
            return redirect(url_for("dashboard"))
        elif code == PORTAL_USER_CODE:
            session['user_role'] = 'user'
            return redirect(url_for("verification"))
        else:
            flash("❌ Unauthorized code!")
            session['user_role'] = None
    return render_template_string(login_html)

@app.route("/logout")
def logout():
    # Clear all session data
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("login"))


# ================== Main ==================
if __name__ == "__main__":
    HOST_IP = "0.0.0.0"
    PORT = 5000
    
    CYBER_TOOL = CyberEye(portal_url=f"http://localhost:{PORT}/login", auth_key=AUTH_KEY)
    
    # NEW: Automatic browser launch
    def open_browser():
        webbrowser.open_new_tab(f'http://localhost:{PORT}/login')

    # Launch browser thread after a short delay
    threading.Timer(1.25, open_browser).start()
    
    print(f"🚀 Flask backend running at http://localhost:{PORT}/")
    app.logger.info(f"🚀 Flask backend running at http://localhost:{PORT}/")
    app.run(host=HOST_IP, port=PORT, debug=True)
