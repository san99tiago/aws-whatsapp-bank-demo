# Built-in imports
import os


# Local Imports
from common.enums import WhatsAppMessageTypes
from common.logger import custom_logger
from common.helpers.dynamodb_helper import DynamoDBHelper
from state_machine.base_step_function import BaseStepFunction
from state_machine.integrations.meta.api_requests import MetaAPI


TABLE_NAME = os.environ.get("TABLE_NAME_AUTH_SESSIONS")

logger = custom_logger()


ALLOWED_MESSAGE_TYPES = [member.value for member in WhatsAppMessageTypes]
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false")


class ValidateMessage(BaseStepFunction):
    """
    This class contains methods that serve as event validation for the State Machine.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

        # TODO: Validate if migrating the helper init outside class is relevant
        self.dynamodb_helper = DynamoDBHelper(table_name=TABLE_NAME)

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
            result = self.dynamodb_helper.get_item_by_pk_and_sk(
                partition_key=f"USER#{phone_number}",
                sort_key="AUTH",
            )

            if result:
                logger.info(
                    f"User {phone_number} authenticated correctly with active session"
                )
            else:
                logger.warning(f"User {phone_number} NOT authenticated")
                self.message_type = "unauthorized"
                self.event["response_message"] = (
                    "Buenos días! Gracias por comunicarte con Rufus Bank.\n Para proceder, debes autenticarte: - https://rufus-auth.san99tiago.com"  # Enforce user auth if ENV VAR ENABLED
                )

        self.logger.info("Validation finished successfully")

        # Add acknowledge message (received) for better user experience
        # Initialize the Meta API
        meta_api = MetaAPI(logger=self.logger)
        response = meta_api.post_text_message(
            text_message="Ruffy recibió tu mensaje (procesando)...",
            to_phone_number=phone_number,
        )

        self.logger.debug(
            response,
            message_details="POST WhatsApp Message Meta API Response",
        )

        if "error" in response:
            self.logger.error(
                response,
                message_details="Error in POST WhatsApp Message Meta API Response",
            )
            raise Exception("Error in POST WhatsApp Message Meta API Response")

        # Add relevant data fields for traceability in the next State Machine steps
        self.event["correlation_id"] = self.correlation_id
        self.event["message_type"] = self.message_type

        return self.event
