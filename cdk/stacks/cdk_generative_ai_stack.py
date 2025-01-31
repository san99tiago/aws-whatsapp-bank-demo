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
from cdklabs.generative_ai_cdk_constructs import bedrock


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
        self.create_bedrock_components()

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

        # Lambda Function for the Bedrock Agent Group (fetch recipes)
        bedrock_agent_lambda_role = aws_iam.Role(
            self,
            "BedrockAgentLambdaRole",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Bedrock Agent Lambda",
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

    def create_bedrock_components(self) -> None:
        """
        Method to create the Bedrock Agent for the chatbot.
        """
        # TODO: refactor this huge function into independent methods... and eventually custom constructs!

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

        # Add permissions to the Lambda function resource policy. You use a resource-based policy to allow an AWS service to invoke your function.
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

        bedrock_agent_role = aws_iam.Role(
            self,
            "BedrockAgentRole",
            assumed_by=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
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
        bedrock_agent_role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelEndpoint",
                    "bedrock:InvokeModelEndpointAsync",
                ],
                resources=["*"],
            )
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

            # Role for the Bedrock KB
            bedrock_kb_role = aws_iam.Role(
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

            # Create a Custom Resource for the OpenSearch Index (not supported by CDK yet)
            # TODO: Replace to L1 or L2 construct when available!!!!!!
            # Define the index name
            index_name = "kb-docs"

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
                policy=f'[{{"Description":"Access for bedrock","Rules":[{{"ResourceType":"index","Resource":["index/*/*"],"Permission":["aoss:*"]}},{{"ResourceType":"collection","Resource":["collection/*"],"Permission":["aoss:*"]}}],"Principal":["{bedrock_agent_role.role_arn}","{bedrock_kb_role.role_arn}","{create_index_lambda.role.role_arn}","arn:aws:iam::{self.account}:root"]}}]',
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
            bedrock_knowledge_base = aws_bedrock.CfnKnowledgeBase(
                self,
                "BedrockKB",
                name="kbdocs",
                description="Bedrock knowledge base that contains a relevant projects for the user.",
                role_arn=bedrock_kb_role.role_arn,
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
            bedrock_knowledge_base.add_dependency(opensearch_serverless_collection)
            bedrock_knowledge_base.node.add_dependency(trigger_lambda_cr)

            # Create the datasource for the bedrock KB
            bedrock_data_source = aws_bedrock.CfnDataSource(
                self,
                "Bedrock-DataSource",
                name="KbDataSource",
                knowledge_base_id=bedrock_knowledge_base.ref,
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
            bedrock_data_source.node.add_dependency(bedrock_knowledge_base)

        # # TODO: Add the automation for the KB ingestion
        # # ... (manual for now when docs refreshed... could be automated)

        # Create the Bedrock Agent 1
        self.bedrock_agent_financial_products = aws_bedrock.CfnAgent(
            self,
            "BedrockAgentFinancialProductsV1",
            agent_name=f"{self.main_resources_name}-agent-financial-products-{self.agents_version}",
            agent_resource_role_arn=bedrock_agent_role.role_arn,
            description="Agent specialized in financial products. Is able to run CRUD operations towards the user products.",
            foundation_model="amazon.nova-lite-v1:0",
            # foundation_model="amazon.nova-pro-v1:0",
            # foundation_model="anthropic.claude-3-haiku-20240307-v1:0",
            # foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            # foundation_model="anthropic.claude-3-5-sonnet-20240620-v1:0",
            instruction="You are a specialized agent in giving back information about User Products for the Bank. In case that products operations are requested, they must provide the <user_id> parameter, so that you can obtain all the bank products of the user. Never give back additional information than the one requested (only the corresponding user products). Always answer in the SAME language as the input.",
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
            agent_resource_role_arn=bedrock_agent_role.role_arn,
            description="Agent specialized in financial advise and knows the best products that the bank offers.",
            foundation_model="amazon.nova-lite-v1:0",
            # foundation_model="amazon.nova-pro-v1:0",
            # foundation_model="anthropic.claude-3-5-sonnet-20240620-v1:0",
            instruction="You are a specialized financial assistant agent that will be able to get the current user products, and then with the help of the <FetchMarketInsights> and the knowledge base, obtain the best advise for the users. If the FetchMarketInsights details are needed, you must ask for the RISK_PROFILE, and let them choose between [CONSERVATIVE, MODERATE, RISKY], if they provide similar words, always pass them as the ones provided in list in CAPITAL case as the <risk_level> parameter. The goal is to always recommend products or actions aligned with the <user_id> and <risk_level> details, so that based on the <BANK INVESTMENT PRODUCTS> document, you can provide the best financial product for the user. Always answer in the SAME language as the input.",
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
                            knowledge_base_id=bedrock_knowledge_base.ref,
                        )
                    ),
                ]
                if self.enable_rag
                else None
            ),
        )

        # # TODO: Add the supervisor agent via CDK when multi-agent-collab is ready
        # self.bedrock_agent_supervisor = aws_bedrock.CfnAgent(
        #     self,
        #     "BedrockAgentSupervisorV1",
        #     agent_name=f"{self.main_resources_name}-agent-supervisor-{self.agents_version}",
        #     agent_resource_role_arn=bedrock_agent_role.role_arn,
        #     description="You are a specialized SUPERVISOR Agent that orchestrates the user-products-agent and the financial-assistant-agent to help the customers.",
        #     foundation_model="amazon.nova-lite-v1:0",
        #     # foundation_model="amazon.nova-pro-v1:0",
        #     # foundation_model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        #     # instruction="You are a specialized SUPERVISOR agent that is able to collaborate with the user-products-agent and the financial-assistant-agent to help the customers. Make sure that the user provides the <user_id> when asking about financial products. Always answer in the SAME language as the input.",
        #     instruction="You are a specialized SUPERVISOR agent that is able to collaborate with the user-products-agent and the financial-assistant-agent to help the customers. Always answer in the SAME language as the input.",
        #     instruction="You are a specialized SUPERVISOR agent that is able to collaborate with the user-products-agent (for questions related to existing user products) and the financial-assistant-agent (to help customers to get advise on their best products based on their risk profile). Always answer in the SAME language as the input.",
        #     instruction="You are a specialized SUPERVISOR agent that is able to collaborate with the user-products-agent (for questions related to existing user products) and the financial-assistant-agent (to help customers to get advise on their best products based on their risk profile). If a customer asks to DETECT/INFER the risk profile, use the "user-products-agent" and choose a category, then proceed to use the "financial-assistant-agent" to share the advised products. Always answer in the SAME language as the input. - When a tool fetches results, always format and include them in your final response within <answer> </answer> tags. Use a clear and structured format for readability.",
        #     instruction="You are a specialized SUPERVISOR agent that is able to collaborate with the user-products-agent (for questions related to existing user products) and the financial-assistant-agent (to help customers to get advise on their best products based on their risk profile). If a customer asks for recommded products, FIRST run the "user-products-agent" infer his risk_profile, SECOND run the "financial-assistant-agent" to find the recommended product. Always answer in the SAME language as the input. - When a tool fetches results, always format and include them in your final response within <answer> </answer> tags. Use a clear and structured format for readability.",
        #     instruction="You are a specialized SUPERVISOR agent that is able to collaborate with the "user-products-agent" (for questions related to existing user products). When a customer asks for recommded products, FIRST run the "user-products-agent" and from the returned products, INFER his risk_profile, always make a choice from [CONSERVATIVE, MODERATE, RISKY], SECOND run the "financial-assistant-agent" to find the recommended product based on the risk_profile. Always answer in the SAME language as the input. - When a tool fetches results, always format and include them in your final response within <answer> </answer> tags. Use a clear and structured format for readability.",
        #     instruction="You are a specialized SUPERVISOR agent that is able to collaborate with the "user-products-agent" (for questions related to existing user products). When a customer asks for recommded products, FIRST run the "user-products-agent" and from the returned products, INFER his risk_profile, always make a choice from [CONSERVATIVE, MODERATE, RISKY], SECOND run the "financial-assistant-agent" to find the recommended product based on the risk_profile. - When a tool fetches results, always format and include them in your final response within <answer> </answer> tags. Use a clear and structured format for readability. Always answer in the SAME language as the input.",
        #     auto_prepare=True,
        # )

        # Create aliases for the bedrock agents (required for multi-agent-collab setup)
        cfn_agent_alias_1 = aws_bedrock.CfnAgentAlias(
            self,
            "BedrockAgentAlias1FinancialProducts",
            agent_alias_name=f"bedrock-agent-alias-financial-products-{self.agents_version}",
            agent_id=self.bedrock_agent_financial_products.ref,
            description="bedrock agent alias 1 (financial-products)",
        )
        cfn_agent_alias_1.add_dependency(self.bedrock_agent_financial_products)

        cfn_agent_alias_2 = aws_bedrock.CfnAgentAlias(
            self,
            "BedrockAgentAlias2FinancialAssistant",
            agent_alias_name=f"bedrock-agent-alias-financial-assistant-{self.agents_version}",
            agent_id=self.bedrock_agent_financial_assistant.ref,
            description="bedrock agent alias 2 (financial-assistant)",
        )
        cfn_agent_alias_2.add_dependency(self.bedrock_agent_financial_assistant)

        # # NOTE: commented until used via SDK in later projects
        # cfn_agent_alias_supervisor = aws_bedrock.CfnAgentAlias(
        #     self,
        #     "BedrockAgentAliasSupervisor",
        #     agent_alias_name="bedrock-agent-alias-supervisor",
        #     agent_id=self.bedrock_agent_supervisor.ref,
        #     description="bedrock agent alias (supervisor)",
        # )
        # cfn_agent_alias_supervisor.add_dependency(self.bedrock_agent_supervisor)

        # # This string will be as <AGENT_ID>|<AGENT_ALIAS_ID>
        # agent_alias_string = cfn_agent_alias_supervisor.ref

        # # Create SSM Parameters for the agent alias to use in the Lambda functions
        # # Note: can not be added as Env-Vars due to circular dependency. Thus, SSM Params (decouple)
        # aws_ssm.StringParameter(
        #     self,
        #     "SSMAgentAlias",
        #     parameter_name=f"/{self.deployment_environment}/aws-wpp/bedrock-agent-alias-id-full-string",
        #     string_value=agent_alias_string,
        # )
        # aws_ssm.StringParameter(
        #     self,
        #     "SSMAgentId",
        #     parameter_name=f"/{self.deployment_environment}/aws-wpp/bedrock-agent-id",
        #     string_value=self.bedrock_agent_supervisor.ref,
        # )

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
