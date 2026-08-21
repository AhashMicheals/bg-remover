"""
Streamlit Application Entry Point for Streamlit Cloud & Deployments
"""
import os
import sys

# Add root directory to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Run app.py
app_file = os.path.join(ROOT_DIR, "app.py")
with open(app_file, "r", encoding="utf-8") as f:
    code = f.read()

exec(compile(code, app_file, "exec"), globals())
