import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame

# Define the input and output paths
args = getResolvedOptions(sys.argv, ['EIF_bucket'])

# Create a Spark context and Glue context
sc = SparkContext()
glueContext = GlueContext(sc)

# Create dynamic frame from the JSON output of the mapping runs
mapped_activities = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": ["s3://" + args['EIF_bucket'] + "/successful-mappings/"]},
    format="json",
    format_options={
        "jsonPath": "$"
    }
)
mapped_activities = mapped_activities.unbox("Output", "json") # convert string value to json
mapped_activities = mapped_activities.unnest() # flatten json
mapped_activities = mapped_activities.apply_mapping( # rename and drop columns
    mappings=[
        ("`Output.ExtendedDescription`", "ExtendedDescription", "string"),
        ("`Output.MappedNAICSTitle`", "MappedNAICSTitle", "string"),
        ("`Output.MappedNAICSCode`", "MappedNAICSCode", "string"),
        ("`Output.CommodityDescription`", "CommodityDescription", "string"),
        ("`Output.Commodity`", "Commodity", "string"),
        ("`Output.MappingJustification`", "MappingJustification", "string"),
        ("`Output.SimplifiedDescription`", "SimplifiedDescription", "string"),
        ("`Output.ContractName`", "ContractName", "string"),
        ("`Output.PossibleMatches.NAICSCode1`", "PossibleNAICSCode1", "string"),
        ("`Output.PossibleMatches.NAICSCode2`", "PossibleNAICSCode2", "string"),
        ("`Output.PossibleMatches.NAICSCode3`", "PossibleNAICSCode3", "string")
    ]
)

# Create dynamic frame from emissions factor data
emissions_factors = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": ["s3://" + args['EIF_bucket'] + "/datasets/SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv"]},
    format="csv",
    format_options={
        "withHeader": True,
        "separator": ",",
        "quoteChar": '"'
    }
)
emissions_factors = emissions_factors.apply_mapping( # rename and drop columns
    mappings=[
        ("2017 NAICS Code", "2017NAICSCode", "string"),
        ("Supply Chain Emission Factors with Margins", "CO2e", "string"),
        ("Reference USEEIO Code", "USEEIOCode", "string")
    ]
)

# Merge frames to create final outputs
# Inner join to get all activities with valid NAICS codes
mapped_factors = mapped_activities.join(paths1=["MappedNAICSCode"], paths2=["2017NAICSCode"], frame2=emissions_factors).drop_fields(["2017NAICSCode"])

# Write output as CSV and rename to be human readable
# For large datasets, use Athena and Quicksight for interacting with results instead
mapped_factors = mapped_factors.coalesce(1)
glueContext.write_dynamic_frame.from_options(
    frame=mapped_factors,
    connection_type="s3",
    connection_options={"path": "s3://" + args['EIF_bucket'] + "/output"},
    format="csv",
    format_options={
        "writeHeader": True,
        "separator": ",",
        "quoteChar": '"'
    }
)
s3 = boto3.client('s3')
objects = s3.list_objects_v2(Bucket=args['EIF_bucket'], Prefix="output/")
for obj in objects['Contents']:
    if obj['Key'].startswith('output/run-'):
        s3.copy_object(
            CopySource={'Bucket': args['EIF_bucket'], 'Key': obj['Key']},
            Bucket=args['EIF_bucket'],
            Key='output/matched_factors.csv'
        )
        s3.delete_object(Bucket=args['EIF_bucket'], Key=obj['Key'])

# Left anti join to get activities without a valid NAICS code. This catches any activities that may be matched to nonexistant codes. 
ma_df = mapped_activities.toDF()
ef_df = emissions_factors.toDF()
no_match_factors = DynamicFrame.fromDF(ma_df.join(ef_df, (ma_df['MappedNAICSCode']==ef_df['2017NAICSCode']), "left_anti"), glueContext, "no_match_activities")
if no_match_factors.count() > 0:
    no_match_factors = no_match_factors.coalesce(1)
    glueContext.write_dynamic_frame.from_options(
        frame=no_match_factors,
        connection_type="s3",
        connection_options={"path": "s3://" + args['EIF_bucket'] + "/output"},
        format="csv",
        format_options={
            "writeHeader": True,
            "separator": ",",
            "quoteChar": '"'
        }
    )
    s3 = boto3.client('s3')
    objects = s3.list_objects_v2(Bucket=args['EIF_bucket'], Prefix="output/")
    for obj in objects['Contents']:
        if obj['Key'].startswith('output/run-'):
            s3.copy_object(
                CopySource={'Bucket': args['EIF_bucket'], 'Key': obj['Key']},
                Bucket=args['EIF_bucket'],
                Key='output/mismatched_factors.csv'
            )
            s3.delete_object(Bucket=args['EIF_bucket'], Key=obj['Key'])