## Introduction

This code is intended to quickly demonstrate the use of [CaML: Carbon Footprinting of Household Products with Zero-Shot Semantic Text Similarity](https://www.amazon.science/publications/caml-carbon-footprinting-of-household-products-with-zero-shot-semantic-text-similarity) in an AWS environment. It has a modified architecture from what is published in the diagram of the Guidance for Enviornmental Impact Factor Mapping on AWS. It uses an Amazon Sagemaker Notebook Instance to allow the user to quickly modify and interact with the CaML code as it runs.

Note that deploying this CDK application will create resources in your AWS account that include the following:
- An Amazon SageMaker notebook instance
- An Amazon S3 bucket
- Amazon IAM roles, policies, and permissions
- AWS Systems Manager Parameter Store parameters
- An AWS CodeCommit repository
- An Amazon Virtual Private Cloud (Amazon VPC) and associated resources

## Task: Product carbon footprinting with EIO-LCA (excerpt from CaML)

Economic input-output life cycle assessment (EIO-LCA) is a method to estimate the carbon footprint of a product or activity based on its sale value. There are databases such as [USEEIO](https://www.epa.gov/land-research/us-environmentally-extended-input-output-useeio-technical-content) which publish the carbon emissions associated with industry sectors in the economy on a per unit currency basis. EIO-LCA estimates are compatible with [Greenhouse Gas Protocol](https://ghgprotocol.org/), and can be used for external reporting of scope 3 impacts. Given that the carbon emission estimate is only based on sale value of a product, it is an approximation and roughly within 2X the value of true emissions as per a [recent study](https://onlinelibrary.wiley.com/doi/pdf/10.1111/jiec.13271). 

We automate the process of mapping products to their EIO industry sectors based on text descriptions. This is one of the key steps in life cycle assessment that is done manually in practice. Our solution alleviates this manual overhead, and scales to any type of product. In a nutshell, we use a natural language model to match industry sectors based on semantic text similarity. The model is pre-trained on web data, and we use it as-is without additional training on products or industry sectors.


## Prerequisities
You will need [python3](https://www.python.org/downloads/) with access to the venv package on your local machine to build and deploy this project.

Follow the steps in [README-CDK](/README-CDK.md) to set up a virtual environment for this project.

You will then need to [bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_bootstrap) your AWS account using the CDK:

`cdk bootstrap aws://ACCOUNT-NUMBER/REGION`

## Architecture

The following diagram depicts the architecture of the CDK stack deployed by this project:

![CDK architecture](/assets/sample-code-architecture-diagram.png)

## Deployment

Note that proceeding with these steps will provision AWS resources in your account.
- Run `cdk deploy` (this may take around 10 minutes)
- Open the AWS console and navigate to Amazon Sagemaker
- Click on **Notebook instances** under **Notebook** on the left
- Click **Open Jupyter** for the newly created instance
- Click the folder `EifmNotebookRepo`
- In the top right select **Terminal** from the **New** dropdown
- Run the following commands within the new terminal (these steps will take several minutes):
    - `cd SageMaker/EifmNotebookRepo`
    - `bash ./setup_env.sh`
    - After the commands complete, close the browser tab
- Navigate to the browser tab with Jupyter open
- Refresh the browser tab. This is needed to allow the newly created environment to appear.
- Open `walkthrough.ipynb`
- You should see **conda_demo_environment** selected in the upper right corner
- You may now run the code in the notebook by clicking **Run All** under the **Cell** menu

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## Cleanup

Note that tearing down the stack will destroy ALL contents of the S3 bucket!

To remove the sample stack from your AWS account, you can run the `cdk destroy` command from the root directory, or terminate the stack in the AWS management console from Amazon CloudFormation.

## Disclaimer
- While this guidance serves as a starting place to help streamline EIF mapping for Life Cycle Assessment (LCA) experts, the results should be vetted by LCA experts prior to considering specific actions and supplemented with appropriate information for greater accuracy. This guidance uses the [v1.2 USEEIO database](https://edg.epa.gov/metadata/catalog/search/resource/details.page?uuid=https://doi.org/10.23719/1528686) and [US Census Bureau North American Industry Classification System 2017 Reference Files](https://www.census.gov/naics/?48967) as a sample for demonstration purposes only. It is recommended that the users apply the most recent version of the database.
- The model was tested on products in the US retail sector and does not cover services. The user assumes responsibility to ensure accuracy of the emission factor mapping and validate the results. The use of this guidance does not guarantee verified greenhouse gas (GHG) disclosures. AWS does not assume any legal liability or responsibility for any errors or omissions, or for the results obtained from the use of this guidance.
- The sample code is a prescriptive starting point, but it only represents a slice of what a complete application might look like.. The sample code is provided on an “as is” basis with no guarantees of accuracy, completeness, adequacy, validity or availability and without any warranties of any kind whatsoever, expressed or implied.
- Sample code, software libraries, command line tools, proofs of concept, templates, or other related technology are provided as AWS Content or Third-Party Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content or Third-Party Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content or Third-Party Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content or Third-Party Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

## License

This library is licensed under the Apache-2.0 License. See the LICENSE file.