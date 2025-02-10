# Built-in imports
import boto3

# External imports
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBRecord,
)

# Own imports
from common.logger import custom_logger
from state_machine.integrations.meta.api_requests import MetaAPI


LOGGER = custom_logger()

step_function_client = boto3.client("stepfunctions")


def trigger_response(record: DynamoDBRecord, logger: Logger = None) -> str:
    """
    Handler for triggering the response to user after auth.

    Args:
        record (DynamoDBRecord): Event from from DynamoDB Stream Record.
        logger (Logger, optional): Logger object. Defaults to None.

    Returns:
        None
    """
    try:
        logger = logger or LOGGER
        log_message = {
            "METHOD": "trigger_response",
        }
        log_message["MESSAGE"] = "answering message to user..."
        log_message["RECORD"] = record.raw_event

        # Extract the necessary information from the DynamoDB Stream Record for Execution Name
        correlation_id = record.dynamodb.new_image.get("correlation_id", "NOT_FOUND")
        logger.append_keys(correlation_id=correlation_id)
        logger.debug(log_message)
        pk_string = record.dynamodb.new_image["PK"]  # Intentionally fail if not found!
        logger.debug(f"Found PK in DynamoDB Stream: {pk_string}")

        # Only use the number from the PK single Table Design Structure...
        # ... PK == USER#{number}
        number = pk_string.split("#")[1]
        from_message = number.replace("+", "")

        # Send message to client
        meta_api = MetaAPI(logger)
        response = meta_api.post_text_message(
            text_message="Te autenticaste exitosamente con Ruffy. ¿Cómo puedo apoyarte hoy?",
            to_phone_number=from_message,
        )

        logger.debug(
            response,
            message_details="POST WhatsApp Message Meta API Response",
        )

        if "error" in response:
            logger.error(
                response,
                message_details="Error in POST WhatsApp Message Meta API Response",
            )
            # Do not raise exception for now... As it could cause undesired loops!
            # raise Exception("Error in POST WhatsApp Message Meta API Response")
        return "Auth success processed OK!"

    except Exception as err:
        log_message["EXCEPTION"] = str(err)
        logger.error(str(log_message))
        raise
