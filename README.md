## Introduction

This code is an example deployment of the [Guidance for Environmental Impact Factor Mapping on AWS](https://aws.amazon.com/solutions/guidance/environmental-impact-factor-mapping-on-aws/). It is intended to demonstrate how to use semantic text matching with large language models to perform emission factor matching. It accepts a single CSV of business activities and outputs a single CSV containing the mapped emissions factors.

Note that deploying this CDK application will create resources in your AWS account that include the following:
- An Amazon S3 bucket
- An AWS Step Functions state machine
- An AWS Glue job
- An Amazon Bedrock Knowledge Base backed by an Amazon OpenSearch Service serverless collection
- Relevant Amazon IAM roles, policies, and permissions

## Task: Product carbon footprinting with EIO-LCA (excerpt from CaML)

Economic input-output life cycle assessment (EIO-LCA) is a method to estimate the carbon footprint of a product or activity based on its sale value. There are databases such as [USEEIO](https://www.epa.gov/land-research/us-environmentally-extended-input-output-useeio-technical-content) which publish the carbon emissions associated with industry sectors in the economy on a per unit currency basis. EIO-LCA estimates are compatible with [Greenhouse Gas Protocol](https://ghgprotocol.org/), and can be used for external reporting of scope 3 impacts. Given that the carbon emission estimate is only based on sale value of a product, it is an approximation and roughly within 2X the value of true emissions as per a [recent study](https://onlinelibrary.wiley.com/doi/pdf/10.1111/jiec.13271). 

We automate the process of mapping products to their EIO industry sectors based on text descriptions. This is one of the key steps in life cycle assessment that is done manually in practice. Our solution alleviates this manual overhead, and scales to any type of product. In a nutshell, we use large language models to match industry sectors based on semantic text similarity. The algorithm recommends the EIO industry sector in three steps: (i) paraphrases the given input using a generative LLM (Claude 3 Sonnet) (ii) finds the relevant EIO industry sectors using an embedding model (Cohere English v3), and (iii) recommends the best EIO industry sector to use with a justification with an LLM (Claude 3 Sonnet).


## Prerequisities
You will need [python3](https://www.python.org/downloads/) with access to the venv package and [Docker](https://docs.docker.com/desktop/) on your local machine to build and deploy this project.

Install the [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) and [bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_bootstrap) your AWS account using the CDK:

`cdk bootstrap aws://ACCOUNT-NUMBER/REGION`

### Data
The sample use the [City of Austin - Purchase Order Quantity Price Detail for Commodity/Goods procurements](https://catalog.data.gov/dataset/purchase-order-quantity-price-detail-for-commodity-goods-procurements) for demonstration purposes. The data has been formatted for ease of processing.

To use your data with this sample code, format it as a CSV with the following headers in the first row:

COMMODITY, COMMODITY_DESCRIPTION, EXTENDED_DESCRIPTION, CONTRACT_NAME
where

COMMODITY is a numeric identifier
COMMODITY_DESCRIPTION is a string enclosed with double quotes
EXTENDED_DESCRIPTION is a string enclosed with double quotes
CONTRACT_NAME is a string enclosed with double quotes

Upload your data in the `input/` prefix of the S3 bucket created by the CDK stack.

## Architecture

The following diagram depicts the architecture of the CDK stack deployed by this project:

![CDK architecture](/docs/sample-code-architecture-diagram.png)

## Deployment
You must explicitly enable access to models before they can be used with the Amazon Bedrock service. Please follow these steps in the [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) to enable access to the models in the region you are deploying the solution:
- Anthropic Claude 3 Sonnet `anthropic.claude-3-sonnet-20240229-v1:0`
- Cohere Embed English v3 `cohere.embed-english-v3`


Note that proceeding with these steps will provision AWS resources in your account.
- `git clone git@github.com:aws-solutions-library-samples/guidance-for-environmental-impact-factor-mapping-on-aws.git`
- `cd guidance-for-environmental-impact-factor-mapping-on-aws`
- Follow the steps in [README-CDK](/README-CDK.md) to set up a virtual environment for this project.
- Run `cdk deploy` (this may take ~5 minutes to complete)
- Run `aws bedrock-agent start-ingestion-job --data-source-id XXXXXXXXXX --knowledge-base-id XXXXXXXXXX` replacing data-source-id and knowledge-base-id with the values from the CDK deploy step (this may take ~10 min to complete, you can monitor the sync progress on the AWS Bedrock console)
- Run `aws stepfunctions start-execution --state-machine-arn XXXXXXXXXX` replacing state-machine-arn with the value from the CDK deploy step(this may take a long time depending on the size of your dataset, ~2 hours for the included dataset of ~5800 activities, you can monitor the execution progress from the AWS Step Functions console)
- The state machine will write a csv file to the Amazon S3 bucket created during the CDK deployment under the key `outputs/output.csv`

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## Cleanup

Note that tearing down the stack will destroy ALL contents of the S3 bucket!

To remove the sample stack from your AWS account, you can run the `cdk destroy` command from the root directory, or terminate the stack in the AWS management console from Amazon CloudFormation.

## Next Steps and Additional Resources
* Read the research paper that this sample code is based on [CaML: Carbon Footprinting of Household Products with Zero-Shot Semantic Text Similarity](https://www.amazon.science/publications/caml-carbon-footprinting-of-household-products-with-zero-shot-semantic-text-similarity)
* Review the latest datasets from the following pages:
    * [US Census Bureau North American Industry Classification System Reference Files](https://www.census.gov/naics/?48967) - click on **Downloadable Files** at the bottom of the page. This sample code uses the [**2022 NAICS Index File**](https://www.census.gov/naics/2022NAICS/2022_NAICS_Index_File.xlsx).
    * [US EPA](https://cfpub.epa.gov/si/si_public_record_Report.cfm?dirEntryId=349324&Lab=CESER) - This sample code uses the [**Supply Chain Factors Dataset v1.3**](https://pasteur.epa.gov/uploads/10.23719/1531143/SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv).

## Disclaimer
Sample code, software libraries, command line tools, proofs of concept, templates, or other related technology are provided as AWS Content or Third-Party Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content or Third-Party Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content or Third-Party Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content or Third-Party Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

## License

This library is licensed under the Apache-2.0 License. See the LICENSE file.