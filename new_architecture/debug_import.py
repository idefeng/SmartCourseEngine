
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / "shared"))
sys.path.insert(0, str(Path.cwd() / "api-gateway"))

print("Python path:")
for p in sys.path:
    print(p)

try:
    print("Attempting to import auth_routes...")
    import api_gateway.auth_routes
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

try:
    print("Attempting to import shared.auth...")
    from shared import auth
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
