import sqlite3
import hashlib
from datetime import datetime
import os

DATABASE_NAME = 'payroll_system.db'

def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def hash_pin(pin):
    """Hash PIN for security using SHA-256"""
    return hashlib.sha256(str(pin).encode()).hexdigest()

def init_database():
    """Initialize all database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Employees table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            phone_number TEXT UNIQUE NOT NULL,
            pin_hash TEXT NOT NULL,
            national_id_last4 TEXT,
            department TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Payslips table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payslips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            month_year TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
            uploaded_by TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            UNIQUE(employee_id, month_year)
        )
    ''')
    
    # Audit logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            phone_number TEXT,
            action_type TEXT NOT NULL,
            action_details TEXT,
            status TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT
        )
    ''')
    
    # Hours worked table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hours_worked (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            regular_hours REAL DEFAULT 0,
            overtime_hours REAL DEFAULT 0,
            total_hours REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    ''')
    
    # Settings table (for system configuration)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ==================== EMPLOYEE FUNCTIONS ====================

def add_employee(employee_id, full_name, phone_number, pin, national_id_last4=None, department=None):
    """Add a new employee to the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        pin_hash = hash_pin(pin)
        
        cursor.execute('''
            INSERT INTO employees (employee_id, full_name, phone_number, pin_hash, national_id_last4, department)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (employee_id, full_name, phone_number, pin_hash, national_id_last4, department))
        
        conn.commit()
        conn.close()
        return True, "Employee added successfully"
    except sqlite3.IntegrityError as e:
        return False, f"Employee ID or phone number already exists: {str(e)}"
    except Exception as e:
        return False, f"Error adding employee: {str(e)}"

def get_employee_by_phone(phone_number):
    """Get employee details by phone number"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM employees WHERE phone_number = ? AND is_active = 1', (phone_number,))
    employee = cursor.fetchone()
    
    conn.close()
    return dict(employee) if employee else None

def verify_employee_credentials(phone_number, employee_id, pin):
    """Verify employee login credentials"""
    employee = get_employee_by_phone(phone_number)
    
    if not employee:
        return False, None
    
    if employee['employee_id'] != employee_id:
        return False, None
    
    if employee['pin_hash'] != hash_pin(pin):
        return False, None
    
    return True, employee

def get_all_employees(active_only=True):
    """Get all employees"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute('SELECT * FROM employees WHERE is_active = 1 ORDER BY employee_id')
    else:
        cursor.execute('SELECT * FROM employees ORDER BY employee_id')
    
    employees = cursor.fetchall()
    conn.close()
    
    return [dict(emp) for emp in employees]

def deactivate_employee(employee_id):
    """Deactivate an employee (soft delete)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE employees SET is_active = 0 WHERE employee_id = ?', (employee_id,))
        conn.commit()
        conn.close()
        return True, "Employee deactivated"
    except Exception as e:
        return False, f"Error: {str(e)}"

def update_employee_pin(employee_id, new_pin):
    """Update employee PIN"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_pin_hash = hash_pin(new_pin)
        cursor.execute('UPDATE employees SET pin_hash = ? WHERE employee_id = ?', (new_pin_hash, employee_id))
        
        conn.commit()
        conn.close()
        return True, "PIN updated successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"

# ==================== PAYSLIP FUNCTIONS ====================

def add_payslip(employee_id, month_year, file_path, file_name, uploaded_by="HR"):
    """Add a payslip record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO payslips (employee_id, month_year, file_path, file_name, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, month_year, file_path, file_name, uploaded_by))
        
        conn.commit()
        conn.close()
        return True, "Payslip added successfully"
    except Exception as e:
        return False, f"Error adding payslip: {str(e)}"

def get_payslip(employee_id, month_year):
    """Get payslip for specific employee and month"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Try exact match first
    cursor.execute('''
        SELECT * FROM payslips 
        WHERE employee_id = ? AND LOWER(month_year) = LOWER(?)
    ''', (employee_id, month_year))
    
    payslip = cursor.fetchone()
    conn.close()
    
    return dict(payslip) if payslip else None

def get_employee_payslips(employee_id):
    """Get all payslips for an employee"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM payslips 
        WHERE employee_id = ? 
        ORDER BY upload_date DESC
    ''', (employee_id,))
    
    payslips = cursor.fetchall()
    conn.close()
    
    return [dict(p) for p in payslips]

def get_all_payslips():
    """Get all payslips"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, e.full_name 
        FROM payslips p
        LEFT JOIN employees e ON p.employee_id = e.employee_id
        ORDER BY p.upload_date DESC
    ''')
    
    payslips = cursor.fetchall()
    conn.close()
    
    return [dict(p) for p in payslips]

def delete_payslip(payslip_id):
    """Delete a payslip record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get file path before deleting
        cursor.execute('SELECT file_path FROM payslips WHERE id = ?', (payslip_id,))
        result = cursor.fetchone()
        
        if result:
            file_path = result['file_path']
            # Delete from database
            cursor.execute('DELETE FROM payslips WHERE id = ?', (payslip_id,))
            conn.commit()
            
            # Delete actual file
            if os.path.exists(file_path):
                os.remove(file_path)
        
        conn.close()
        return True, "Payslip deleted"
    except Exception as e:
        return False, f"Error: {str(e)}"

# ==================== AUDIT LOG FUNCTIONS ====================

def log_action(employee_id, phone_number, action_type, action_details, status, ip_address=None):
    """Log an action to audit trail"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_logs (employee_id, phone_number, action_type, action_details, status, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (employee_id, phone_number, action_type, action_details, status, ip_address))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging action: {e}")
        return False

def get_audit_logs(limit=100):
    """Get recent audit logs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM audit_logs 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (limit,))
    
    logs = cursor.fetchall()
    conn.close()
    
    return [dict(log) for log in logs]

def get_employee_audit_logs(employee_id, limit=50):
    """Get audit logs for specific employee"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM audit_logs 
        WHERE employee_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (employee_id, limit))
    
    logs = cursor.fetchall()
    conn.close()
    
    return [dict(log) for log in logs]

# ==================== STATISTICS FUNCTIONS ====================

def get_dashboard_stats():
    """Get statistics for admin dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total active employees
    cursor.execute('SELECT COUNT(*) as count FROM employees WHERE is_active = 1')
    total_employees = cursor.fetchone()['count']
    
    # Total payslips
    cursor.execute('SELECT COUNT(*) as count FROM payslips')
    total_payslips = cursor.fetchone()['count']
    
    # Total requests today
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) as count FROM audit_logs 
        WHERE action_type = 'payslip_request' 
        AND DATE(timestamp) = ?
    ''', (today,))
    requests_today = cursor.fetchone()['count']
    
    # Recent activity
    cursor.execute('''
        SELECT COUNT(*) as count FROM audit_logs 
        WHERE timestamp >= datetime('now', '-7 days')
    ''')
    activity_7days = cursor.fetchone()['count']
    
    conn.close()
    
    return {
        'total_employees': total_employees,
        'total_payslips': total_payslips,
        'requests_today': requests_today,
        'activity_7days': activity_7days
    }

# ==================== BULK IMPORT FUNCTIONS ====================

def bulk_import_employees(employees_data):
    """
    Bulk import employees from list of dictionaries
    employees_data format: [
        {'employee_id': 'EMP001', 'full_name': 'John Doe', 'phone_number': '+263...', 'pin': '1234'},
        ...
    ]
    """
    success_count = 0
    errors = []
    
    for emp_data in employees_data:
        try:
            success, message = add_employee(
                emp_data['employee_id'],
                emp_data['full_name'],
                emp_data['phone_number'],
                emp_data['pin'],
                emp_data.get('national_id_last4'),
                emp_data.get('department')
            )
            if success:
                success_count += 1
            else:
                errors.append(f"{emp_data['employee_id']}: {message}")
        except Exception as e:
            errors.append(f"{emp_data.get('employee_id', 'Unknown')}: {str(e)}")
    
    return success_count, errors

# Initialize database when module is imported
if __name__ == "__main__":
    init_database()
    print(f"Database '{DATABASE_NAME}' ready!")