import json, os, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone


load_dotenv()

client = AsyncIOMotorClient(os.getenv("db_url"))
db = client[os.getenv("db_name")]
user_collections = db["users"]


# ✅ Async logic for post-confirmation
async def lambda_handler(event, context):
    print("=== Cognito Trigger Event ===")
    print(json.dumps(event, indent=2))

    try:
        cognito_user_name = event.get("userName")
        user_attrs = event["request"]["userAttributes"]
        sub = user_attrs.get("sub")
        email = user_attrs.get("email")
        name = user_attrs.get("name")
        phone = user_attrs.get("phone_number")

        existing = await user_collections.find_one({"cognito_id": sub})
        if existing:
            print(f"User already exists: {email}")
        else:
            idp_provider = "google" if "google" in cognito_user_name else "email_signup"
            await user_collections.insert_one({
                "cognito_id": sub,
                "email": email,
                "name": name,
                "phone_number": phone,
                "createdAt": datetime.now(timezone.utc),
                "idp_provider": idp_provider
            })
            print(f"✅ User stored successfully: {email}")


        return event

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise e


# ✅ Sync entry point (AWS calls this one)
def handler(event, context):
    """AWS Lambda entry point for Cognito trigger."""
    try:
        # ✅ Get current loop if already running (Lambda reuses it)
        loop = asyncio.get_event_loop()

        if loop.is_running():
            # ✅ Create a task within the existing loop (no new loop)
            future = asyncio.run_coroutine_threadsafe(lambda_handler(event, context), loop)
            return future.result()
        else:
            # ✅ Run normally if no loop is running
            return loop.run_until_complete(lambda_handler(event, context))

    except RuntimeError:
        # ✅ Create a new loop if none exists (cold start case)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(lambda_handler(event, context))
