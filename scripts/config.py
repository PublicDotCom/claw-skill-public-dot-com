"""
Secure config loader for Public.com skill.
Reads API secret and account ID from secure file or environment variables.
"""
import os
import subprocess
import sys


def get_api_secret():
    """
    Get PUBLIC_COM_SECRET from secure file or environment.
    Tries in order:
    1. ~/.openclaw/workspace/.secrets/public_com_secret.txt
    2. PUBLIC_COM_SECRET environment variable

    Returns the secret string or None if not found.
    """
    # Try secure file first
    secret_file = os.path.expanduser("~/.openclaw/workspace/.secrets/public_com_secret.txt")
    if os.path.exists(secret_file):
        try:
            with open(secret_file, 'r') as f:
                secret = f.read().strip()
                if secret:
                    return secret
        except Exception:
            pass

    # Fall back to environment variable
    return os.getenv("PUBLIC_COM_SECRET")


def get_account_id():
    """
    Get PUBLIC_COM_ACCOUNT_ID from secure file or environment.
    Tries in order:
    1. ~/.openclaw/workspace/.secrets/public_com_account.txt
    2. PUBLIC_COM_ACCOUNT_ID environment variable

    Returns the account ID string or None if not found.
    """
    # Try secure file first
    account_file = os.path.expanduser("~/.openclaw/workspace/.secrets/public_com_account.txt")
    if os.path.exists(account_file):
        try:
            with open(account_file, 'r') as f:
                account_id = f.read().strip()
                if account_id:
                    return account_id
        except Exception:
            pass

    # Fall back to environment variable
    return os.getenv("PUBLIC_COM_ACCOUNT_ID")


def create_client(secret, account_id=None):
    """
    Create a PublicApiClient with a custom User-Agent for observability.
    Installs the SDK if not already present.
    """
    try:
        from public_api_sdk import PublicApiClient, PublicApiClientConfiguration
        from public_api_sdk.auth_config import ApiKeyAuthConfig
    except ImportError:
        print("Installing required dependency: publicdotcom-py...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
        from public_api_sdk import PublicApiClient, PublicApiClientConfiguration
        from public_api_sdk.auth_config import ApiKeyAuthConfig

    client = PublicApiClient(
        ApiKeyAuthConfig(api_secret_key=secret),
        config=PublicApiClientConfiguration(default_account_number=account_id),
    )
    client.api_client.session.headers["User-Agent"] = "openclaw-skill/1.0"
    return client
