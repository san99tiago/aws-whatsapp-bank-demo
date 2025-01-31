# DEMO SCRIPT TO LOAD SAMPLE DATA TO DYNAMODB
import os, boto3

# TODO: Replace the items with your own data... Parametrize this script... Improve it...

items = [
    # LOAD DEMO USER PROFILES...
    {
        "PK": "MARKET#CONSERVATIVE",
        "SK": "ADVICE#LATEST#",
        "advice": "Invest in low-risk products",
        "products_list": "CDT or FIC-CONSERVADOR",
    },
    {
        "PK": "MARKET#MODERATE",
        "SK": "ADVICE#LATEST#",
        "advice": "Invest in medium-risk products",
        "products_list": "CDT or FIC-MODERADO",
    },
    {
        "PK": "MARKET#RISKY",
        "SK": "ADVICE#LATEST#",
        "advice": "Invest in high-risk products",
        "products_list": "FIC-RIESGO or MGC",
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
