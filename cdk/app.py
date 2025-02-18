#!/usr/bin/env python3

# Built-in imports
import os

# External imports
import aws_cdk as cdk

# Own imports
from helpers.add_tags import add_tags_to_app
from stacks.cdk_chatbot_api_stack import ChatbotAPIStack
from stacks.cdk_generative_ai_stack import GenerativeAIStack


print("--> Deployment AWS configuration (safety first):")
print("CDK_DEFAULT_ACCOUNT", os.environ.get("CDK_DEFAULT_ACCOUNT"))
print("CDK_DEFAULT_REGION", os.environ.get("CDK_DEFAULT_REGION"))


app: cdk.App = cdk.App()


# Configurations for the deployment (obtained from env vars and CDK context)
DEPLOYMENT_ENVIRONMENT = os.environ["DEPLOYMENT_ENVIRONMENT"]  # Fail if not set
MAIN_RESOURCES_NAME = app.node.try_get_context("main_resources_name")
# TODO: enhance app_config to be a data class (improve keys/typings)
APP_CONFIG = app.node.try_get_context("app_config")[DEPLOYMENT_ENVIRONMENT]


# STACK 1: Stack for receiving WhatsApp messages and core infrastructure for input/output messages
stack: ChatbotAPIStack = ChatbotAPIStack(
    app,
    f"{MAIN_RESOURCES_NAME}-chatbot-api-{DEPLOYMENT_ENVIRONMENT}",
    MAIN_RESOURCES_NAME,
    APP_CONFIG,
    env={
        "account": os.environ.get("CDK_DEFAULT_ACCOUNT"),
        "region": os.environ.get("CDK_DEFAULT_REGION"),
    },
    description=f"Stack for {MAIN_RESOURCES_NAME} chatbot-api infrastructure in {DEPLOYMENT_ENVIRONMENT} environment",
)

# STACK 2: Stack for the Generative-AI Multi-Agent solution for processing messages with private context (Tools, RAG, etc)
stack: GenerativeAIStack = GenerativeAIStack(
    app,
    f"{MAIN_RESOURCES_NAME}-generative-ai-{DEPLOYMENT_ENVIRONMENT}",
    MAIN_RESOURCES_NAME,
    APP_CONFIG,
    env={
        "account": os.environ.get("CDK_DEFAULT_ACCOUNT"),
        "region": os.environ.get("CDK_DEFAULT_REGION"),
    },
    description=f"Stack for {MAIN_RESOURCES_NAME} generative-ai infrastructure in {DEPLOYMENT_ENVIRONMENT} environment",
)

# STACK 3: Auth component with Cognito/Frontend/Cloudfront
# # TODO!!!


add_tags_to_app(
    app,
    MAIN_RESOURCES_NAME,
    DEPLOYMENT_ENVIRONMENT,
)

app.synth()
