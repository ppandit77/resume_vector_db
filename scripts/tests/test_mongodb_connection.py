"""
Simple MongoDB Atlas Connection Test
"""
import sys
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Load environment
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core.load_env import load_env
load_env()

# Get credentials from env
host = os.getenv("MONGODB_HOST")
username = os.getenv("MONGODB_USERNAME")
password = os.getenv("MONGODB_PASSWORD")
database = os.getenv("MONGODB_DATABASE")

# Build connection string
connection_string = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"

print("=" * 80)
print("TESTING MONGODB ATLAS CONNECTION")
print("=" * 80)
print(f"\nHost: {host}")
print(f"Username: {username}")
print(f"Database: {database}")
print(f"\nAttempting connection...")

try:
    # Create client with short timeout
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)

    # Test connection by pinging
    client.admin.command('ping')

    print("\n✅ SUCCESS: Connected to MongoDB Atlas!")

    # List databases
    print("\nAvailable databases:")
    for db_name in client.list_database_names():
        print(f"  - {db_name}")

    # Try to access our database
    db = client[database]
    print(f"\nCollections in '{database}':")
    for coll_name in db.list_collection_names():
        print(f"  - {coll_name}")

    client.close()

except ConnectionFailure as e:
    print(f"\n❌ CONNECTION FAILED: {e}")
    print("\nPossible causes:")
    print("1. IP address not whitelisted in MongoDB Atlas Network Access")
    print("2. Incorrect credentials")
    print("3. Network connectivity issues")
    sys.exit(1)

except OperationFailure as e:
    print(f"\n❌ OPERATION FAILED: {e}")
    print("\nPossible causes:")
    print("1. IP address not whitelisted")
    print("2. Insufficient permissions")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("CONNECTION TEST COMPLETED")
print("=" * 80)
