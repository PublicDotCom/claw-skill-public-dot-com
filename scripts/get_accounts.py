import sys

from config import get_api_secret, create_client


def get_accounts():
    secret = get_api_secret()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)

    try:
        client = create_client(secret)

        accounts_response = client.get_accounts()

        print("Your Public.com Accounts:")
        print("-" * 40)
        for account in accounts_response.accounts:
            print(f"Account ID: {account.account_id}")
            print(f"Account Type: {account.account_type}")
            print("-" * 40)

        client.close()
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        sys.exit(1)


if __name__ == "__main__":
    get_accounts()
