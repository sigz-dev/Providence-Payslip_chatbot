from flask import Flask, render_template_string, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import os
from functools import wraps
import pandas as pd
from config import Config
import database as db

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Ensure upload folder exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# ==================== AUTHENTICATION ====================

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES ====================

@app.route('/')
@login_required
def dashboard():
    """Main dashboard"""
    stats = db.get_dashboard_stats()
    recent_logs = db.get_audit_logs(limit=10)
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>HR Admin Dashboard - Providence Staffing Solutions</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 40px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .header h1 { font-size: 28px; margin-bottom: 5px; }
            .header p { opacity: 0.9; }
            
            .logout-btn {
                float: right;
                background: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                padding: 8px 20px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }
            
            .logout-btn:hover { background: rgba(255,255,255,0.3); }
            
            .container { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
            .stat-card .number { font-size: 36px; font-weight: bold; color: #667eea; }
            
            .nav-buttons {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            
            .nav-btn {
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                text-decoration: none;
                color: #333;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }
            
            .nav-btn:hover { transform: translateY(-5px); box-shadow: 0 5px 20px rgba(0,0,0,0.15); }
            .nav-btn .icon { font-size: 32px; margin-bottom: 10px; }
            .nav-btn .label { font-weight: 600; }
            
            .section {
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            
            .section h2 {
                margin-bottom: 20px;
                color: #667eea;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
            }
            
            table th, table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            
            table th {
                background: #f8f9fa;
                font-weight: 600;
                color: #666;
            }
            
            table tr:hover { background: #f8f9fa; }
            
            .badge {
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
            
            .badge-success { background: #d4edda; color: #155724; }
            .badge-danger { background: #f8d7da; color: #721c24; }
            .badge-warning { background: #fff3cd; color: #856404; }
            
            .alert {
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            
            .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="{{ url_for('logout') }}" class="logout-btn">Logout</a>
            <h1>HR Admin Dashboard</h1>
            <p>Pro -Payroll Management System</p>
        </div>
        
        <div class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>TOTAL EMPLOYEES</h3>
                    <div class="number">{{ stats.total_employees }}</div>
                </div>
                <div class="stat-card">
                    <h3>TOTAL PAYSLIPS</h3>
                    <div class="number">{{ stats.total_payslips }}</div>
                </div>
                <div class="stat-card">
                    <h3>REQUESTS TODAY</h3>
                    <div class="number">{{ stats.requests_today }}</div>
                </div>
                <div class="stat-card">
                    <h3>ACTIVITY (7 DAYS)</h3>
                    <div class="number">{{ stats.activity_7days }}</div>
                </div>
            </div>
            
            <div class="nav-buttons">
                <a href="{{ url_for('upload_payslip') }}" class="nav-btn">
                    <div class="icon">📄</div>
                    <div class="label">Upload Payslip</div>
                </a>
                <a href="{{ url_for('manage_employees') }}" class="nav-btn">
                    <div class="icon">👥</div>
                    <div class="label">Manage Employees</div>
                </a>
                <a href="{{ url_for('view_payslips') }}" class="nav-btn">
                    <div class="icon">📊</div>
                    <div class="label">View All Payslips</div>
                </a>
                <a href="{{ url_for('audit_logs') }}" class="nav-btn">
                    <div class="icon">📋</div>
                    <div class="label">Audit Logs</div>
                </a>
                <a href="{{ url_for('bulk_import') }}" class="nav-btn">
                    <div class="icon">⬆️</div>
                    <div class="label">Bulk Import</div>
                </a>
            </div>
            
            <div class="section">
                <h2>Recent Activity</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Employee ID</th>
                            <th>Action</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for log in recent_logs %}
                        <tr>
                            <td>{{ log.timestamp }}</td>
                            <td>{{ log.employee_id or 'N/A' }}</td>
                            <td>{{ log.action_type }}</td>
                            <td>
                                {% if log.status == 'success' %}
                                    <span class="badge badge-success">Success</span>
                                {% elif log.status == 'failed' %}
                                    <span class="badge badge-danger">Failed</span>
                                {% else %}
                                    <span class="badge badge-warning">{{ log.status }}</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return render_template_string(html, stats=stats, recent_logs=recent_logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>HR Admin Login</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .login-box {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                width: 100%;
                max-width: 400px;
            }
            
            .login-box h1 {
                text-align: center;
                margin-bottom: 30px;
                color: #333;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 5px;
                color: #666;
                font-weight: 600;
            }
            
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .btn-login {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
            }
            
            .btn-login:hover {
                opacity: 0.9;
            }
            
            .alert {
                padding: 12px;
                margin-bottom: 20px;
                border-radius: 5px;
                text-align: center;
            }
            
            .alert-error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1> HR Admin Login</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn-login">Login</button>
            </form>
        </div>
    </body>
    </html>
    '''
    
    return render_template_string(html)

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/upload-payslip', methods=['GET', 'POST'])
@login_required
def upload_payslip():
    """Upload payslip page"""
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        month_year = request.form.get('month_year')
        file = request.files.get('payslip_file')
        
        if not all([employee_id, month_year, file]):
            flash('All fields are required', 'error')
            return redirect(url_for('upload_payslip'))
        
        if not Config.allowed_file(file.filename):
            flash('Only PDF files are allowed', 'error')
            return redirect(url_for('upload_payslip'))
        
        # Save file
        filename = secure_filename(f"{employee_id}_{month_year}.pdf")
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Add to database
        success, message = db.add_payslip(employee_id, month_year, file_path, filename, session.get('username', 'HR'))
        
        if success:
            flash(f'Payslip uploaded successfully for {employee_id}', 'success')
            db.log_action(employee_id, None, 'payslip_upload', f'{month_year} by {session.get("username")}', 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('upload_payslip'))
    
    employees = db.get_all_employees()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upload Payslip</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 40px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .header h1 { font-size: 28px; }
            
            .back-btn {
                display: inline-block;
                color: white;
                text-decoration: none;
                margin-bottom: 10px;
                opacity: 0.9;
            }
            
            .back-btn:hover { opacity: 1; }
            
            .container { max-width: 800px; margin: 30px auto; padding: 0 20px; }
            
            .form-card {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #333;
            }
            
            .form-group input, .form-group select {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            
            .form-group input:focus, .form-group select:focus {
                outline: none;
                border-color: #667eea;
            }
            
            .btn-submit {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
            }
            
            .btn-submit:hover { opacity: 0.9; }
            
            .alert {
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            
            .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            
            .help-text {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="{{ url_for('dashboard') }}" class="back-btn">← Back to Dashboard</a>
            <h1>📄 Upload Payslip</h1>
        </div>
        
        <div class="container">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <div class="form-card">
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Employee ID</label>
                        <select name="employee_id" required>
                            <option value="">Select Employee</option>
                            {% for emp in employees %}
                            <option value="{{ emp.employee_id }}">{{ emp.employee_id }} - {{ emp.full_name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>Month & Year</label>
                        <input type="text" name="month_year" placeholder="e.g., December2024" required>
                        <div class="help-text">Format: MonthYear (e.g., December2024, Nov2024)</div>
                    </div>
                    
                    <div class="form-group">
                        <label>Payslip PDF File</label>
                        <input type="file" name="payslip_file" accept=".pdf" required>
                        <div class="help-text">Only PDF files allowed (Max 5MB)</div>
                    </div>
                    
                    <button type="submit" class="btn-submit">Upload Payslip</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return render_template_string(html, employees=employees)

# COMPLETE EMPLOYEE MANAGEMENT SECTION
# Replace everything from @app.route('/employees') to @app.route('/payslips')

@app.route('/employees')
@login_required
def manage_employees():
    """Manage employees page"""
    employees = db.get_all_employees()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Manage Employees</title>
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; background: #f5f5f5; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
    .container { max-width: 1400px; margin: 20px auto; padding: 20px; }
    .btn { padding: 8px 15px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; border: none; cursor: pointer; font-size: 13px; display: inline-block; margin: 2px; }
    .btn:hover { opacity: 0.9; }
    .btn-success { background: #28a745; }
    .btn-warning { background: #ffc107; color: #333; }
    .btn-danger { background: #dc3545; }
    table { width: 100%; background: white; border-collapse: collapse; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background: #f8f9fa; font-weight: 600; }
    tr:hover { background: #f8f9fa; }
    .badge { padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
    .badge-active { background: #d4edda; color: #155724; }
    .badge-inactive { background: #f8d7da; color: #721c24; }
    .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
    .alert-success { background: #d4edda; color: #155724; }
    .alert-error { background: #f8d7da; color: #721c24; }
    .back-btn { color: white; text-decoration: none; opacity: 0.9; }
    </style></head>
    <body>
    <div class="header">
        <a href="{{ url_for('dashboard') }}" class="back-btn">← Back</a>
        <h1>👥 Manage Employees ({{ employees|length }})</h1>
    </div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}{% for cat, msg in messages %}
        <div class="alert alert-{{ cat }}">{{ msg }}</div>
        {% endfor %}{% endif %}{% endwith %}
        
        <a href="{{ url_for('add_employee') }}" class="btn btn-success">+ Add Employee</a>
        <br><br>
        
        <table>
        <tr><th>ID</th><th>Name</th><th>Phone</th><th>Dept</th><th>Status</th><th>Actions</th></tr>
        {% for emp in employees %}
        <tr>
            <td><strong>{{ emp.employee_id }}</strong></td>
            <td>{{ emp.full_name }}</td>
            <td>{{ emp.phone_number }}</td>
            <td>{{ emp.department or 'N/A' }}</td>
            <td>{% if emp.is_active %}<span class="badge badge-active">Active</span>{% else %}<span class="badge badge-inactive">Inactive</span>{% endif %}</td>
            <td>
                <a href="{{ url_for('view_employee', employee_id=emp.employee_id) }}" class="btn">View</a>
                <a href="{{ url_for('edit_employee', employee_id=emp.employee_id) }}" class="btn btn-warning">Edit</a>
                {% if emp.is_active %}
                <form method="POST" action="{{ url_for('delete_employee', employee_id=emp.employee_id) }}" style="display:inline;" onsubmit="return confirm('Delete {{ emp.full_name }}?');">
                    <button type="submit" class="btn btn-danger">Delete</button>
                </form>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
        </table>
    </div>
    </body></html>
    ''', employees=employees)

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    """Add new employee"""
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip().upper()
        full_name = request.form.get('full_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        national_id_last4 = request.form.get('national_id_last4', '').strip()
        department = request.form.get('department', '').strip()
        
        if not all([employee_id, full_name, phone_number, national_id_last4]):
            flash('All required fields must be filled', 'error')
            return redirect(url_for('add_employee'))
        
        if len(national_id_last4) != 4 or not national_id_last4.isdigit():
            flash('National ID must be 4 digits', 'error')
            return redirect(url_for('add_employee'))
        
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'
        
        success, message = db.add_employee(employee_id, full_name, phone_number, national_id_last4, national_id_last4, department or None)
        
        if success:
            flash(f'Employee {employee_id} added!', 'success')
            db.log_action(employee_id, None, 'employee_created', f'by {session.get("username")}', 'success')
            return redirect(url_for('manage_employees'))
        else:
            flash(message, 'error')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Add Employee</title>
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; background: #f5f5f5; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
    .container { max-width: 600px; margin: 20px auto; padding: 20px; background: white; border-radius: 10px; }
    .form-group { margin-bottom: 15px; }
    label { display: block; margin-bottom: 5px; font-weight: 600; }
    input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
    .btn { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
    .btn:hover { opacity: 0.9; }
    .back-btn { color: white; text-decoration: none; }
    .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
    .alert-error { background: #f8d7da; color: #721c24; }
    </style></head>
    <body>
    <div class="header">
        <a href="{{ url_for('manage_employees') }}" class="back-btn">← Back</a>
        <h1>➕ Add Employee</h1>
    </div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}{% for cat, msg in messages %}
        <div class="alert alert-{{ cat }}">{{ msg }}</div>
        {% endfor %}{% endif %}{% endwith %}
        
        <form method="POST">
            <div class="form-group">
                <label>Employee ID *</label>
                <input type="text" name="employee_id" placeholder="EMP001" required>
            </div>
            <div class="form-group">
                <label>Full Name *</label>
                <input type="text" name="full_name" placeholder="John Moyo" required>
            </div>
            <div class="form-group">
                <label>Phone Number *</label>
                <input type="text" name="phone_number" placeholder="+263771234567" required>
            </div>
            <div class="form-group">
                <label>National ID Last 4 Digits *</label>
                <input type="text" name="national_id_last4" placeholder="1234" maxlength="4" required>
            </div>
            <div class="form-group">
                <label>Department</label>
                <input type="text" name="department" placeholder="Production, HR, etc.">
            </div>
            <button type="submit" class="btn">Add Employee</button>
        </form>
    </div>
    </body></html>
    ''')

@app.route('/employees/view/<employee_id>')
@login_required
def view_employee(employee_id):
    """View employee details"""
    employees = db.get_all_employees(active_only=False)
    employee = next((e for e in employees if e['employee_id'] == employee_id), None)
    
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('manage_employees'))
    
    payslips = db.get_employee_payslips(employee_id)
    logs = db.get_employee_audit_logs(employee_id, limit=20)
    
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Employee Details</title>
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; background: #f5f5f5; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
    .container { max-width: 1000px; margin: 20px auto; padding: 20px; }
    .card { background: white; padding: 20px; margin: 10px 0; border-radius: 10px; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
    .info-item { padding: 10px; border-bottom: 1px solid #eee; }
    .label { font-size: 12px; color: #666; }
    .value { font-size: 16px; font-weight: 600; margin-top: 5px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background: #f8f9fa; }
    .back-btn { color: white; text-decoration: none; }
    .badge { padding: 4px 10px; border-radius: 10px; font-size: 11px; }
    .badge-active { background: #d4edda; color: #155724; }
    </style></head>
    <body>
    <div class="header">
        <a href="{{ url_for('manage_employees') }}" class="back-btn">← Back</a>
        <h1>👤 {{ employee.full_name }}</h1>
    </div>
    <div class="container">
        <div class="card">
            <h2>Information</h2>
            <div class="info-grid">
                <div class="info-item"><div class="label">Employee ID</div><div class="value">{{ employee.employee_id }}</div></div>
                <div class="info-item"><div class="label">Status</div><div class="value">{% if employee.is_active %}<span class="badge badge-active">Active</span>{% endif %}</div></div>
                <div class="info-item"><div class="label">Name</div><div class="value">{{ employee.full_name }}</div></div>
                <div class="info-item"><div class="label">Phone</div><div class="value">{{ employee.phone_number }}</div></div>
                <div class="info-item"><div class="label">Department</div><div class="value">{{ employee.department or 'N/A' }}</div></div>
                <div class="info-item"><div class="label">Created</div><div class="value">{{ employee.created_at[:10] }}</div></div>
            </div>
        </div>
        
        <div class="card">
            <h2>Payslips ({{ payslips|length }})</h2>
            {% if payslips %}
            <table>
                <tr><th>Month</th><th>File</th><th>Date</th></tr>
                {% for p in payslips %}
                <tr><td>{{ p.month_year }}</td><td>{{ p.file_name }}</td><td>{{ p.upload_date[:10] }}</td></tr>
                {% endfor %}
            </table>
            {% else %}<p>No payslips yet.</p>{% endif %}
        </div>
        
        <div class="card">
            <h2>Activity (Last 20)</h2>
            {% if logs %}
            <table>
                <tr><th>Time</th><th>Action</th><th>Status</th></tr>
                {% for log in logs %}
                <tr><td>{{ log.timestamp }}</td><td>{{ log.action_type }}</td><td>{{ log.status }}</td></tr>
                {% endfor %}
            </table>
            {% else %}<p>No activity yet.</p>{% endif %}
        </div>
    </div>
    </body></html>
    ''', employee=employee, payslips=payslips, logs=logs)

@app.route('/employees/edit/<employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    """Edit employee"""
    employees = db.get_all_employees(active_only=False)
    employee = next((e for e in employees if e['employee_id'] == employee_id), None)
    
    if not employee:
        flash('Employee not found', 'error')
        return redirect(url_for('manage_employees'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        department = request.form.get('department', '').strip()
        national_id_last4 = request.form.get('national_id_last4', '').strip()
        change_auth = request.form.get('change_auth') == 'yes'
        
        if not all([full_name, phone_number]):
            flash('Name and Phone required', 'error')
            return redirect(url_for('edit_employee', employee_id=employee_id))
        
        if change_auth and (len(national_id_last4) != 4 or not national_id_last4.isdigit()):
            flash('National ID must be 4 digits', 'error')
            return redirect(url_for('edit_employee', employee_id=employee_id))
        
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'
        
        try:
            conn = db.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE employees SET full_name=?, phone_number=?, department=?, updated_at=CURRENT_TIMESTAMP WHERE employee_id=?',
                         (full_name, phone_number, department or None, employee_id))
            
            if change_auth:
                new_pin_hash = db.hash_pin(national_id_last4)
                cursor.execute('UPDATE employees SET pin_hash=?, national_id_last4=? WHERE employee_id=?',
                             (new_pin_hash, national_id_last4, employee_id))
            
            conn.commit()
            conn.close()
            flash(f'Employee {employee_id} updated!', 'success')
            db.log_action(employee_id, None, 'employee_updated', f'by {session.get("username")}', 'success')
            return redirect(url_for('manage_employees'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Edit Employee</title>
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; background: #f5f5f5; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
    .container { max-width: 600px; margin: 20px auto; padding: 20px; background: white; border-radius: 10px; }
    .form-group { margin-bottom: 15px; }
    label { display: block; margin-bottom: 5px; font-weight: 600; }
    input[type="text"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
    input[type="checkbox"] { width: auto; }
    .btn { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; }
    .back-btn { color: white; text-decoration: none; }
    .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
    .alert-success { background: #d4edda; color: #155724; }
    .alert-error { background: #f8d7da; color: #721c24; }
    .auth-box { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style></head>
    <body>
    <div class="header">
        <a href="{{ url_for('manage_employees') }}" class="back-btn">← Back</a>
        <h1>✏️ Edit {{ employee.full_name }}</h1>
    </div>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}{% for cat, msg in messages %}
        <div class="alert alert-{{ cat }}">{{ msg }}</div>
        {% endfor %}{% endif %}{% endwith %}
        
        <form method="POST">
            <div class="form-group">
                <label>Full Name *</label>
                <input type="text" name="full_name" value="{{ employee.full_name }}" required>
            </div>
            <div class="form-group">
                <label>Phone *</label>
                <input type="text" name="phone_number" value="{{ employee.phone_number }}" required>
            </div>
            <div class="form-group">
                <label>Department</label>
                <input type="text" name="department" value="{{ employee.department or '' }}">
            </div>
            <div class="auth-box">
                <label><input type="checkbox" name="change_auth" value="yes"> Reset Authentication</label>
                <div class="form-group" style="margin-top: 10px;">
                    <label>New National ID Last 4</label>
                    <input type="text" name="national_id_last4" placeholder="1234" maxlength="4">
                </div>
            </div>
            <button type="submit" class="btn">Save Changes</button>
        </form>
    </div>
    </body></html>
    ''', employee=employee)

@app.route('/employees/delete/<employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    """Delete employee"""
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM employees WHERE employee_id = ?', (employee_id,))
        conn.commit()
        conn.close()
        flash(f'Employee {employee_id} deleted', 'success')
        db.log_action(employee_id, None, 'employee_deleted', f'by {session.get("username")}', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('manage_employees'))
@app.route('/payslips')
@login_required
def view_payslips():   
    """View all payslips"""
    payslips = db.get_all_payslips()
    return render_template_string('<h1>Payslips</h1><a href="{{ url_for(\'dashboard\') }}">Back</a><pre>{{ payslips }}</pre>', payslips=payslips)

@app.route('/audit')
@login_required
def audit_logs():
    """View audit logs"""
    logs = db.get_audit_logs(100)
    return render_template_string('<h1>Audit Logs</h1><a href="{{ url_for(\'dashboard\') }}">Back</a><pre>{{ logs }}</pre>', logs=logs)

@app.route('/bulk-import')
@login_required
def bulk_import():
    """Bulk import employees"""
    return render_template_string('<h1>Bulk Import (Coming Soon)</h1><a href="{{ url_for(\'dashboard\') }}">Back</a>')

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🏭 HR ADMIN DASHBOARD STARTING")
    print("="*50)
    print(f"📍 URL: http://localhost:{Config.ADMIN_PORT}")
    print(f"👤 Username: {Config.ADMIN_USERNAME}")
    print(f"🔑 Password: {Config.ADMIN_PASSWORD}")
    print("="*50 + "\n")
    
    app.run(debug=True, port=Config.ADMIN_PORT, use_reloader=False)