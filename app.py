"""
Forwarding proxy to the new Enterprise Modular Architecture.
This file maintains backwards compatibility so the `python app.py` 
terminal command still works seamlessly.
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
