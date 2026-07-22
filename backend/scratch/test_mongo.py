import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    # Try different URIs
    uris = [
        # As provided, with angle brackets
        "mongodb+srv://<belamohamed386_db_user>:<2xuLyXtUh1xctpUh>@fluxa.mwqxou8.mongodb.net/",
        # Without angle brackets
        "mongodb+srv://belamohamed386_db_user:2xuLyXtUh1xctpUh@fluxa.mwqxou8.mongodb.net/",
    ]
    
    for uri in uris:
        print(f"Testing connection to: {uri.split('@')[1]} using credentials: {uri.split('://')[1].split('@')[0]}")
        client = AsyncIOMotorClient(uri)
        client.append_metadata = None # patch
        try:
            # Trigger connection by listing databases
            dbs = await client.list_database_names()
            print(f"-> SUCCESS! Connected successfully. Databases: {dbs}\n")
            return
        except Exception as e:
            print(f"-> FAILED: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_connection())
