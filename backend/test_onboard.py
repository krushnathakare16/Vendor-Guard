import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.api.endpoints.onboarding import onboard_vendor, OnboardRequest

async def main():
    try:
        req = OnboardRequest(vendor_name="intel")
        res = await onboard_vendor(req)
        print("SUCCESS:")
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
