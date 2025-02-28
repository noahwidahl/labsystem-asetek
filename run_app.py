import os
import subprocess

# Sti til app.py
app_path = os.path.join('app', 'app.py')

# Start Flask-appen
os.chdir(os.path.dirname(os.path.abspath(__file__)))
subprocess.run(['python', app_path])