# Enterprise RAG Security Hub

This Security Hub is part of the **Enterprise RAG (GPT-RAG)** Solution Accelerator.

To learn more about the Enterprise RAG, please go to [https://aka.ms/gpt-rag](https://aka.ms/gpt-rag).

## Overview
The Security Hub Function integrates with Azure Content Safety and centralizes GPT Responsible AI checks. This function ensures that AI-generated content adheres to safety and ethical standards.

## Features

### Groundedness Detection 
The Groundedness Detection evaluates whether the text responses of large language models (LLMs) are grounded in the source materials provided by users. Ungroundedness refers to instances where LLMs produce information that is non-factual or inaccurate compared to the source materials.

### Prompt Shields
Generative AI models can be exploited by malicious actors. To mitigate these risks, safety mechanisms are integrated to restrict the behavior of LLMs within a safe operational scope. Despite these safeguards, LLMs can still be vulnerable to adversarial inputs that bypass the integrated safety protocols. Prompt Shields analyzes LLM inputs and detects User Prompt Attacks

### Protected Material Detection
The Protected Material Text check flags known text content (e.g., song lyrics, articles, recipes, and selected web content) that might be output by large language models.

### Harm Categories
Content Safety recognizes four distinct categories of objectionable content:

#### Hate and Fairness
Hate and fairness-related harms refer to any content that attacks or uses pejorative or discriminatory language with reference to a person or identity group based on certain differentiating attributes, including but not limited to race, ethnicity, nationality, gender identity and expression, sexual orientation, religion, immigration status, ability status, personal appearance, and body size.

Fairness is concerned with ensuring that AI systems treat all groups of people equitably without contributing to existing societal inequities. Similar to hate speech, fairness-related harms hinge upon disparate treatment of identity groups.

#### Sexual
Sexual content describes language related to anatomical organs and genitals, romantic relationships, acts portrayed in erotic or affectionate terms, pregnancy, physical sexual acts (including those portrayed as assault or forced sexual violent acts against one's will), prostitution, pornography, and abuse.

#### Violence
Violence describes language related to physical actions intended to hurt, injure, damage, or kill someone or something. It also includes descriptions of weapons, guns, and related entities, such as manufacturers, associations, and legislation.

#### Self-Harm
Self-harm describes language related to physical actions intended to purposely hurt, injure, or damage one's body or kill oneself.

### Block lists
Create lists of words that should never be used and filter queries and answers that include them.

### Responsible AI
Conduct comprehensive evaluations to ensure that the AI system adheres to responsible AI principles. These principles are designed to guide the development and deployment of AI technologies in a manner that is ethical, transparent, and fair.

#### Fairness
This check is dedicated to ensuring that the AI system treats all groups of people equitably. It aims to prevent the AI from contributing to or exacerbating existing societal inequities. The fairness check evaluates the AI's decision-making processes to ensure that they do not favor or discriminate against any particular group based on attributes such as race, gender, age, or socioeconomic status.

### Auditing
This feature provides an endpoint that logs all interactions with the orchestrator. The purpose of this auditing capability is to maintain a detailed record of all activities and decisions made by the AI system. These logs are crucial for transparency and accountability, allowing for thorough reviews and analyses of the AI's behavior and ensuring compliance with ethical standards and regulatory requirements.

## Security hub implementation
- Deploy the [security hub function](https://github.com/Azure/gpt-rag-securityhub)
- Create a content safety resource
- Give the security hub function the roles of "Cognitive Services Users" and "Reader" in the content safety resource. 
- Add enviroment variables to security hub:
    "CONTENT_SAFETY_ENDPOINT": "https://{your-content-safety-resource}.cognitiveservices.azure.com/",
    "AZURE_KEY_VAULT_NAME": "[YOUR_KEY_VAULT_NAME]"
- Add enviroment variables to orchestrator:
    "SECURITY_HUB_ENDPOINT": "https://{your-securityHub-function-url}/api",
    "SECURITY_HUB_CHECK": "true",

- OPTIONAL: 
- To use the auditing feature give the function permission to access the cosmos db and add these env variables to the security hub function:
    "AZURE_DB_ID": "[YOUR_DB_ID]",
    "AZURE_DB_NAME": "[YOUR_DB_NAME]",
    "AZURE_DB_CONTAINER_NAME": "[YOUR_AUDITING_CONTAINER_NAME]",

### Granting Cosmos DB Access

To grant access to the Cosmos DB for auditing purposes, run the following PowerShell command. Replace the placeholder values with your actual details:

```powershell
New-AzCosmosDBSqlRoleAssignment `
  -AccountName <Your-CosmosDB-AccountName> `
  -ResourceGroupName <Your-ResourceGroupName> `
  -RoleDefinitionId <Your-RoleDefinitionId> `
  -Scope "/" `
  -PrincipalId <Your-PrincipalId>
```

For example:

```powershell
New-AzCosmosDBSqlRoleAssignment `
  -AccountName dbgpt0-ifqbichztvg3i `
  -ResourceGroupName MyResourceGroup `
  -RoleDefinitionId "00000000-0000-0000-0000-000000000000" `
  -Scope "/" `
  -PrincipalId "11111111-1111-1111-1111-111111111111"



- To customize threshholds of harm and groundedness checks, add these env variables to orchestrator with your prefered values:
    "SECURITY_HUB_HATE_THRESHHOLD": "0",
    "SECURITY_HUB_SELFHARM_THRESHHOLD": "0",
    "SECURITY_HUB_SEXUAL_THRESHHOLD": ""0,
    "SECURITY_HUB_VIOLENCE_THRESHHOLD": "0",
    "SECURITY_HUB_UNGROUNDED_PERCENTAGE_THRESHHOLD":"0.0

    Harm categories must be an int value beetween 0 and 4
    Ungroundedness percentage must be a float value beetween 0 and 1

- If responsible AI checks are to be conducted, the following environment variables must be set with correct values, and the Cognitive Services OpenAI User role for the security hub function is needed in the AOAI service:
        "RESPONSIBLE_AI_CHECK": "True",
        "AZURE_OPENAI_RESOURCE": "",
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT": "",
        "AZURE_OPENAI_CHATGPT_MODEL": ""

- If the content safety service is consumed via APIM, you need to have a Key Vault with a secret that contains the APIM key named "apimSubscriptionKey" and set these environment variables:
        "APIM_ENABLED": "true",
        "AZURE_KEY_VAULT_NAME": "",
        "APIM_ENDPOINT": ""

    Additionally, roles are needed to read the secret from the Key Vault.

- You can also add this optional variables if you want to add your blocklists(you should first [create and fill the blocklist](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/how-to/use-blocklist?tabs=windows%2Crest#create-or-modify-a-blocklist)):
        "BLOCK_LIST_CHECK": "true",
        "BLOCK_LISTS_NAMES": [names]

### Running Locally with VS Code  
   
[How can I test the solution locally in VS Code?](docs/LOCAL_DEPLOYMENT.md)

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
