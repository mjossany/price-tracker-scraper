"""
Debug wrapper for lambda_function.py
Adds debugpy support for SAM local debugging.

This file should NOT be deployed to production.
It's only used for local SAM debugging with --debug-port.

Usage:
    ./debug_sam.sh
    Then press F5 and select "Attach to SAM Local (Debug)"
"""
import os

# Enable remote debugging if DEBUG_PORT is set (for SAM local debugging)
if os.getenv('DEBUG_PORT'):
    import debugpy
    debug_port = int(os.getenv('DEBUG_PORT', 5678))
    debugpy.listen(("0.0.0.0", debug_port))
    print(f"⏳ Waiting for debugger to attach on port {debug_port}...")
    debugpy.wait_for_client()
    print("✅ Debugger attached!")

# Import the real lambda handler
from lambda_function import lambda_handler as _lambda_handler


def lambda_handler(event, context):
    """
    Debug wrapper that delegates to the real lambda_handler.
    This function is used by SAM when debugging with --debug-port.
    """
    return _lambda_handler(event, context)
