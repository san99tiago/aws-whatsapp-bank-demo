# NOTE: This is a super-MVP code for testing. Still has a lot of gaps to solve/fix. Do not use in prod.
# Built-in imports
import os
import uuid


# Own imports
from common.logger import custom_logger
from common.helpers.dynamodb_helper import DynamoDBHelper
from state_machine.integrations.meta.api_requests import MetaAPI
from agents.bank_certificates.generate_certificates import generate_certificate_pdf
from agents.bank_certificates.s3_helper import upload_pdf_to_s3


TABLE_NAME = os.environ["TABLE_NAME"]  # Mandatory to pass table name as env var
BUCKET_NAME = os.environ["BUCKET_NAME"]  # Mandatory to pass table name as env var


logger = custom_logger()
dynamodb_helper = DynamoDBHelper(table_name=TABLE_NAME)


def action_group_generate_certificates(parameters):
    # Extract user_id from parameters
    user_id = None
    for param in parameters:
        if param["name"] == "from_number":
            from_number = param["value"]
            user_id = param["value"]  # User ID is also the from_number for now...

    all_user_products = dynamodb_helper.query_by_pk_and_sk_begins_with(
        partition_key=f"USER#{user_id}",
        sort_key_portion="PRODUCT#",
    )

    logger.debug(f"all_user_products: {all_user_products}")

    # Generate the PDF file and save it locally
    certificate_local_path = generate_certificate_pdf(
        product_list=all_user_products,
        location="Medellin, Colombia",
    )

    logger.debug(f"certificate_local_path: {certificate_local_path}")

    # Upload the local certificate to an S3 bucket and generate public URL for 10 mins
    certificate_url = upload_pdf_to_s3(
        bucket_name=BUCKET_NAME,
        file_path=certificate_local_path,
        object_name=f"certificates/{str(uuid.uuid4())}/rufus_certificate.pdf",
    )

    # Send the Certificate via Meta API
    meta_api = MetaAPI(logger)
    response = meta_api.post_document_message(
        document_url=certificate_url,
        to_phone_number=from_number,
    )

    logger.debug(
        response,
        message_details="POST WhatsApp Message Meta API Response",
    )

    logger.info(f"Certificate URL: {certificate_url}")
    return "Certificate generated successfully for Rufus client!"


def lambda_handler(event, context):
    action_group = event["actionGroup"]
    _function = event["function"]
    parameters = event.get("parameters", [])

    logger.info(f"PARAMETERS ARE: {parameters}")
    logger.info(f"ACTION GROUP IS: {action_group}")

    # TODO: enhance this If-Statement approach to a dynamic one...
    if (
        action_group == "GenerateCertificates"
        or action_group == "<GenerateCertificates>"
    ):
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
