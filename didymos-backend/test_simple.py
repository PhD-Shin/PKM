import sys
print("Python version:", sys.version)
print("Testing imports...")

try:
    from app.services import llm_client
    print("✅ llm_client imported")
except Exception as e:
    print(f"❌ llm_client import failed: {e}")

try:
    from app.services import cluster_service
    print("✅ cluster_service imported")
except Exception as e:
    print(f"❌ cluster_service import failed: {e}")

print("\nAll imports successful!")
