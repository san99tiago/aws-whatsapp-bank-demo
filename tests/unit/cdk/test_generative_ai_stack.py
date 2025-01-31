# Built-in imports
import os

# External imports
import aws_cdk as core
import aws_cdk.assertions as assertions

# Own imports
from cdk.stacks.cdk_generative_ai_stack import GenerativeAIStack

app: core.App = core.App()
stack: GenerativeAIStack = GenerativeAIStack(
    scope=app,
    construct_id="santi-bank-demo-collab-test",
    main_resources_name="santi-bank-demo-collab",
    app_config={
        "deployment_environment": "dev",
        "log_level": "DEBUG",
        "table_name": "test-table-history-dev",
        "agents_data_table_name": "test-table-agents-data-dev",
        "api_gw_name": "test-api-wpp-dev",
        "secret_name": "/dev/aws-whatsapp-bank-demo",
        "comment": "Update the <enable_rag> to <true> in case that support for RAG with PDFs is required. Warning: could be expensive.",
        "enable_rag": True,
        "meta_endpoint": "https://graph.facebook.com/",
    },
)
template: assertions.Template = assertions.Template.from_stack(stack)


def test_app_synthesize_ok():
    app.synth()


def test_dynamodb_table_created():
    match = template.find_resources(
        type="AWS::DynamoDB::Table",
    )
    assert len(match) >= 1


def test_lambda_function_created():
    match = template.find_resources(
        type="AWS::Lambda::Function",
    )
    assert len(match) >= 2
