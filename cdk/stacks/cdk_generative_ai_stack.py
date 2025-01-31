# Built-in imports
import os

# External imports
from aws_cdk import (
    Duration,
    aws_bedrock,
    aws_dynamodb,
    aws_iam,
    aws_lambda,
    aws_opensearchserverless as oss,
    aws_ssm,
    aws_s3,
    aws_s3_deployment as s3d,
    custom_resources as cr,
    CfnOutput,
    RemovalPolicy,
    Stack,
    Tags,
)
from constructs import Construct


# Global settings and setup
# FOUNDATION_MODEL_CHILD_AGENTS = "anthropic.claude-3-haiku-20240307-v1:0"
# FOUNDATION_MODEL_CHILD_AGENTS = "anthropic.claude-3-5-haiku-20241022-v1:0"

FOUNDATION_MODEL_SUPERVISOR_AGENT = "amazon.nova-pro-v1:0"
FOUNDATION_MODEL_CHILD_AGENTS = "amazon.nova-lite-v1:0"
AGENT_1_INSTRUCTION = (
    "You are the 'user-products-agent', specialized in retrieving and providing information about the user's existing bank products. "
    "If the user requests details about their products, ensure they provide the <user_id> parameter to retrieve all relevant bank products. "
    "Your response must strictly contain the requested user product details. Do not provide any additional information or analysis. "
    "Always respond in the SAME language as the input, maintaining clear and concise communication."
)

AGENT_2_INSTRUCTION = (
    "You are the 'financial-assistant-agent', specialized in providing personalized financial advice and product recommendations. "
    "To deliver advice, you must: "
    "1. Infer the user's RISK_PROFILE based on their existing products or directly from user input. Use only [CONSERVATIVE, MODERATE, RISKY] as valid options, converting similar terms to these canonical forms. "
    "2. Fetch Market Insights using the <FetchMarketInsights> tool and integrate the RISK_PROFILE. "
    "3. Cross-reference the results with the <RUFUS BANK INVESTMENT PRODUCTS> document to recommend the most suitable products or actions for the user. "
    "Your recommendations must align with the user's <user_id> and <RISK_PROFILE>. Always provide advice tailored to their profile and preferences. "
    "Ensure responses are in the SAME language as the input, clear, and actionable."
)

SUPERVISOR_AGENT_INSTRUCTION = (
    "You are 'Ruffy', the supervisor agent for Rufus Bank, orchestrating interactions between specialized agents to provide the best user experience. "
    "Introduce yourself with: 'Hi, I am Ruffy, your bank assistant for Rufus Bank. How can I help you today?' "
    "- For questions about EXISTING PRODUCTS, route the request to the 'user-products-agent'. "
    "- For PRODUCT RECOMMENDATIONS (any question about recommended products), follow this process: "
    "  1. Request user product information from the 'user-products-agent' using the <user_id>. "
    "  2. From the returned products, infer the user's RISK_PROFILE (choose from [CONSERVATIVE, MODERATE, RISKY]). "
    "  3. Execute the 'financial-assistant-agent' to find recommended products based on the RISK_PROFILE. "
    "- Always format fetched results clearly, embedding them within <answer></answer> tags. "
    "- NEVER include RISK_PROFILE information in responses unless the user explicitly requests product recommendations. "
    "- Provide structured, detailed answers while maintaining the SAME language as the input. "
    "- If the user's request is not clear or cannot be understood, politely ask for clarification. "
)

SUPERVISOR_INSTRUCTIONS_FOR_AGENT_1 = (
    "Invoke the 'user-products-agent' to retrieve details about the user's existing bank products. "
    "Ensure the user provides the <user_id> for accurate retrieval. "
    "When the task involves product recommendations, first use this agent to gather user product information, then proceed to infer the RISK_PROFILE and consult the 'financial-assistant-agent'."
)

SUPERVISOR_INSTRUCTIONS_FOR_AGENT_2 = (
    "Invoke the 'financial-assistant-agent' for any tasks involving Market Insights or customized financial recommendations. "
    "Ensure these recommendations align with the user's RISK_PROFILE and bank product offerings."
)


# AGENT_1_INSTRUCTION = (
#     "You are the 'user-products-agent' (v1.0). You specialize in retrieving and providing information about the user's existing bank products. "
#     "Your message format is: {'agent': 'user-products-agent', 'action': '<action_name>', 'parameters': {}, 'result': {}, 'status': 'success'/'error', 'language': '<language_code>'}. "
#     "Actions:"
#     "  - 'get_products': Retrieve user product details. Parameters: {'user_id': '<user_id>'}. Result: A JSON array of product objects. Each object has fields like 'product_id', 'product_name', 'balance', 'interest_rate', etc.  Example: `[{'product_id': '1', 'product_name': 'Checking Account', ...}, ...]`"
#     "  - If the 'user_id' is missing or invalid, return {'status': 'error', 'result': 'Invalid user_id'}. "
#     "Respond in the language specified by the 'language' parameter."
# )

# AGENT_2_INSTRUCTION = (
#     "You are the 'financial-assistant-agent' (v1.0). You specialize in providing personalized financial advice and product recommendations. "
#     "Your message format is: {'agent': 'financial-assistant-agent', 'action': '<action_name>', 'parameters': {}, 'result': {}, 'status': 'success'/'error', 'language': '<language_code>'}. "
#     "Actions:"
#     "  - 'get_recommendations': Provide product recommendations. Parameters: {'user_id': '<user_id>', 'risk_profile': '<risk_profile>'}. Result: A JSON array of recommended product objects, including 'product_id', 'product_name', 'description', 'reason', etc. Example: `[{'product_id': '3', 'product_name': 'High-Yield Savings', ...}, ...]`"
#     "  - 'get_market_insights': Retrieve market insights. Parameters: {'risk_profile': '<risk_profile>'}. Result: A JSON object containing relevant market data. Example: `{'stock_market_trend': 'up', 'interest_rates': 'low', ...}`.  "
#     "  - You MUST call 'get_market_insights' before 'get_recommendations'."
#     "  - If the 'risk_profile' is not one of [CONSERVATIVE, MODERATE, RISKY], return {'status': 'error', 'result': 'Invalid risk_profile'}. "
#     "Respond in the language specified by the 'language' parameter."
# )

# SUPERVISOR_AGENT_INSTRUCTION = (
#     "You are 'Ruffy', the supervisor agent for Rufus Bank (v1.1). All communication uses JSON format. Your message format is: {'agent': 'ruffy', 'action': '<action_name>', 'parameters': {}, 'result': {}, 'status': 'success'/'error', 'language': '<language_code>'}. "
#     "Workflow:"
#     "1. Greet user: {'action': 'greet', 'result': 'Hi, I am Ruffy...'}."
#     "2. Handle requests:"
#     "   - 'get_products': {'action': 'get_products', 'parameters': {'user_id': '<user_id>'}, 'result': <product_info_json>, 'status': 'success'/'error', 'language': '<language_code>'} - Route to 'user-products-agent'."
#     "   - 'recommend_products':"
#     "       a. Get user products: {'action': 'get_products', 'parameters': {'user_id': '<user_id>'}, 'result': <product_info_json>, 'status': 'success'/'error', 'language': '<language_code>'} - Route to 'user-products-agent'."
#     "       b. Infer risk profile: {'action': 'infer_risk_profile', 'parameters': {'products': <product_info_json>}, 'result': {'risk_profile': 'CONSERVATIVE'/'MODERATE'/'RISKY'}, 'status': 'success'/'error', 'language': '<language_code>'}."  # Use rules to infer from product portfolio.
#     "       c. Get market insights: {'action': 'get_market_insights', 'parameters': {'risk_profile': <risk_profile>}, 'result': <market_insights_json>, 'status': 'success'/'error', 'language': '<language_code>'} - Route to 'financial-assistant-agent'."
#     "       d. Get recommendations: {'action': 'get_recommendations', 'parameters': {'user_id': '<user_id>', 'risk_profile': '<risk_profile>'}, 'result': <recommendations_json>, 'status': 'success'/'error', 'language': '<language_code>'} - Route to 'financial-assistant-agent'."
#     "   - 'get_market_insights': {'action': 'get_market_insights', 'parameters': {'risk_profile': '<risk_profile>'}, 'result': <market_insights_json>, 'status': 'success'/'error', 'language': '<language_code>'} - Route to 'financial-assistant-agent'."
#     "3. Handle errors: If an agent returns {'status': 'error'}, log the error and inform the user. For example: {'action': 'error', 'parameters': {'message': 'Failed to retrieve products'}, 'result': 'Sorry, there was an error processing your request.', 'status': 'error', 'language': '<language_code>'}."
#     "4. Clarification: If the user request is unclear, ask clarifying questions:  {'action': 'clarification', 'result': 'Could you please clarify your request?'}."
#     "5. Logging: Log all agent interactions, including messages, parameters, results, and errors.  This is crucial for debugging and monitoring the system."
#     "6. Risk Profile Inference Rules (Example):"
#     "   - If more than 50% of products are low-risk (e.g., savings accounts, CDs), risk_profile = CONSERVATIVE."
#     "   - If more than 50% are moderate-risk (e.g., balanced mutual funds), risk_profile = MODERATE."
#     "   - If more than 50% are high-risk (e.g., stocks, options), risk_profile = RISKY."
#     "   - If no clear majority, risk_profile = MODERATE (default)."
#     "Always respond in the language specified by the 'language' parameter."
# )

# SUPERVISOR_INSTRUCTIONS_FOR_AGENT_1 = "Invoke the 'user-products-agent' to retrieve details about the user's existing bank products using the 'get_products' action. Ensure you provide the <user_id>. When the task involves product recommendations, first use this agent to gather user product information, then proceed to infer the RISK_PROFILE."

# SUPERVISOR_INSTRUCTIONS_FOR_AGENT_2 = "Invoke the 'financial-assistant-agent' for any tasks involving Market Insights or customized financial recommendations using the 'get_recommendations' or 'get_market_insights' actions. Ensure these recommendations align with the user's RISK_PROFILE and bank product offerings."


class GenerativeAIStack(Stack):
    """
    Class to create the GenerativeAIStack resources, which includes the API Gateway,
    Lambda Functions, DynamoDB Table, Streams and Async Processes Infrastructure.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        main_resources_name: str,
        app_config: dict[str],
        **kwargs,
    ) -> None:
        """
        :param scope (Construct): Parent of this stack, usually an 'App' or a 'Stage', but could be any construct.
        :param construct_id (str): The construct ID of this stack (same as aws-cdk Stack 'construct_id').
        :param main_resources_name (str): The main unique identified of this stack.
        :param app_config (dict[str]): Dictionary with relevant configuration values for the stack.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Input parameters
        self.construct_id = construct_id
        self.main_resources_name = main_resources_name
        self.app_config = app_config
        self.deployment_environment = self.app_config["deployment_environment"]

        # Parameter to control the the agents versions (v0, v1, v2)... Only when needed
        self.agents_version = self.app_config["agents_version"]

        # Parameter to enable/disable RAG
        self.enable_rag = self.app_config["enable_rag"]

        # Main methods for the deployment
        self.create_dynamodb_tables()
        self.create_lambda_layers()
        self.create_lambda_functions()
        self.create_bedrock_roles()
        self.create_rag_components()
        self.create_bedrock_child_agents()
        self.create_bedrock_supervisor_agent()

        # Generate CloudFormation outputs
        self.generate_cloudformation_outputs()

    def create_dynamodb_tables(self):
        """
        Create DynamoDB table for the multi-agent-collaboration-demo solution.
        """

        # TODO: Add DynamoDB Table to store conversations in a future version

        # Generic "PK" and "SK", to leverage Single-Table-Design
        self.agents_data_dynamodb_table = aws_dynamodb.Table(
            self,
            "DynamoDB-Table-AgentsData",
            table_name=self.app_config["agents_data_table_name"],
            partition_key=aws_dynamodb.Attribute(
                name="PK", type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="SK", type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        Tags.of(self.agents_data_dynamodb_table).add(
            "Name", self.app_config["agents_data_table_name"]
        )

    def create_lambda_layers(self) -> None:
        """
        Create the Lambda layers that are necessary for the additional runtime
        dependencies of the Lambda Functions.
        """

        # Layer for "LambdaPowerTools" (for logging, traces, observability, etc)
        self.lambda_layer_powertools = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            "Layer-PowerTools",
            layer_version_arn=f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python311-x86_64:5",
        )

        # Layer for "common" Python requirements (fastapi, mangum, pydantic, ...)
        self.lambda_layer_common = aws_lambda.LayerVersion(
            self,
            "Layer-Common",
            code=aws_lambda.Code.from_asset("lambda-layers/common/modules"),
            compatible_runtimes=[
                aws_lambda.Runtime.PYTHON_3_11,
            ],
            description="Lambda Layer for Python with <common> library",
            removal_policy=RemovalPolicy.DESTROY,
            compatible_architectures=[aws_lambda.Architecture.X86_64],
        )

    def create_lambda_functions(self) -> None:
        """
        Create the Lambda Functions for the solution.
        """
        # Get relative path for folder that contains Lambda function source
        # ! Note--> we must obtain parent dirs to create path (that"s why there is "os.path.dirname()")
        PATH_TO_LAMBDA_FUNCTION_FOLDER = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "backend",
        )

        # Lambda Function for the Bedrock Agent Groups
        bedrock_agent_lambda_role = aws_iam.Role(
            self,
            "BedrockAgentLambdaRole",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Bedrock Agent Lambda",
            role_name=f"{self.main_resources_name}-lambda-role-action-groups",
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonDynamoDBFullAccess",
                ),
            ],
        )

        # Lambdas for the Action Group (used for Bedrock Agents)
        self.lambda_action_group_crud_user_products = aws_lambda.Function(
            self,
            "Lambda-AG-UserProductsCRUD",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            handler="agents/crud_user_products/lambda_function.lambda_handler",
            function_name=f"{self.main_resources_name}-bedrock-action-group-crud-user-products",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
                "TABLE_NAME": self.app_config["agents_data_table_name"],
            },
            layers=[self.lambda_layer_powertools],
            role=bedrock_agent_lambda_role,
        )

        self.lambda_action_group_market_insights = aws_lambda.Function(
            self,
            "Lambda-AG-MarketInsights",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            handler="agents/market_insights/lambda_function.lambda_handler",
            function_name=f"{self.main_resources_name}-bedrock-action-group-market-insights",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
                "TABLE_NAME": self.app_config["agents_data_table_name"],
            },
            layers=[self.lambda_layer_powertools],
            role=bedrock_agent_lambda_role,
        )

        # Add permissions to the Lambda functions resource policies.
        # The resource-based policy is to allow an AWS service to invoke your function.
        self.lambda_action_group_crud_user_products.add_permission(
            "AllowBedrockInvoke1",
            principal=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
        )
        self.lambda_action_group_market_insights.add_permission(
            "AllowBedrockInvoke2",
            principal=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
        )

    def create_bedrock_roles(self) -> None:
        """
        Method to create the Bedrock Agent for the chatbot.
        """
        # TODO: refactor this huge function into independent methods... and eventually custom constructs!

        self.bedrock_agent_role = aws_iam.Role(
            self,
            "BedrockAgentRole",
            assumed_by=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
            role_name=f"{self.main_resources_name}-bedrock-agent-role",
            description="Role for Bedrock Agent",
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_FullAccess",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess",
                ),
            ],
        )
        # Add additional IAM actions for the bedrock agent
        self.bedrock_agent_role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelEndpoint",
                    "bedrock:InvokeModelEndpointAsync",
                    "iam:PassRole",
                ],
                resources=["*"],
            )
        )

        # Role for the Bedrock KB
        if self.enable_rag:
            self.bedrock_kb_role = aws_iam.Role(
                self,
                "IAMRole-BedrockKB",
                role_name=f"{self.main_resources_name}-bedrock-kb-role",
                assumed_by=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
                managed_policies=[
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonBedrockFullAccess"
                    ),
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonOpenSearchServiceFullAccess"
                    ),
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonS3FullAccess"
                    ),
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                        "CloudWatchLogsFullAccess"
                    ),
                    # TROUBLESHOOTING: Add additional permissions for the KB
                    aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AdministratorAccess"
                    ),  # TODO: DELETE THIS LINE IN PRODUCTION
                ],
            )

    def create_rag_components(self):
        """
        Method to create the RAG components for the chatbot.
        """

        # Get relative path for folder that contains the kb assets
        # ! Note--> we must obtain parent dirs to create path (that"s why there is "os.path.dirname()")
        PATH_TO_KB_FOLDER = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "knowledge_base",
        )
        PATH_TO_CUSTOM_RESOURCES = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "custom_resources",
        )

        # Create the S3 bucket for uploading the KB assets
        if self.enable_rag:
            s3_bucket_kb = aws_s3.Bucket(
                self,
                "S3-KB",
                bucket_name=f"{self.main_resources_name}-kb-assets-{self.account}",
                auto_delete_objects=True,
                versioned=True,
                encryption=aws_s3.BucketEncryption.S3_MANAGED,
                block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=RemovalPolicy.DESTROY,
            )
            s3_bucket_kb.grant_read_write(
                aws_iam.ServicePrincipal("bedrock.amazonaws.com")
            )

            # Upload assets to S3 bucket KB at deployment time
            s3d.BucketDeployment(
                self,
                "S3Upload-KB",
                sources=[s3d.Source.asset(PATH_TO_KB_FOLDER)],
                destination_bucket=s3_bucket_kb,
                destination_key_prefix="docs/",
            )

            # Create opensearch serverless collection requires a security policy of type encryption. The policy must be a string and the resource contains the collections it is applied to.
            opensearch_serverless_encryption_policy = oss.CfnSecurityPolicy(
                self,
                "OpenSearchServerlessEncryptionPolicy",
                name="encryption-policy",
                policy='{"Rules":[{"ResourceType":"collection","Resource":["collection/*"]}],"AWSOwnedKey":true}',
                type="encryption",
                description="Encryption policy for the opensearch serverless collection",
            )

            # We also need a security policy of type network so that the collection becomes accessable. The policy must be a string and the resource contains the collections it is applied to.
            opensearch_serverless_network_policy = oss.CfnSecurityPolicy(
                self,
                "OpenSearchServerlessNetworkPolicy",
                name="network-policy",
                policy='[{"Description":"Public access for collection","Rules":[{"ResourceType":"dashboard","Resource":["collection/*"]},{"ResourceType":"collection","Resource":["collection/*"]}],"AllowFromPublic":true}]',
                type="network",
                description="Network policy for the opensearch serverless collection",
            )

            # Create the OpenSearch Collection
            opensearch_serverless_collection = oss.CfnCollection(
                self,
                "OpenSearchCollection-KB ",
                name="pdf-collection",
                description="Collection for the PDF documents",
                standby_replicas="DISABLED",
                type="VECTORSEARCH",
            )

            opensearch_serverless_collection.add_dependency(
                opensearch_serverless_encryption_policy
            )
            opensearch_serverless_collection.add_dependency(
                opensearch_serverless_network_policy
            )

            # Create a Custom Resource for the OpenSearch Index (not supported by CDK yet)
            # TODO: Replace to L1 or L2 construct when available!!!!!!
            index_name = f"{self.main_resources_name}-kb-docs"

            # Define the Lambda function that creates a new index in the opensearch serverless collection
            create_index_lambda = aws_lambda.Function(
                self,
                "Index",
                runtime=aws_lambda.Runtime.PYTHON_3_11,
                handler="create_oss_index.handler",
                code=aws_lambda.Code.from_asset(PATH_TO_CUSTOM_RESOURCES),
                timeout=Duration.seconds(300),
                environment={
                    "COLLECTION_ENDPOINT": opensearch_serverless_collection.attr_collection_endpoint,
                    "INDEX_NAME": index_name,
                    "REGION": self.region,
                },
                layers=[self.lambda_layer_common],  # To add requests library
            )

            # Define IAM permission policy for the Lambda function. This function calls the OpenSearch Serverless API to create a new index in the collection and must have the "aoss" permissions.
            create_index_lambda.role.add_to_principal_policy(
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "es:ESHttpPut",
                        "es:*",
                        "iam:CreateServiceLinkedRole",
                        "iam:PassRole",
                        "iam:ListUsers",
                        "iam:ListRoles",
                        "aoss:*",
                    ],
                    resources=["*"],
                )
            )

            # Finally we can create a complete data access policy for the collection that also includes the lambda function that will create the index. The policy must be a string and the resource contains the collections it is applied to.
            opensearch_serverless_access_policy = oss.CfnAccessPolicy(
                self,
                "OpenSearchServerlessAccessPolicy",
                name=f"{self.main_resources_name}-accessp",
                policy=f'[{{"Description":"Access for bedrock","Rules":[{{"ResourceType":"index","Resource":["index/*/*"],"Permission":["aoss:*"]}},{{"ResourceType":"collection","Resource":["collection/*"],"Permission":["aoss:*"]}}],"Principal":["{self.bedrock_agent_role.role_arn}","{self.bedrock_kb_role.role_arn}","{create_index_lambda.role.role_arn}","arn:aws:iam::{self.account}:root"]}}]',
                type="data",
                description="Data access policy for the opensearch serverless collection",
            )

            # Add dependencies to the collection
            opensearch_serverless_collection.add_dependency(
                opensearch_serverless_access_policy
            )

            # Define the request body for the lambda invoke api call that the custom resource will use
            aossLambdaParams = {
                "FunctionName": create_index_lambda.function_name,
                "InvocationType": "RequestResponse",
            }

            # On creation of the stack, trigger the Lambda function we just defined
            trigger_lambda_cr = cr.AwsCustomResource(
                self,
                "IndexCreateCustomResource",
                on_create=cr.AwsSdkCall(
                    service="Lambda",
                    action="invoke",
                    parameters=aossLambdaParams,
                    physical_resource_id=cr.PhysicalResourceId.of("Parameter.ARN"),
                ),
                policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                    resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
                ),
                removal_policy=RemovalPolicy.DESTROY,
                timeout=Duration.seconds(300),
            )

            # Define IAM permission policy for the custom resource
            trigger_lambda_cr.grant_principal.add_to_principal_policy(
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["lambda:*", "iam:CreateServiceLinkedRole", "iam:PassRole"],
                    resources=["*"],
                )
            )

            # Only trigger the custom resource after the opensearch access policy has been applied to the collection
            trigger_lambda_cr.node.add_dependency(opensearch_serverless_access_policy)
            trigger_lambda_cr.node.add_dependency(opensearch_serverless_collection)

            # Create the Bedrock KB
            self.bedrock_knowledge_base = aws_bedrock.CfnKnowledgeBase(
                self,
                "BedrockKB",
                name="kbdocs",
                description="Bedrock knowledge base that contains a relevant projects for the user.",
                role_arn=self.bedrock_kb_role.role_arn,
                knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                    type="VECTOR",
                    vector_knowledge_base_configuration=aws_bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                        embedding_model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1"
                    ),
                ),
                storage_configuration=aws_bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                    type="OPENSEARCH_SERVERLESS",
                    opensearch_serverless_configuration=aws_bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                        collection_arn=opensearch_serverless_collection.attr_arn,
                        vector_index_name=index_name,
                        field_mapping=aws_bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                            metadata_field="AMAZON_BEDROCK_METADATA",  # Must match to Lambda Function
                            text_field="AMAZON_BEDROCK_TEXT_CHUNK",  # Must match to Lambda Function
                            vector_field="bedrock-knowledge-base-default-vector",  # Must match to Lambda Function
                        ),
                    ),
                ),
            )

            # Add dependencies to the KB
            self.bedrock_knowledge_base.add_dependency(opensearch_serverless_collection)
            self.bedrock_knowledge_base.node.add_dependency(trigger_lambda_cr)

            # Create the datasource for the bedrock KB
            bedrock_data_source = aws_bedrock.CfnDataSource(
                self,
                "Bedrock-DataSource",
                name="KbDataSource",
                knowledge_base_id=self.bedrock_knowledge_base.ref,
                description="The S3 data source definition for the bedrock knowledge base containing information about projects.",
                data_source_configuration=aws_bedrock.CfnDataSource.DataSourceConfigurationProperty(
                    s3_configuration=aws_bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                        bucket_arn=s3_bucket_kb.bucket_arn,
                        inclusion_prefixes=["docs"],
                    ),
                    type="S3",
                ),
                vector_ingestion_configuration=aws_bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                    chunking_configuration=aws_bedrock.CfnDataSource.ChunkingConfigurationProperty(
                        chunking_strategy="FIXED_SIZE",
                        fixed_size_chunking_configuration=aws_bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                            max_tokens=300, overlap_percentage=20
                        ),
                    )
                ),
            )
            # Only trigger the custom resource when the kb is completed
            bedrock_data_source.node.add_dependency(self.bedrock_knowledge_base)

        # # TODO: Add the automation for the KB ingestion
        # # ... (manual for now when docs refreshed... could be automated)

    def create_bedrock_child_agents(self):
        """
        Method to create the Bedrock Agents at the lowest hierarchy level (child agents).
        """

        # Create the Bedrock Agent 1
        self.bedrock_agent_financial_products = aws_bedrock.CfnAgent(
            self,
            "BedrockAgentFinancialProductsV1",
            agent_name=f"{self.main_resources_name}-agent-financial-products-{self.agents_version}",
            agent_resource_role_arn=self.bedrock_agent_role.role_arn,
            description="Agent specialized in financial products. Is able to run CRUD operations towards the user products and generate PDF certificates.",
            # foundation_model="amazon.nova-lite-v1:0",
            # foundation_model="amazon.nova-pro-v1:0",
            # foundation_model="anthropic.claude-3-haiku-20240307-v1:0",
            # foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            # foundation_model="anthropic.claude-3-5-sonnet-20240620-v1:0",
            foundation_model=FOUNDATION_MODEL_CHILD_AGENTS,
            instruction=AGENT_1_INSTRUCTION,
            auto_prepare=True,
            action_groups=[
                aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="FetchUserProducts",
                    description="A function that is able to fetch the user products from the database from an input user_id.",
                    action_group_executor=aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.lambda_action_group_crud_user_products.function_arn,
                    ),
                    function_schema=aws_bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            aws_bedrock.CfnAgent.FunctionProperty(
                                name="FetchUserProducts",
                                # the properties below are optional
                                description="Function to fetch the user products based on the input input user_id",
                                parameters={
                                    "user_id": aws_bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="user_id to fetch the user products",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                ),
            ],
        )

        # Create the Bedrock Agent 2
        self.bedrock_agent_financial_assistant = aws_bedrock.CfnAgent(
            self,
            "BedrockAgentFinancialAssistantV1",
            agent_name=f"{self.main_resources_name}-agent-financial-assistant-{self.agents_version}",
            agent_resource_role_arn=self.bedrock_agent_role.role_arn,
            description="Agent specialized in financial advise and knows the best products that rufus bank offers.",
            foundation_model=FOUNDATION_MODEL_CHILD_AGENTS,
            instruction=AGENT_2_INSTRUCTION,
            auto_prepare=True,
            action_groups=[
                aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="FetchMarketInsights",
                    description="A function that is able to fetch the latest market insights knowing the <risk_level> for the user.",
                    action_group_executor=aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.lambda_action_group_market_insights.function_arn,
                    ),
                    function_schema=aws_bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            aws_bedrock.CfnAgent.FunctionProperty(
                                name="FetchMarketInsights",
                                # the properties below are optional
                                description="Function that is able to fetch the latest market insights knowing the <risk_level> for the user.",
                                parameters={
                                    "risk_level": aws_bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Risk level to fetch the market insights",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                ),
            ],
            knowledge_bases=(
                [
                    (
                        aws_bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                            description="The knowledge base for the agent that contains the main BANK PRODUCTS available to be recommended.",
                            knowledge_base_id=self.bedrock_knowledge_base.ref,
                        )
                    ),
                ]
                if self.enable_rag
                else None
            ),
        )

        # Create aliases for the bedrock agents (required for multi-agent-collab setup)
        self.cfn_agent_alias_1 = aws_bedrock.CfnAgentAlias(
            self,
            "BedrockAgentAlias1FinancialProducts",
            agent_alias_name=f"bedrock-agent-alias-financial-products-{self.agents_version}",
            agent_id=self.bedrock_agent_financial_products.ref,
            description="bedrock agent alias 1 (financial-products)",
        )
        self.cfn_agent_alias_1.add_dependency(self.bedrock_agent_financial_products)

        self.cfn_agent_alias_2 = aws_bedrock.CfnAgentAlias(
            self,
            "BedrockAgentAlias2FinancialAssistant",
            agent_alias_name=f"bedrock-agent-alias-financial-assistant-{self.agents_version}",
            agent_id=self.bedrock_agent_financial_assistant.ref,
            description="bedrock agent alias 2 (financial-assistant)",
        )
        self.cfn_agent_alias_2.add_dependency(self.bedrock_agent_financial_assistant)

    def create_bedrock_supervisor_agent(self):
        """
        Method to create the Bedrock Agents at the lowest hierarchy level (supervisor agent).
        """

        # IMPORTANT: I create the Supervisor Agent via an AWS CustomResource because we don't have
        # ... the L1 CDK Constructs yet.  This basically uses the underlying AWS Bedrock API calls
        # TODO: Update to CDK L1 when multi-agent collaboration is supported on CF/CDK
        supervisor_agent_description = "Supervisor Agent for the bank "
        supervisor_agent_name = (
            f"{self.main_resources_name}-create-supervisor-agent-{self.agents_version}"
        )
        cr_create_supervisor_agent = cr.AwsCustomResource(
            self,
            f"BedrockCreateSupervisorAgent{self.agents_version}",
            function_name=supervisor_agent_name,
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            # policy=cr.AwsCustomResourcePolicy.from_statements(
            #     [
            #         aws_iam.PolicyStatement(
            #             actions=[
            #                 "bedrock:CreateAgent",
            #                 "bedrock:UpdateAgent",
            #                 "bedrock:DeleteAgent",
            #                 "iam:PassRole",
            #             ],
            #             resources=["*"],
            #         )
            #     ]
            # ),
            on_create={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "CreateAgentCommand",
                "parameters": {
                    "agentName": supervisor_agent_name,
                    "agentResourceRoleArn": self.bedrock_agent_role.role_arn,
                    "description": supervisor_agent_description,
                    "foundationModel": FOUNDATION_MODEL_SUPERVISOR_AGENT,
                    "instruction": SUPERVISOR_AGENT_INSTRUCTION,
                    "idleSessionTTLInSeconds": 1800,
                    "agentCollaboration": "SUPERVISOR",
                    "orchestrationType": "DEFAULT",
                },
                "physical_resource_id": cr.PhysicalResourceId.of(supervisor_agent_name),
            },
            on_update={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "UpdateAgentCommand",
                "parameters": {
                    "agentId": cr.PhysicalResourceId.from_response("agent.agentId"),
                    "agentName": supervisor_agent_name,
                    "agentResourceRoleArn": self.bedrock_agent_role.role_arn,
                    "description": "Supervisor Agent",
                    "foundationModel": FOUNDATION_MODEL_SUPERVISOR_AGENT,
                    "instruction": SUPERVISOR_AGENT_INSTRUCTION,
                    "idleSessionTTLInSeconds": 1800,
                },
                "physical_resource_id": cr.PhysicalResourceId.of(supervisor_agent_name),
            },
            on_delete={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "DeleteAgentCommand",
                "parameters": {
                    "agentId": cr.PhysicalResourceId.from_response("agent.agentId"),
                    "skipResourceInUseCheck": True,
                },
            },
        )
        # Define IAM permission policy for the custom resource
        cr_create_supervisor_agent.grant_principal.add_to_principal_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["bedrock:*", "iam:PassRole"],
                resources=["*"],
            )
        )

        # Intentionally break/skip remaining resources if Custom Resource for Supervisor Agent fails
        if not cr_create_supervisor_agent.get_response_field("agent.agentId"):
            print(
                "Failed to create supervisor agent in CDK, skipping dependent resources"
            )
            self.supervisor_agent_id = ""
            self.supervisor_agent_alias_id = ""
            return

        # Create the Supervisor to Child Agents associations (for the multi-agent collaboration)
        # IMPORTANT: This is done via a Custom Resource as we don't have L1 Constructs yet.

        # Associate with Agent 1 (financial-products)
        associate_agent_1_name = (
            f"{self.main_resources_name}-associate-agent-1-{self.agents_version}"
        )
        cr_associate_agent_1 = cr.AwsCustomResource(
            self,
            associate_agent_1_name,
            function_name=associate_agent_1_name,
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "AssociateAgentCollaboratorCommand",
                "parameters": {
                    "agentId": cr_create_supervisor_agent.get_response_field(
                        "agent.agentId"
                    ),
                    "agentVersion": "DRAFT",
                    "agentDescriptor": {
                        "aliasArn": self.cfn_agent_alias_1.attr_agent_alias_arn
                    },
                    "collaboratorName": self.bedrock_agent_financial_products.agent_name,
                    "collaborationInstruction": SUPERVISOR_INSTRUCTIONS_FOR_AGENT_1,
                    "relayConversationHistory": "TO_COLLABORATOR",
                },
                "physical_resource_id": cr.PhysicalResourceId.of(
                    associate_agent_1_name
                ),
            },
        )
        # Define IAM permission policy for the custom resource
        cr_associate_agent_1.grant_principal.add_to_principal_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["bedrock:*", "iam:PassRole"],
                resources=["*"],
            )
        )
        # Add dependencies for execution order
        cr_associate_agent_1.node.add_dependency(cr_create_supervisor_agent)
        cr_associate_agent_1.node.add_dependency(self.bedrock_agent_financial_products)

        # Associate with Agent 2 (financial-assistant)
        associate_agent_2_name = (
            f"{self.main_resources_name}-associate-agent-2-{self.agents_version}"
        )
        cr_associate_agent_2 = cr.AwsCustomResource(
            self,
            associate_agent_2_name,
            function_name=associate_agent_2_name,
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "AssociateAgentCollaboratorCommand",
                "parameters": {
                    "agentId": cr_create_supervisor_agent.get_response_field(
                        "agent.agentId"
                    ),
                    "agentVersion": "DRAFT",
                    "agentDescriptor": {
                        "aliasArn": self.cfn_agent_alias_2.attr_agent_alias_arn
                    },
                    "collaboratorName": self.bedrock_agent_financial_assistant.agent_name,
                    "collaborationInstruction": SUPERVISOR_INSTRUCTIONS_FOR_AGENT_2,
                    "relayConversationHistory": "TO_COLLABORATOR",
                },
                "physical_resource_id": cr.PhysicalResourceId.of(
                    associate_agent_2_name
                ),
            },
        )
        # Define IAM permission policy for the custom resource
        cr_associate_agent_2.grant_principal.add_to_principal_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["bedrock:*", "iam:PassRole"],
                resources=["*"],
            )
        )

        # Add dependencies for execution order
        cr_associate_agent_2.node.add_dependency(cr_create_supervisor_agent)
        cr_associate_agent_2.node.add_dependency(self.bedrock_agent_financial_assistant)

        # Prepare Supervisor Agent (via Custom Resource, as not available yet via CF/CDK).
        prepare_supervisor_agent_name = (
            f"{self.main_resources_name}-prepare-supervisor-agent-{self.agents_version}"
        )
        cr_prepare_supervisor_agent = cr.AwsCustomResource(
            self,
            prepare_supervisor_agent_name,
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            on_create={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "PrepareAgentCommand",
                "parameters": {
                    "agentId": cr_create_supervisor_agent.get_response_field(
                        "agent.agentId"
                    )
                },
                "physical_resource_id": cr.PhysicalResourceId.of(
                    prepare_supervisor_agent_name
                ),
            },
            on_update={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "PrepareAgentCommand",
                "parameters": {
                    "agentId": cr_create_supervisor_agent.get_response_field(
                        "agent.agentId"
                    )
                },
                "physical_resource_id": cr.PhysicalResourceId.of(
                    prepare_supervisor_agent_name
                ),
            },
            # TODO: Validate if delete agent makes sense here ?
            on_delete={
                "service": "@aws-sdk/client-bedrock-agent",
                "action": "DeleteAgentCommand",
                "parameters": {
                    "agentId": cr_create_supervisor_agent.get_response_field(
                        "agent.agentId"
                    ),
                    "skipResourceInUseCheck": True,
                },
            },
        )

        # Add dependencies for execution order
        cr_prepare_supervisor_agent.node.add_dependency(self.cfn_agent_alias_1)
        cr_prepare_supervisor_agent.node.add_dependency(self.cfn_agent_alias_2)
        cr_prepare_supervisor_agent.node.add_dependency(cr_associate_agent_1)
        cr_prepare_supervisor_agent.node.add_dependency(cr_associate_agent_2)

        # Enable alias for the Supervisor Agent to be used in other applications
        cfn_agent_alias_supervisor = aws_bedrock.CfnAgentAlias(
            self,
            f"BedrockAgentAliasSupervisor={self.agents_version}",
            agent_alias_name=f"bedrock-agent-alias-supervisor-{self.agents_version}",
            agent_id=cr_create_supervisor_agent.get_response_field("agent.agentId"),
            description="bedrock agent alias (supervisor)",
        )
        cfn_agent_alias_supervisor.node.add_dependency(cr_prepare_supervisor_agent)

        # This string will be as <AGENT_ID>|<AGENT_ALIAS_ID>
        agent_alias_string = cfn_agent_alias_supervisor.ref

        # Create SSM Parameters for the agent alias to use in the Lambda functions
        # Note: can not be added as Env-Vars due to circular dependency. Thus, SSM Params (decouple)
        aws_ssm.StringParameter(
            self,
            "SSMAgentAlias",
            parameter_name=f"/{self.deployment_environment}/aws-wpp/bedrock-agent-alias-id-full-string",
            string_value=agent_alias_string,
        )
        aws_ssm.StringParameter(
            self,
            "SSMAgentId",
            parameter_name=f"/{self.deployment_environment}/aws-wpp/bedrock-agent-id",
            string_value=cr_create_supervisor_agent.get_response_field("agent.agentId"),
        )

    def generate_cloudformation_outputs(self) -> None:
        """
        Method to add the relevant CloudFormation outputs.
        """

        CfnOutput(
            self,
            "DeploymentEnvironment",
            value=self.app_config["deployment_environment"],
            description="Deployment environment",
        )

        # TODO: Identify valuable outputs and add them!
