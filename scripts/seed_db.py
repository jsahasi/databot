"""Initial data sync from ON24 API to PostgreSQL."""
import asyncio

async def main():
    print("Seed script - will sync ON24 data to PostgreSQL")
    print("Usage: python scripts/seed_db.py")

if __name__ == "__main__":
    asyncio.run(main())
