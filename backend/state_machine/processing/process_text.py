# Built-in imports
from datetime import datetime

# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.enums import WhatsAppMessageTypes
from common.logger import custom_logger

# TODO: Add bedrock_agent helper
from state_machine.processing.bedrock_agent import call_bedrock_agent


logger = custom_logger()
ALLOWED_MESSAGE_TYPES = WhatsAppMessageTypes.__members__


class ProcessText(BaseStepFunction):
    """
    This class contains methods that serve as the "text processing" for the State Machine.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_text(self):
        """
        Method to validate the input message and process the expected text response.
        """

        self.logger.info("Starting process_text for the chatbot")

        # TODO: Add more robust "text processing" logic here (actual response)
        self.text = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("text", {})
            .get("S", "DEFAULT_RESPONSE")
        )

        phone_number = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("from_number", {})
            .get("S")
        )

        # # Uncomment these for troubleshooting if needed in the future :)
        # # First step is to answer an "acnowledged" message (before a real bedrock interaction)
        # self.response_message = (
        #     f"Received: {self.text} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        # )

        # Add extra params to the text input
        self.text = (
            f"input: {self.text}\n"
            f"from_number: {phone_number}\n"
            f"Please answer in the same language as the user.\n"
        )

        # TODO: Add more complex "text processing" logic here with memory and sessions...
        self.response_message = call_bedrock_agent(self.text, phone_number)

        self.logger.info(f"Generated response message: {self.response_message}")
        self.logger.info("Validation finished successfully")

        self.event["response_message"] = self.response_message

        return self.event
