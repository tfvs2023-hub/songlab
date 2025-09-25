import importlib
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    importlib.import_module("main_v2")
    print("IMPORT_OK")
except Exception:
    traceback.print_exc()
