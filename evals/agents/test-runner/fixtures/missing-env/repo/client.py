import os


def auth_header():
    return {"Authorization": f"Bearer {os.environ['BILLING_API_TOKEN']}"}


def base_url():
    return "https://billing.example.invalid/v1"
