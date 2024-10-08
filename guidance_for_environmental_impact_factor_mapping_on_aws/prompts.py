# Prompt to clean activity names and descriptions into a simple activity description to be matched in the next step.
clean_text_prompt = """I want to do of LCA of business activities based on Environmentally Extended Input Output (EEIO) 
Environmental Impact Factors (EIF). I am interested in the environmental impact associated with the materials 
and manufacturing phase of the activity. I am given business activity descriptions, and I want to 
paraphrase it to a plain language description before I select an EIF. 

Below is an example, inside <example></example> XML tags, of a given activity, and its plain language descriptions. Note that the descriptions 
are brief, and do not make any assumptions about the activity.

<example>
COMMODITY                                                      20142770002
COMMODITY_DESCRIPTION      GLOVES WORK MECHANIC SYNTHETIC LEATHER SZ LARGE
EXTENDED_DESCRIPTION     RC LN_____ QTY DEL_____ P/F_____ B/O______ DEL...
CONTRACT_NAME                            MSC items for Glen Bell warehouse

The item is a synthetic leather large work gloves 
</example>

Following the example, provide a plain language description of the activity data given below:
COMMODITY              {}
COMMODITY_DESCRIPTION  {}
EXTENDED_DESCRIPTION   {}
CONTRACT_NAME          {}

Make the most of the given information. DO NOT say that information is limited.
DO NOT refrain from providing a description, or ask for more information.
If you cannot provide a plain language description, simply summarize the 
information provided. You MUST provide a description. 

Avoid filler words such as "Based on the details" or "happy to assist", 
keep your response to the point.
Do not repeat the given instructions or information. 
DO NOT say you have insufficient information for an LCA.

Only provide the description and nothing else."""

# Prompt to generate possible emission factor matches from the NAICS index
possible_eio_matches_system_prompt = """You are a Lifecycle Analysis expert matching business activities to their North American Industry Classification System (NAICS) titles.

I want to do of LCA of business activities based on Environmentally Extended Input Output (EEIO) Environmental Impact Factors (EIF). I am interested in the environmental impact associated with the materials and manufacturing phase of the activity. I am given a business activity and I want to match it to its the North American Industry Classification System code and title.

Format the output in JSON with the keys "NAICSCode1", "NAICSTitle1", "NAICSCode2", "NAICSTitle2", "NAICSCode3", "NAICSTitle3".

Below is an example, inside <example></example> XML tags, of a given activity and three possible NAICS codes and titles.

<example>
The item is a synthetic leather large work gloves.

{
	"NAICSCode1": "315990",
	"NAICSTitle1": "Apparel Accessories and Other Apparel Manufacturing",
	"NAICSCode2": "339920",
	"NAICSTitle2": "Sporting and Athletic Goods Manufacturing",
	"NAICSCode3": "316998",
	"NAICSTitle3": "All Other Leather Good and Allied Product Manufacturing"
}
</example>

What are three possible NAICS titles for the given activity:
$query$

$search_results$

Make the most of the given information. DO NOT say that information is limited or ask for more information.
YOU MUST provide three NAICS titles.
Avoid filler words such as "Based on the details" or "happy to assist", keep your response to the point.
Do not repeat the given instructions or information. 
DO NOT say you have insufficient information for an LCA.

Respond with the JSON output and nothing else.
"""

# Prompt to choose the best emission factor from the options
best_eif_prompt = """You are a Lifecycle Analysis expert matching business activities to their North American Industry Classification System (NAICS) titles.

I want to do of LCA of business activities based on Environmentally Extended Input Output (EEIO) Environmental Impact Factors (EIF). I am interested in the environmental impact associated with the materials and manufacturing phase of the activity. I am given a business activity and three possible corresponding NAICS codes and titles. 

I want to pick the NAICS code and title that best match the given activity. Include justification for your choice.
Format the output in JSON with the keys "BestNAICSCode", "BestNAICSTitle", "Justification".

Activity:
{}

Possible NAICS codes and titles:
{} - {}
{} - {}
{} - {}

Which of these impact factors is the best match for the provided activity? 

Note that impact factor names with 'market' in them are better match than those with 'production' in them.
Make the most of the given information. DO NOT say that information is limited or ask for more information.
YOU MUST choose a best code and title. YOU MUST include a justification for your choice.
Avoid filler words such as "Based on the details" or "happy to assist", keep your response to the point.
Do not repeat the given instructions or information. 
DO NOT say you have insufficient information for an LCA.

Respond with the JSON output and nothing else.
"""

best_eif_prompt_w_example = """You are a Lifecycle Analysis expert matching business activities to their North American Industry Classification System (NAICS) titles.

I want to do of LCA of business activities based on Environmentally Extended Input Output (EEIO) Environmental Impact Factors (EIF). I am interested in the environmental impact associated with the materials and manufacturing phase of the activity. I am given a business activity and three possible corresponding NAICS codes and titles. 

I want to pick the NAICS code and title that best match the given activity. Include justification for your choice.
Format the output in JSON with the keys "BestNAICSCode", "BestNAICSTitle", "Justification".

<example>
Activity:
The item is a synthetic leather large work gloves.

Possible NAICS codes and titles:
315990 - Apparel Accessories and Other Apparel Manufacturing
339920 - Sporting and Athletic Goods Manufacturing
316998 - All Other Leather Good and Allied Product Manufacturing

{
    "BestNAICSCode": "316998",
    "BestNAICSTitle": "All Other Leather Good and Allied Product Manufacturing",
    "Justification": "The most appropriate NAICS title is Apparel Accessories and Other Apparel Manufacturing. This covers work gloves made of leather or other materials, which matches the description of synthetic leather work gloves."
}
</example>

Activity:
{}

Possible NAICS codes and titles:
{} - {}
{} - {}
{} - {}

Which of these impact factors is the best match for the provided activity? 

Note that impact factor names with 'market' in them are better match than those with 'production' in them.
Make the most of the given information. DO NOT say that information is limited or ask for more information.
YOU MUST choose a best code and title. YOU MUST include a justification for your choice.
Avoid filler words such as "Based on the details" or "happy to assist", keep your response to the point.
Do not repeat the given instructions or information. 
DO NOT say you have insufficient information for an LCA.

Respond with the JSON output and nothing else.
"""