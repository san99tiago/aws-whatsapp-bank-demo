# NOTE: This is a super-MVP code for testing. Still has a lot of gaps to solve/fix. Do not use in prod.
# Built-in imports
import os

# Own imports
from common.logger import custom_logger
from common.helpers.dynamodb_helper import DynamoDBHelper


TABLE_NAME = os.environ["TABLE_NAME"]  # Mandatory to pass table name as env var

logger = custom_logger()
dynamodb_helper = DynamoDBHelper(table_name=TABLE_NAME)


def action_group_generate_certificates(parameters):
    # Extract user_id from parameters
    user_id = None
    for param in parameters:
        if param["name"] == "user_id":
            user_id = param["value"]

    all_user_products = dynamodb_helper.query_by_pk_and_sk_begins_with(
        partition_key=f"USER#{user_id}",
        sort_key_portion="PRODUCT#",
    )

    # TODO: Add helper to actually generate PDF Certificates for user.
    certificates_response = "Certificate Generated Dummy Response"

    logger.info(f"certificates_response: {certificates_response}")
    return certificates_response


def lambda_handler(event, context):
    action_group = event["actionGroup"]
    _function = event["function"]
    parameters = event.get("parameters", [])

    logger.info(f"PARAMETERS ARE: {parameters}")
    logger.info(f"ACTION GROUP IS: {action_group}")

    # TODO: enhance this If-Statement approach to a dynamic one...
    if action_group == "GenerateCertificates":
        results = action_group_generate_certificates(parameters)
    else:
        raise ValueError(f"Action Group <{action_group}> not supported.")

    # Convert the list of events to a string to be able to return it in the response as a string
    response_body = {"TEXT": {"body": str(results)}}

    action_response = {
        "actionGroup": action_group,
        "function": _function,
        "functionResponse": {"responseBody": response_body},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }
    logger.info("Response: {}".format(function_response))

    return function_response
