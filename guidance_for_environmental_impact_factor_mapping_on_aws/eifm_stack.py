from aws_cdk import (
    Stack,
    aws_sagemaker as sagemaker,
    aws_iam as iam,
    aws_codecommit as codecommit,
    aws_ssm as ssm,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_s3_deployment as s3_deployment,
    RemovalPolicy,
    Fn
)
from cdk_nag import (
    NagSuppressions
)
from constructs import Construct
from os import path


class EifmStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        notebook_instance_name = "EifmNotebook"

        # vpc for the sagemaker notebook to run in
        notebook_vpc = ec2.Vpc(self, f"{notebook_instance_name}Vpc",
                      max_azs=1,
                   subnet_configuration=[ec2.SubnetConfiguration(
                       subnet_type=ec2.SubnetType.PUBLIC,
                       name="Public",
                   ), ec2.SubnetConfiguration(
                       subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                       name="Private",
                   )
                   ],
                   nat_gateways=1
                   )

        # security group for the sagemaker notebook
        notebook_sg = ec2.SecurityGroup.from_security_group_id(self, f"{notebook_instance_name}SG", notebook_vpc.vpc_default_security_group, mutable=False)

        # interface endpoint for the notebook to use when accessing S3
        # https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html#accessing-bucket-and-aps-from-interface-endpoints
        s3_interface_endpoint = notebook_vpc.add_interface_endpoint("S3InterfaceEndpoint", service=ec2.InterfaceVpcEndpointAwsService.S3, security_groups=[notebook_sg], private_dns_enabled=False)

        # repository to hold the sagemaker notebook code stored under source/notebook_source
        demo_notebook_repo = codecommit.Repository(
            self, f"{notebook_instance_name}Repo",
            repository_name=f"{notebook_instance_name}Repo",
            code=codecommit.Code.from_directory(
                path.normpath(path.join(__file__, "../../source/notebook_source")))
        )

        # role that the sagemaker notebook assumes
        demo_notebook_role = iam.Role(
            self, f"{notebook_instance_name}Role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"))

        # grant the notebook permissions to pull from the CodeCommit repository
        pull_grant = demo_notebook_repo.grant_pull(demo_notebook_role)

        # S3 bucket to hold datasets, inputs, outputs
        input_output_bucket = s3.Bucket(self, "InputOutputBucket", 
                                        auto_delete_objects=True, 
                                        removal_policy=RemovalPolicy.DESTROY, 
                                        enforce_ssl=True,
                                        server_access_logs_prefix="accesslog/")
        
        # grant the notebook permissions to read and write from this bucket omitting the accesslogs/ prefix
        input_output_bucket.grant_read_write(demo_notebook_role, "datasets/*")
        input_output_bucket.grant_read_write(demo_notebook_role, "input/*")
        input_output_bucket.grant_read_write(demo_notebook_role, "outputs/*")

        # deploy the files in this repository under source/s3_files to the bucket
        s3_deployment.BucketDeployment(self, "InputOutputDeployment",
                                       destination_bucket=input_output_bucket,
                                       sources=[s3_deployment.Source.asset(path.normpath(path.join(__file__, "../../source/s3_files")))])


        # create ssm parameters for the s3 interface endpoint url and bucket name so that the notebook can look them up
        s3_interface_endpoint_url_parameter = ssm.StringParameter(self, "S3InterfaceEndpointParameter", string_value=Fn.join("", ["https://bucket", Fn.select(1, Fn.split("*", Fn.select(0, s3_interface_endpoint.vpc_endpoint_dns_entries), assumed_length=2))]), parameter_name="s3-interface-endpoint-url")
        s3_interface_endpoint_url_parameter.grant_read(demo_notebook_role)
        input_output_bucket_parameter = ssm.StringParameter(self, "InputOutputBucketParameter", string_value=input_output_bucket.bucket_name, parameter_name="input-output-bucket-name")
        input_output_bucket_parameter.grant_read(demo_notebook_role)

        # policy to let the notebook log to cloudwatch
        cloudwatch_logging_policy = iam.Policy(
            self,
            "CloudWatchLoggingPolicy",
            statements=[iam.PolicyStatement(effect=iam.Effect.ALLOW, actions=["logs:CreateLogGroup",
                                                                              "logs:CreateLogStream",
                                                                              "logs:PutLogEvents"], resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/sagemaker/NotebookInstances:log-stream:{notebook_instance_name}/*"])]
        )
        # attach that policy
        cloudwatch_logging_policy.attach_to_role(demo_notebook_role)

        # create the notebook instance
        notebook = sagemaker.CfnNotebookInstance(
            self, notebook_instance_name,
            notebook_instance_name=notebook_instance_name,
            instance_type="ml.g4dn.xlarge",
            platform_identifier="notebook-al2-v2",
            default_code_repository=demo_notebook_repo.repository_clone_url_http,
            role_arn=demo_notebook_role.role_arn,
            security_group_ids=[notebook_sg.security_group_id],
            subnet_id=notebook_vpc.private_subnets[0].subnet_id,
            direct_internet_access='Disabled'
        )

        # The notebook cannot be deployed until its role has been granted permissions to pull from the repository
        notebook.node.add_dependency(pull_grant)

        # cdk-nag suppressions
        NagSuppressions.add_resource_suppressions(notebook_vpc, [{"id": "AwsSolutions-VPC7", "reason": "No flow logs for demo purposes."}])
        NagSuppressions.add_resource_suppressions(demo_notebook_role, [{"id": "AwsSolutions-IAM5", "reason": "grant_read_write uses wildcard"}], True)
        NagSuppressions.add_resource_suppressions_by_path(self, ["/EifmStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/DefaultPolicy/Resource", "/EifmStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/Resource", "/EifmStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/Resource"], [{"id": "AwsSolutions-IAM4", "reason": "Configured by cdk construct"}, {"id": "AwsSolutions-IAM5", "reason": "Configured by cdk construct"}, {"id": "AwsSolutions-L1", "reason": "Configured by cdk construct"}])
        NagSuppressions.add_resource_suppressions(cloudwatch_logging_policy, [{"id": "AwsSolutions-IAM5", "reason": "Resources are restricted to notebook instance."}])
        NagSuppressions.add_resource_suppressions(notebook, [{"id": "AwsSolutions-SM2", "reason": "Using default encryption settings"}])
        
