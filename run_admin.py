import sys
print("Python version:", sys.version)
print("Starting import...")

try:
    from admin_dashboard import app
    from config import Config
    print("Import successful!")
    print(f"Starting server on port {Config.ADMIN_PORT}...")
    app.run(debug=True, port=Config.ADMIN_PORT, host='127.0.0.1')
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()