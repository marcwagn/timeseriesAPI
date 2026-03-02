import os
import importlib

pkg_dir = os.path.dirname(__file__)

# Import every .py file in this folder except __init__.py
for filename in os.listdir(pkg_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]  # Strip .py
        importlib.import_module(f"{__name__}.{module_name}")
