################################################################################
# Lambda Function that receives the DynamoDB Auth Session Stream...
# ... and resumes conversation with user by sending another message!
################################################################################

# External imports
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBStreamEvent,
    DynamoDBRecord,
)

# Own imports
from common.logger import custom_logger
from trigger.helpers.whatsapp_helper import trigger_response  # noqa

logger = custom_logger()


def send_message_to_user(record: DynamoDBRecord) -> None:
    logger.append_keys(event_id=record.event_id)
    trigger_response(record)


@logger.inject_lambda_context(log_event=True)
@event_source(data_class=DynamoDBStreamEvent)
def lambda_handler(event: DynamoDBStreamEvent, context: LambdaContext):
    logger.info("Starting message processing from DynamoDB Stream")
    try:
        for record in event.records:
            if record.event_name.name != "REMOVE":  # Only process new items
                correlation_id = record.dynamodb.new_image.get("correlation_id")
                logger.append_keys(correlation_id=correlation_id)
                logger.debug(record.raw_event, message_details="DynamoDB Stream Record")
                send_message_to_user(record)
            else:
                logger.info("Skipping auth message, as it's not an ADD event.")

        logger.info("Finished message processing")
    except Exception as e:
        logger.exception(
            f"Wrong input event, does not match DynamoDBRecord schema: {e}"
        )
        raise e
