from aws_cdk import (
    Stack,
    aws_logs as logs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_glue as glue,
    aws_bedrock as bedrock,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from cdklabs.generative_ai_cdk_constructs import (
    bedrock as bedrock_kb
)
from cdk_nag import (
    NagSuppressions
)
from constructs import Construct
from os import path

from . import prompts

# LLM Models
embedding_llm_model_id = bedrock_kb.BedrockFoundationModel.COHERE_EMBED_ENGLISH_V3
inference_llm_model_id = bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_SONNET_20240229_V1_0

# Helper function that retries calls to Bedrock when throttled
def add_bedrock_retries(task):
    task.add_retry(
            max_attempts=5,
            backoff_rate=2,
            interval=Duration.seconds(5),
            errors=["ThrottlingException", "LimitExceededException"]
    )

class EifmStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        #---------------------------------------------------------------------------
        # CloudWatch log group for Step Function logs
        #---------------------------------------------------------------------------
        log_group = logs.LogGroup(self, "EIFMappingLogGroup",
            log_group_name="EIFMappingLogGroup",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.ONE_MONTH
        )
        #---------------------------------------------------------------------------

        #---------------------------------------------------------------------------
        # S3 Bucket to hold datasets, input files, and mapping output
        #---------------------------------------------------------------------------
        eif_bucket = s3.Bucket(self, "EIFMappingBucket",  
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            server_access_logs_prefix="accesslog/",
            auto_delete_objects=True, 
            removal_policy=RemovalPolicy.DESTROY
        )
                
        # Deploy the source datasets, inputs, and Glue script in this repository to the bucket
        s3_deployment.BucketDeployment(self, "DatasetsDeployment",
            destination_bucket=eif_bucket,
            destination_key_prefix="datasets/",
            sources=[s3_deployment.Source.asset(path.normpath(path.join(__file__, "../assets/datasets/")))]
        )
        s3_deployment.BucketDeployment(self, "InputDatasetsDeployment",
            destination_bucket=eif_bucket,
            destination_key_prefix="input/",
            sources=[s3_deployment.Source.asset(path.normpath(path.join(__file__, "../assets/input/")))]
        )
        glue_script_deployment = s3_deployment.BucketDeployment(self, "GlueScriptDeployment",
            destination_bucket=eif_bucket,
            destination_key_prefix="glue_scripts/",
            sources=[s3_deployment.Source.asset(path.normpath(path.join(__file__, "../glue_scripts/")))]
        )

        #---------------------------------------------------------------------------
        # Bedrock knowledge base
        #---------------------------------------------------------------------------
        kb_role = iam.Role(self, "KnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com")
        )
        kb_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=[embedding_llm_model_id.as_arn(self)]
        ))
        kb = bedrock_kb.KnowledgeBase(self, 'EIFMappingKnowledgeBase',
            embeddings_model= embedding_llm_model_id,
            name = "EIFMappingKnowledgeBase",
            description = "Knowledge base for EIF mapping",
            existing_role=kb_role
        )

        CfnOutput(self, "KnowledgeBaseId", value=kb.knowledge_base_id)

        kb_data_source = bedrock_kb.S3DataSource(self, 'KnowledgeBaseDataSource',
            bucket= eif_bucket,
            inclusion_prefixes= ["datasets"],
            knowledge_base=kb,
            data_source_name='NAICS_Data',
            chunking_strategy= bedrock_kb.ChunkingStrategy.FIXED_SIZE,
            max_tokens=50,
            overlap_percentage=10
        )
        CfnOutput(self, "DataSourceId", value=kb_data_source.data_source_id)

        # Bedrock model for performing mapping
        inf_model=bedrock.FoundationModel.from_foundation_model_id(self, "MappingModel", inference_llm_model_id)

        #---------------------------------------------------------------------------
        # Glue job
        #---------------------------------------------------------------------------
        # Create IAM role for Glue job
        glue_role = iam.Role(self, "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
            ]
        )
        # Add inline policy for S3 access
        glue_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"],
            resources=[
                eif_bucket.bucket_arn,
                eif_bucket.arn_for_objects("*")
            ]
        ))
        glue_job = glue.CfnJob(self, "CreateGlueCleaningJob",
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location="s3://{}/glue_scripts/format_output.py".format(eif_bucket.bucket_name)
            ),
            name="eif-cleaning-job",
            role=glue_role.role_arn,
            number_of_workers=2,
            worker_type="G.1X"
        )
        glue_job.node.add_dependency(glue_script_deployment)
   
        #---------------------------------------------------------------------------
        # Step Functions
        #---------------------------------------------------------------------------
        # Step 1: Clean activity description using LLM
        clean_activity_description = tasks.BedrockInvokeModel(
            self,
            "CleanActivityDescription",
            model=inf_model,
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": sfn.JsonPath.format(
                                        prompts.clean_text_prompt,
                                        sfn.JsonPath.string_at("$.Commodity"),
                                        sfn.JsonPath.string_at("$.CommodityDescription"),
                                        sfn.JsonPath.string_at("$.ExtendedDescription"),
                                        sfn.JsonPath.string_at("$.ContractName")
                                    )
                                }
                            ]
                        }
                    ]
                }
            ),
            result_selector={
                "SimplifiedDescription.$": "$.Body.content[0].text"
            },
            result_path= "$.CleanedActivity"
        )
        add_bedrock_retries(clean_activity_description)

        # Step 2: Match activity to possible NAICS descriptions and codes using knowledge base
        generate_possible_matches = tasks.CallAwsService(
            self,
            "GeneratePossibleEIFMatches",
            service="bedrockagentruntime",
            action="retrieveAndGenerate",
            parameters={
                "Input": {
                    "Text": sfn.JsonPath.format("{}", sfn.JsonPath.string_at("$.CleanedActivity.SimplifiedDescription"))
                },
                "RetrieveAndGenerateConfiguration": {
                "KnowledgeBaseConfiguration": {
                  "GenerationConfiguration": {
                    "InferenceConfig": {
                      "TextInferenceConfig": {
                        "MaxTokens": 512,
                        "Temperature": 0,
                        "TopP": 1
                      }
                    },
                    "PromptTemplate": {
                      "TextPromptTemplate": prompts.possible_eio_matches_system_prompt
                    }
                  },
                  "KnowledgeBaseId": kb.knowledge_base_id,
                  "ModelArn": inf_model.model_arn,
                  "RetrievalConfiguration": {
                    "VectorSearchConfiguration": {
                      "NumberOfResults": 3
                    }
                  }
                },
                "Type": "KNOWLEDGE_BASE"
              }
            },
            result_selector={
                "NAICSOptions": sfn.JsonPath.string_to_json("$.Output.Text")
            },
            result_path= "$.PossibleMatches",
            iam_resources=["*"]
        )
        add_bedrock_retries(generate_possible_matches)

        # Step 3: Choose best EIF match from possible choices using LLM
        choose_best_eif_match = tasks.BedrockInvokeModel(
            self,
            "ChooseBestEIFMatch",
            model=inf_model,
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": sfn.JsonPath.format(
                                        prompts.best_eif_prompt,
                                        sfn.JsonPath.string_at("$.CleanedActivity.SimplifiedDescription"),
                                        sfn.JsonPath.string_at("$.PossibleMatches.NAICSOptions.NAICSCode1"),
                                        sfn.JsonPath.string_at("$.PossibleMatches.NAICSOptions.NAICSTitle1"),
                                        sfn.JsonPath.string_at("$.PossibleMatches.NAICSOptions.NAICSCode2"),
                                        sfn.JsonPath.string_at("$.PossibleMatches.NAICSOptions.NAICSTitle2"),
                                        sfn.JsonPath.string_at("$.PossibleMatches.NAICSOptions.NAICSCode3"),
                                        sfn.JsonPath.string_at("$.PossibleMatches.NAICSOptions.NAICSTitle3")
                                    )
                                }
                            ]
                        }
                    ]
                }
            ),
            result_selector={
                "BestChoice.$": "States.StringToJson($.Body.content[0].text)"
            },
            result_path= "$.MappedEIF"
        )
        add_bedrock_retries(choose_best_eif_match)

        # Step 4: Format output for later use
        format_output = sfn.Pass(
            self,
            "FormatOutput",
            parameters={
                "Commodity.$": "$.Commodity",
                "CommodityDescription.$": "$.CommodityDescription",
                "ExtendedDescription.$": "$.ExtendedDescription",
                "ContractName.$": "$.ContractName",
                "SimplifiedDescription.$": "$.CleanedActivity.SimplifiedDescription",
                "PossibleMatches.$": "$.PossibleMatches.NAICSOptions",
                "MappedNAICSCode.$": "$.MappedEIF.BestChoice.BestNAICSCode",
                "MappedNAICSTitle.$": "$.MappedEIF.BestChoice.BestNAICSTitle",
                "MappingJustification.$": "$.MappedEIF.BestChoice.Justification"
                }
        )

        ### Loop mapping steps over each record in input file
        eif_mapping_chain = (
            sfn.Chain.start(clean_activity_description)
            .next(generate_possible_matches)
            .next(choose_best_eif_match)
            .next(format_output)
        )
        eif_mapping = sfn.DistributedMap(
            self,
            "MapEmissionsFactors",
            label="MapEmissionsFactors",
            map_execution_type= sfn.StateMachineType.STANDARD,
            max_concurrency=5,
            tolerated_failure_percentage=10,
            item_reader=sfn.S3CsvItemReader(
                bucket=eif_bucket,
                key="input/activities.csv",
                csv_headers=sfn.CsvHeaders.use_first_row()
            ),
            item_selector={
                "Commodity.$": "$$.Map.Item.Value.Commodity",
                "CommodityDescription.$": "$$.Map.Item.Value.CommodityDescription",
                "ExtendedDescription.$": "$$.Map.Item.Value.ExtendedDescription",
                "ContractName.$": "$$.Map.Item.Value.ContractName"
            },
            result_writer=sfn.ResultWriter(
                bucket=eif_bucket,
                prefix="mapping-runs"
            )
        ).item_processor(eif_mapping_chain)

        ### The Glue job that cleans and merges the mapped activities into a single output file requires the source bucket to have all the same data format.
        # Read the output manifest to determine how many output files there are
        read_manifest = tasks.CallAwsService(
            self,
            "ReadMapExecutionManifest",
            service="s3",
            action="getObject",
            parameters={
                "Bucket.$": "$.ResultWriterDetails.Bucket",
                "Key.$": "$.ResultWriterDetails.Key"
            },
            result_selector={
                "Manifest.$": "States.StringToJson($.Body)"
            },
            output_path="$.Manifest",
            iam_resources=[eif_bucket.arn_for_objects("*")]
        )

        # Move the successful matches to a new prefix for the Glue job
        move_output = tasks.CallAwsService(
            self,
            "CopyObjectToProcessingPrefix",
            service="s3",
            action="copyObject",
            parameters={
                "Bucket.$": "$.Bucket",
                "CopySource": sfn.JsonPath.format("{}/{}", sfn.JsonPath.string_at("$.Bucket"), sfn.JsonPath.string_at("$.SourceKey")),
                "Key": sfn.JsonPath.format("successful-mappings/SUCCEEDED_{}.json", sfn.JsonPath.string_at("$.DestinationKey"))
            },
            iam_resources=[eif_bucket.arn_for_objects("*")]
        )
        move_successes = sfn.Map(
            self,
            "MoveSuccessfulRunsToProcessingPrefix",
            items_path="$.ResultFiles.SUCCEEDED",
            item_selector={
                "Bucket.$": "$.DestinationBucket",
                "SourceKey.$": "$$.Map.Item.Value.Key",
                "DestinationKey.$": "$$.Map.Item.Index"
            }
        ).item_processor(move_output)

        # Clean mapped factors into human readable CSV
        run_glue_job = tasks.GlueStartJobRun(
            self,
            "CleanSuccessfulMappedFactors",
            glue_job_name=glue_job.name,
            arguments=sfn.TaskInput.from_object({
                "--EIF_bucket": eif_bucket.bucket_name
            })
        )

        ### Put all the steps together into the complete state machine
        full_chain = eif_mapping.next(read_manifest.next(move_successes.next(run_glue_job)))
        eif_sfn = sfn.StateMachine(
            self,
            "EIFMappingStateMachine",
            state_machine_name="EIFMapping",
            definition_body=sfn.DefinitionBody.from_chainable(full_chain),
            removal_policy=RemovalPolicy.DESTROY,
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL
            )
        )
        eif_bucket.grant_read_write(eif_sfn.role)
        eif_sfn.role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:RetrieveAndGenerate", "bedrock:Retrieve"],
            resources=[kb.knowledge_base_arn]
        ))
        CfnOutput(self, "StateMachineARN", value=eif_sfn.state_machine_arn)

        #---------------------------------------------------------------------------
        # cdk-nag suppressions
        #---------------------------------------------------------------------------
        NagSuppressions.add_resource_suppressions_by_path(self, 
            path=[
                "/EIFMappingStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/DefaultPolicy/Resource",
                "/EIFMappingStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/Resource",
                "/EIFMappingStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/Resource",
                "/EIFMappingStack/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/Resource",
                "/EIFMappingStack/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/DefaultPolicy/Resource"
            ], 
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Configured by cdk construct"
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Configured by cdk construct"
                },
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Configured by cdk construct"
                }
            ]
        )
        NagSuppressions.add_resource_suppressions(
            construct=glue_role,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Glue job needs managed policy AWSGlueServiceRole to function"
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Glue job interacts with all objects in bucket"
                }
            ],
            apply_to_children=True
        )
        NagSuppressions.add_resource_suppressions(
            construct=eif_sfn,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Configured by construct"
                }
            ],
            apply_to_children=True
        )