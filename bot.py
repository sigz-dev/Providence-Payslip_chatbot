from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
from config import Config
import database as db

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Twilio client for sending files
twilio_client = None
if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
    twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

# User session management (in-memory for now)
user_sessions = {}

def send_message(to_number, message_text):
    """Send a WhatsApp message"""
    resp = MessagingResponse()
    resp.message(message_text)
    return str(resp)

def send_file_via_whatsapp(to_number, file_path, message_text="Here is your payslip:"):
    """Send a file via WhatsApp using Twilio"""
    if not twilio_client:
        return False, "Twilio not configured"
    
    try:
        # Create public URL for the file
        public_url = f"{request.url_root}download/{os.path.basename(file_path)}"
        
        message = twilio_client.messages.create(
            from_=Config.TWILIO_WHATSAPP_NUMBER,
            to=to_number,
            body=message_text,
            media_url=[public_url]
        )
        return True, "File sent successfully"
    except Exception as e:
        print(f"Error sending file: {e}")
        return False, str(e)

@app.route('/download/<filename>')
def download_file(filename):
    """Serve uploaded files for Twilio to fetch"""
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/pdf')
    return "File not found", 404

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    print(f"\n>>> Message from {sender}: {incoming_msg}")
    
    # Initialize session for new users
    if sender not in user_sessions:
        user_sessions[sender] = {
            'state': 'initial',
            'data': {}
        }
    
    session = user_sessions[sender]
    
    # Handle reset commands
    if incoming_msg.lower() in ['menu', 'start', 'restart', 'reset', 'hi', 'hello']:
        session['state'] = 'initial'
        session['data'] = {}
    
    # State machine for conversation flow
    if session['state'] == 'initial':
        response_text = """PROVIDENCE STAFFING SOLUTIONS!

I can help you with:
1️⃣ Get my payslip
2️⃣ Check hours worked (Coming soon)
3️⃣ Leave balance (Coming soon)

Reply with 1 to get your payslip."""
        
        session['state'] = 'menu_selected'
        print(f">>> Sent welcome menu")
        return send_message(sender, response_text)
    
    elif session['state'] == 'menu_selected':
        if '1' in incoming_msg:
            session['data']['request_type'] = 'payslip'
            response_text = """📋 Payslip Request

Please enter your Employee ID
(Example: EMP001)"""
            session['state'] = 'awaiting_employee_id'
            print(f">>> Requesting employee ID")
            return send_message(sender, response_text)
        
        elif '2' in incoming_msg or '3' in incoming_msg:
            response_text = "⏳ This feature is coming soon!\n\nType 'menu' to return to main menu."
            session['state'] = 'initial'
            return send_message(sender, response_text)
        
        else:
            response_text = "❌ Please reply with 1, 2, or 3\n\nType 'menu' to see options again."
            return send_message(sender, response_text)
    
    elif session['state'] == 'awaiting_employee_id':
        session['data']['employee_id'] = incoming_msg.upper()
        response_text = """🔐 Security Check

Please enter your 4-digit PIN:"""
        session['state'] = 'awaiting_pin'
        print(f">>> Requesting PIN for {incoming_msg.upper()}")
        return send_message(sender, response_text)
    
    elif session['state'] == 'awaiting_pin':
        employee_id = session['data']['employee_id']
        pin = incoming_msg.strip()
        
        # Verify credentials
        is_valid, employee = db.verify_employee_credentials(sender, employee_id, pin)
        
        if is_valid:
            session['data']['employee'] = employee
            response_text = f"""✅ Welcome {employee['full_name']}!

Which month's payslip do you need?

Examples:
- December2024
- November2024
- Dec2024

Please type the month:"""
            session['state'] = 'awaiting_month'
            
            # Log successful authentication
            db.log_action(employee_id, sender, 'authentication', 'Success', 'success')
            print(f">>> Authentication successful for {employee_id}")
            return send_message(sender, response_text)
        else:
            response_text = """❌ Invalid credentials!

Your Employee ID or PIN is incorrect.

Type 'start' to try again or contact HR for help."""
            
            # Log failed authentication
            db.log_action(employee_id, sender, 'authentication', 'Failed - Invalid credentials', 'failed')
            print(f">>> Authentication failed for {employee_id}")
            
            session['state'] = 'initial'
            session['data'] = {}
            return send_message(sender, response_text)
    
    elif session['state'] == 'awaiting_month':
        month_input = incoming_msg.strip()
        employee_id = session['data']['employee_id']
        employee = session['data']['employee']
        
        # Get payslip from database
        payslip = db.get_payslip(employee_id, month_input)
        
        if payslip:
            file_path = payslip['file_path']
            
            # Check if file exists
            if os.path.exists(file_path):
                # Send the PDF file
                if twilio_client:
                    # For production with Twilio
                    success, message = send_file_via_whatsapp(
                        sender, 
                        file_path, 
                        f"✅ Your {month_input} payslip:"
                    )
                    
                    if success:
                        response_text = f"""✅ Payslip sent successfully!

Month: {month_input}
Employee: {employee['full_name']}

Check your messages for the PDF file.

Type 'menu' for more options."""
                        
                        # Log successful delivery
                        db.log_action(employee_id, sender, 'payslip_request', f'{month_input} - Delivered', 'success')
                        print(f">>> Payslip sent: {employee_id} - {month_input}")
                    else:
                        response_text = f"""⚠️ Found your payslip but couldn't send it automatically.

Please contact HR to get your {month_input} payslip.

Type 'menu' to return."""
                        
                        db.log_action(employee_id, sender, 'payslip_request', f'{month_input} - Send failed', 'failed')
                else:
                    # For testing without Twilio
                    response_text = f"""✅ Payslip Found!

Month: {month_input}
Employee: {employee['full_name']}
File: {payslip['file_name']}

(In production with Twilio configured, the PDF would be sent here)

Type 'menu' for more options."""
                    
                    db.log_action(employee_id, sender, 'payslip_request', f'{month_input} - Found (test mode)', 'success')
                    print(f">>> Payslip found (test mode): {employee_id} - {month_input}")
            else:
                response_text = f"""⚠️ Payslip record found but file is missing.

Please contact HR about your {month_input} payslip.

Type 'menu' to return."""
                
                db.log_action(employee_id, sender, 'payslip_request', f'{month_input} - File missing', 'failed')
        else:
            response_text = f"""❌ No payslip found for {month_input}

Please check:
- Month spelling (e.g., December2024)
- Contact HR if you believe this is an error

Type 'menu' to return to main menu."""
            
            db.log_action(employee_id, sender, 'payslip_request', f'{month_input} - Not found', 'failed')
            print(f">>> Payslip not found: {employee_id} - {month_input}")
        
        session['state'] = 'initial'
        session['data'] = {}
        return send_message(sender, response_text)
    
    else:
        # Fallback
        response_text = "Something went wrong. Type 'start' to begin again."
        session['state'] = 'initial'
        return send_message(sender, response_text)

@app.route('/')
def home():
    """Home page"""
    stats = db.get_dashboard_stats()
    
    return f"""
    <html>
    <head>
        <title>WhatsApp Payslip Bot</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .card {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #667eea; }}
            .status {{ color: green; font-weight: bold; }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-top: 20px;
            }}
            .stat-box {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
            }}
            .stat-number {{ font-size: 32px; font-weight: bold; color: #667eea; }}
            .stat-label {{ color: #666; margin-top: 5px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🏭 Dairy Factory Payslip Bot</h1>
            <p class="status">✅ Status: ONLINE</p>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">{stats['total_employees']}</div>
                    <div class="stat-label">Active Employees</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{stats['total_payslips']}</div>
                    <div class="stat-label">Total Payslips</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{stats['requests_today']}</div>
                    <div class="stat-label">Requests Today</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{stats['activity_7days']}</div>
                    <div class="stat-label">Activity (7 Days)</div>
                </div>
            </div>
            
            <h3 style="margin-top: 30px;">System Information:</h3>
            <ul>
                <li><strong>Bot Endpoint:</strong> /whatsapp</li>
                <li><strong>Database:</strong> {Config.DATABASE_NAME}</li>
                <li><strong>Admin Dashboard:</strong> <a href="http://localhost:{Config.ADMIN_PORT}">localhost:{Config.ADMIN_PORT}</a></li>
                <li><strong>Twilio Configured:</strong> {'Yes' if twilio_client else 'No (Test Mode)'}</li>
            </ul>
            
            <p style="margin-top: 30px; color: #666;">
                <strong>Note:</strong> This bot is running and ready to receive WhatsApp messages via Twilio webhook.
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/test')
def test():
    """Test endpoint"""
    stats = db.get_dashboard_stats()
    return {
        'status': 'online',
        'database': Config.DATABASE_NAME,
        'twilio_configured': twilio_client is not None,
        'stats': stats
    }

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 WHATSAPP PAYSLIP BOT - PRODUCTION VERSION")
    print("="*60)
    stats = db.get_dashboard_stats()
    print(f"📊 Employees: {stats['total_employees']}")
    print(f"📄 Payslips: {stats['total_payslips']}")
    print(f"🔗 Bot URL: http://localhost:{Config.BOT_PORT}")
    print(f"🔗 Webhook: http://localhost:{Config.BOT_PORT}/whatsapp")
    print(f"⚙️  Admin Dashboard: http://localhost:{Config.ADMIN_PORT}")
    print("="*60)
    
    if not twilio_client:
        print("⚠️  WARNING: Twilio not configured - running in TEST MODE")
        print("   Update .env file with Twilio credentials for production")
        print("="*60)
    
    print("\n🚀 Bot is running and ready!\n")
    
    app.run(debug=True, port=Config.BOT_PORT, use_reloader=False)