"""
Streamlit Application Entry Point
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

app_file = os.path.join(BASE_DIR, "app.py")
with open(app_file, "r", encoding="utf-8") as f:
    code = f.read()

exec(compile(code, app_file, "exec"), globals())
