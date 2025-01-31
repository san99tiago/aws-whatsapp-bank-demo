# DEMO SCRIPT TO LOAD SAMPLE DATA TO DYNAMODB
import os, boto3

# TODO: Replace the items with your own data... Parametrize this script... Improve it...

items = [
    # LOAD DEMO USER PROFILES...
    {
        "PK": "USER#santi123",
        "SK": "PROFILE#",
        "first_name": "Santi123",
        "last_name": "Garci",
        "email": "santi123@example.com",
        "phone_number": "+1234567890",
        "address": "123 Main St, Anytown, COL",
    },
    {
        "PK": "USER#dani456",
        "SK": "PROFILE#",
        "first_name": "Moni",
        "last_name": "Hill",
        "email": "moni@example.com",
        "phone_number": "+9876543210",
        "address": "456 Abc St, Othertown, COL",
    },
    # LOAD DEMO USER PRODUCTS...
    {
        "PK": "USER#santi123",
        "SK": "PRODUCT#01",
        "product_name": "Credit Card",
        "last_digits": "1111",
        "details": "Amex Card",
        "status": "ACTIVE",
    },
    {
        "PK": "USER#santi123",
        "SK": "PRODUCT#02",
        "product_name": "Credit Card",
        "last_digits": "2222",
        "details": "Visa Card",
        "status": "ACTIVE",
    },
    {
        "PK": "USER#santi123",
        "SK": "PRODUCT#03",
        "product_name": "Bank Account",
        "last_digits": "3333",
        "details": "Savings Account",
        "status": "ACTIVE",
    },
    {
        "PK": "USER#santi123",
        "SK": "PRODUCT#04",
        "product_name": "Bank Account",
        "last_digits": "4444",
        "details": "Mortgage Debt",
        "status": "ACTIVE",
    },
    {
        "PK": "USER#dani456",
        "SK": "PRODUCT#01",
        "product_name": "LOW-RISK-FUND",
        "last_digits": "7777",
        "details": "Low risk collective fund",
        "status": "ACTIVE",
    },
    {
        "PK": "USER#dani456",
        "SK": "PRODUCT#02",
        "product_name": "CDT",
        "last_digits": "8888",
        "details": "Low risk virtual investment",
        "status": "ACTIVE",
    },
    {
        "PK": "USER#dani456",
        "SK": "PRODUCT#03",
        "product_name": "Bank Account",
        "last_digits": "9999",
        "details": "Savings Account",
        "status": "ACTIVE",
    },
]

# Load data to DynamoDB
deployment_environment = os.environ["DEPLOYMENT_ENVIRONMENT"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(f"multi-agent-collab-data-{deployment_environment}")

for item in items:
    print(f"Loading item: {item}")
    result = table.put_item(Item=item)
    print(f"Result: {result} \n")
