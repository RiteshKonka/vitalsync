import importlib, sys

def try_import(name):
    try:
        m = importlib.import_module(name)
        print(f"import {name} OK ->", getattr(m, '__file__', '<package>'))
    except Exception as e:
        print(f"IMPORT {name} ERROR:", type(e).__name__, e)

print('--- Test: import as package (backend, backend.main) ---')
try_import('backend')
try_import('backend.main')

print('\n--- Test: import as top-level modules (main, api.routes) ---')
try_import('main')
try_import('api.routes')

print('\n--- Try to import app object from backend.main ---')
try:
    from importlib import import_module
    mod = import_module('backend.main')
    print('backend.main.app present?', hasattr(mod, 'app'))
except Exception as e:
    print('backend.main import failed:', e)

print('\n--- Done')
