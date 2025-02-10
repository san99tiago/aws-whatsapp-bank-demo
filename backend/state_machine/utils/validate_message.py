# Built-in imports
import os


# Local Imports
from state_machine.base_step_function import BaseStepFunction
from common.enums import WhatsAppMessageTypes
from common.logger import custom_logger


from common.helpers.dynamodb_helper import DynamoDBHelper


TABLE_NAME = os.environ[
    "TABLE_NAME_AUTH_SESSIONS"
]  # Mandatory to pass table name as env var

logger = custom_logger()
dynamodb_helper = DynamoDBHelper(table_name=TABLE_NAME)


ALLOWED_MESSAGE_TYPES = [member.value for member in WhatsAppMessageTypes]
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false")


class ValidateMessage(BaseStepFunction):
    """
    This class contains methods that serve as event validation for the State Machine.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def validate_input(self):
        """
        Method to validate the input JSON body for the beginning of the State Machine.
        """

        self.logger.info("Starting validate_input JSON body validation")

        # TODO: Add a more complex validation here (Python schema, etc.)

        # Obtain message_type from the DynamoDB Stream event
        # TODO: add abstraction and validation
        self.message_type = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("type", {})
            .get("S", "NOT_FOUND_MESSAGE_TYPE")
        )

        if self.message_type not in ALLOWED_MESSAGE_TYPES:
            logger.error(f"Message type {self.message_type} not allowed")
            raise ValueError(
                f"Message type <{self.message_type}> is not allowed. Allowed ones are: {ALLOWED_MESSAGE_TYPES}"
            )

        # ADDITIONAL CHECKS FOR AUTH IF ENABLED
        if AUTH_ENABLED == "true":
            logger.debug("Auth enabled, proceeding to check session status...")

            # Obtain from_number from the DynamoDB Stream event
            phone_number = (
                self.event.get("input", {})
                .get("dynamodb", {})
                .get("NewImage", {})
                .get("from_number", {})
                .get("S")
            )

            # Check if active session in DynamoDB
            result = dynamodb_helper.get_item_by_pk_and_sk(
                partition_key=f"USER#{phone_number}",
                sort_key="AUTH",
            )

            if not result:
                logger.warning(f"User {phone_number} NOT authenticated")
                self.message_type = "unauthorized"
                self.event["response_message"] = (
                    "Hi there, you need to authenticate. \nPlease visit: - https://rufus-auth.san99tiago.com"  # Enforce user auth if ENV VAR ENABLED
                )
            logger.info(
                f"User {phone_number} authenticated correctly with active session"
            )

        self.logger.info("Validation finished successfully")

        # Add relevant data fields for traceability in the next State Machine steps
        self.event["correlation_id"] = self.correlation_id
        self.event["message_type"] = self.message_type

        return self.event
