import asyncio
import os
import sys

from twikit import Client


async def main():
    print("--- Twitter Account Checker ---")

    # Clean list from user request
    candidates = [
        "leakedcaps",
        "allcappersfree",
        "Allinonecappers",
        "allcappersfreee",
        "Capperleaked",
        "ItsCappersPicks",
        "ExclusiveCapper",
        "free_topCappers",
        "capperspicksvip",
        "MrLeaked_",
        "EZMSports",
        "allpicksarefree",
    ]

    # Load cookies
    client = Client("en-US")
    cookies_path = "data/sessions/twitter_cookies.json"
    if os.path.exists(cookies_path):
        client.load_cookies(cookies_path)
    else:
        print("No cookies, can't check.")
        return

    valid_users = []

    for screen_name in candidates:
        print(f"Checking {screen_name}...", end=" ", flush=True)
        try:
            user = await client.get_user_by_screen_name(screen_name)
            print(f"OK (ID: {user.id})")
            valid_users.append(screen_name)
        except Exception as e:
            msg = str(e).lower()
            if "suspended" in msg:
                print("SUSPENDED")
            elif "does not exist" in msg:
                print("NOT FOUND")
            else:
                print(f"ERROR: {e}")
                # Treat as potentially valid or temporary error?
                # For safety, maybe exclude if error is not 'suspended'/'not found'
                # unless it's a network error.
                pass

        await asyncio.sleep(1.5)  # Rate limit safety

    print("\n--- Valid Accounts ---")
    print(valid_users)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
