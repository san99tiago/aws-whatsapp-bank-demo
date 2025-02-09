# DEMO SCRIPT TO LOAD SAMPLE DATA TO DYNAMODB
import os, boto3

# TODO: Replace the items with your own data... Parametrize this script... Improve it...

# IMPORTANT: Replace these with your own phones!!!
PHONE_NUMBER_1 = "REPLACE_ME_WITH_YOUR_PHONE_NUMBER"
PHONE_NUMBER_2 = "REPLACE_ME_WITH_BUSINESS_PHONE_NUMBER"

items = [
    # LOAD DEMO USER PROFILES...
    {
        "PK": f"USER#{PHONE_NUMBER_1}",
        "SK": "PROFILE#",
        "first_name": f"{PHONE_NUMBER_1}",
        "last_name": "Garci",
        "email": "santigarci@example.com",
        "phone_number": "+1234567890",
        "address": "123 Main St, Anytown, COL",
    },
    {
        "PK": f"USER#{PHONE_NUMBER_2}",
        "SK": "PROFILE#",
        "first_name": "Rufus",
        "last_name": "Hill",
        "email": "rufushill@example.com",
        "phone_number": "+9876543210",
        "address": "456 Abc St, Othertown, COL",
    },
    # LOAD DEMO USER PRODUCTS...
    {
        "PK": f"USER#{PHONE_NUMBER_1}",
        "SK": "PRODUCT#01",
        "product_name": "Credit Card",
        "last_digits": "1111",
        "details": "Amex Card",
        "status": "ACTIVE",
    },
    {
        "PK": f"USER#{PHONE_NUMBER_1}",
        "SK": "PRODUCT#02",
        "product_name": "Credit Card",
        "last_digits": "2222",
        "details": "Visa Card",
        "status": "ACTIVE",
    },
    {
        "PK": f"USER#{PHONE_NUMBER_1}",
        "SK": "PRODUCT#03",
        "product_name": "Bank Account",
        "last_digits": "3333",
        "details": "Savings Account",
        "status": "ACTIVE",
    },
    {
        "PK": f"USER#{PHONE_NUMBER_1}",
        "SK": "PRODUCT#04",
        "product_name": "Bank Account",
        "last_digits": "4444",
        "details": "Mortgage Debt",
        "status": "ACTIVE",
    },
    {
        "PK": f"USER#{PHONE_NUMBER_2}",
        "SK": "PRODUCT#01",
        "product_name": "LOW-RISK-FUND",
        "last_digits": "7777",
        "details": "Low risk collective fund",
        "status": "ACTIVE",
    },
    {
        "PK": f"USER#{PHONE_NUMBER_2}",
        "SK": "PRODUCT#02",
        "product_name": "CDT",
        "last_digits": "8888",
        "details": "Low risk virtual investment",
        "status": "ACTIVE",
    },
    {
        "PK": f"USER#{PHONE_NUMBER_2}",
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
table = dynamodb.Table(f"rufus-bank-wpp-agents-data-{deployment_environment}")

for item in items:
    print(f"Loading item: {item}")
    result = table.put_item(Item=item)
    print(f"Result: {result} \n")
