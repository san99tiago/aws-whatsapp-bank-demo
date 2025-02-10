import boto3
import time
from botocore.exceptions import ClientError

# UPDATE THESE PARAMS
PHONE_NUMBER_1 = "REPLACE_ME_WITH_YOUR_PHONE_NUMBER"

# Calculate the TTL (2 minutes from now)
ttl = int(time.time()) + 120

# DynamoDB parameters
params = {
    "TableName": "rufus-bank-auth-sessions-prod",
    "Item": {
        "PK": {"S": f"USER#{PHONE_NUMBER_1}"},
        "SK": {"S": "AUTH"},
        "active": {"BOOL": True},
        "ttl": {"N": str(ttl)},
    },
}

# DynamoDB client configuration
dynamodb_client = boto3.client(
    "dynamodb",
    region_name="us-east-1",
)

try:
    # Add the item to DynamoDB
    dynamodb_client.put_item(**params)
    print("Item added to DynamoDB successfully.")
except ClientError as error:
    print(f"Error adding item to DynamoDB: {error}")
