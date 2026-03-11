"""Manual sync trigger."""
import asyncio

async def main():
    print("Manual sync trigger - will pull latest data from ON24 API")

if __name__ == "__main__":
    asyncio.run(main())
