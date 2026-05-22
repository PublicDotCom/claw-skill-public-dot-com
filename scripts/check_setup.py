"""
Verifies that the environment is correctly configured for the Public.com skill.
Checks that required environment variables are set and the API key is valid.
"""
import sys

from config import get_api_secret, get_account_id, create_client


def check_setup():
    print("Checking Public.com skill setup...")
    print("-" * 40)

    # Check API secret
    secret = get_api_secret()
    if not secret:
        print("FAIL: PUBLIC_COM_SECRET is not set.")
        print("      Set it with: export PUBLIC_COM_SECRET=[YOUR_API_SECRET]")
        print("      Get your API secret at: https://public.com/settings/v2/api")
        sys.exit(1)
    print("OK:   PUBLIC_COM_SECRET is set.")

    # Check optional account ID
    account_id = get_account_id()
    if account_id:
        print(f"OK:   PUBLIC_COM_ACCOUNT_ID is set ({account_id}).")
    else:
        print("INFO: PUBLIC_COM_ACCOUNT_ID is not set (optional).")
        print("      Commands that need an account ID will look it up automatically.")

    # Verify the API key works by fetching accounts
    print("-" * 40)
    print("Verifying API key by fetching accounts...")
    try:
        client = create_client(secret, account_id)
        accounts_response = client.get_accounts()
        accounts = accounts_response.accounts
        client.close()

        if not accounts:
            print("WARN: API key is valid but no accounts were found.")
        else:
            print(f"OK:   API key is valid. Found {len(accounts)} account(s):")
            for account in accounts:
                print(f"        - {account.account_id} ({account.account_type})")

    except Exception as e:
        print(f"FAIL: Could not connect to Public.com API: {e}")
        print("      Your API key may be invalid or expired.")
        print("      Generate a new one at: https://public.com/settings/v2/api")
        sys.exit(1)

    print("-" * 40)
    print("Setup looks good. You are ready to use the Public.com skill.")


if __name__ == "__main__":
    check_setup()
