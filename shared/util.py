import os
import time
import logging
from azure.keyvault.secrets.aio import SecretClient as AsyncSecretClient
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
import semantic_kernel as sk
from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from tenacity import retry, wait_random_exponential, stop_after_attempt



AZURE_OPENAI_TEMPERATURE = os.environ.get("AZURE_OPENAI_TEMPERATURE") or "0.17"
AZURE_OPENAI_TOP_P = os.environ.get("AZURE_OPENAI_TOP_P") or "0.27"
AZURE_OPENAI_RESP_MAX_TOKENS = os.environ.get("AZURE_OPENAI_MAX_TOKENS") or "1000"
AZURE_OPENAI_LOAD_BALANCING = os.environ.get("AZURE_OPENAI_LOAD_BALANCING") or "false"
AZURE_OPENAI_LOAD_BALANCING = True if AZURE_OPENAI_LOAD_BALANCING.lower() == "true" else False
AZURE_OPENAI_CHATGPT_MODEL = os.environ.get("AZURE_OPENAI_CHATGPT_MODEL")
AZURE_OPENAI_EMBEDDING_MODEL = os.environ.get("AZURE_OPENAI_EMBEDDING_MODEL")
AZURE_DB_ID = os.environ.get("AZURE_DB_ID")
AZURE_DB_NAME = os.environ.get("AZURE_DB_NAME")
AZURE_DB_URI = f"https://{AZURE_DB_ID}.documents.azure.com:443/"
APIM_ENABLED = os.environ.get("APIM_ENABLED") or "false"
APIM_ENABLED = True if APIM_ENABLED.lower() == "true" else False
##########################################################
# KEY VAULT 
##########################################################

async def get_secret(secretName):
    keyVaultName = os.environ["AZURE_KEY_VAULT_NAME"]
    KVUri = f"https://{keyVaultName}.vault.azure.net"
    async with AsyncDefaultAzureCredential() as credential:
        async with AsyncSecretClient(vault_url=KVUri, credential=credential) as client:
            retrieved_secret = await client.get_secret(secretName)
            value = retrieved_secret.value

    # Consider logging the elapsed_time or including it in the return value if needed
    return value

def divide_string(s, min_chars=0, max_chars=1000):
    result = []
    current_pos = 0

    while current_pos < len(s):
        # Determine the end position, prioritizing the max_chars limit
        end_pos = min(len(s), current_pos + max_chars)
        
        # Adjust end_pos to avoid breaking words, if possible
        if end_pos < len(s) and s[end_pos] not in [' ', '\n', '\t']:
            while end_pos > current_pos and s[end_pos - 1] not in [' ', '\n', '\t']:
                end_pos -= 1
        
        # If we cannot find a space, revert to the max_chars limit
        if end_pos == current_pos:
            end_pos = min(len(s), current_pos + max_chars)
        
        # Extract and add the substring
        result.append(s[current_pos:end_pos])
        
        # Update current_pos
        current_pos = end_pos

    # Handle case where the last substring is shorter than min_chars
    if len(result) > 1 and len(result[-1]) < min_chars:
        combined = result[-2] + result[-1]
        result.pop()  # Remove last element
        result[-1] = combined  # Update second-to-last element with combined string
        
        # Now divide the combined string into two as equal parts as possible
        half = len(combined) // 2
        # Find nearest space to half to avoid breaking words
        split_point = half
        while split_point < len(combined) and combined[split_point] not in [' ', '\n', '\t']:
            split_point += 1
        if split_point == len(combined):  # If no space found, try to find space backwards
            split_point = half
            while split_point > 0 and combined[split_point] not in [' ', '\n', '\t']:
                split_point -= 1
        
        # If still no space found, split at half
        if split_point in [0, len(combined)]:
            split_point = half
        
        # Replace the combined string with two new substrings
        result[-1] = combined[:split_point]
        result.append(combined[split_point:])

    return result

async def create_kernel(service_id='aoai_chat_completion',apim_key=None):
    kernel = sk.Kernel()
    chatgpt_config =await get_aoai_config(AZURE_OPENAI_CHATGPT_MODEL)
    if APIM_ENABLED:
        kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
                deployment_name=chatgpt_config['deployment'],
                endpoint=chatgpt_config['endpoint'],
                api_version=chatgpt_config['api_version'],
                api_key=apim_key
            )
        )
    else:
        kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
                deployment_name=chatgpt_config['deployment'],
                endpoint=chatgpt_config['endpoint'],
                api_version=chatgpt_config['api_version'],
                ad_token=chatgpt_config['api_key']
            )
        )
    return kernel

async def get_aoai_config(model):
    if APIM_ENABLED:
        if model in ('gpt-35-turbo', 'gpt-35-turbo-16k', 'gpt-4', 'gpt-4-32k','gpt-4o'):
            deployment = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "gpt-4o"
        elif model == AZURE_OPENAI_EMBEDDING_MODEL:
            deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        else:
            raise Exception(f"Model {model} not supported. Check if you have the correct env variables set.")
        result = {
            "endpoint": os.environ.get("APIM_AZURE_OPENAI_ENDPOINT"),
            "deployment": deployment,
            "model": model,  # ex: 'gpt-35-turbo-16k', 'gpt-4', 'gpt-4-32k', 'gpt-4o'
            "api_version": os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-03-01-preview",
        }
    else:
        resource = await get_next_resource(model)
        async with AsyncDefaultAzureCredential() as credential:
            token = await credential.get_token("https://cognitiveservices.azure.com/.default")

            if model in ('gpt-35-turbo', 'gpt-35-turbo-16k', 'gpt-4', 'gpt-4-32k','gpt-4o'):
                deployment = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "gpt-4o"
            elif model == AZURE_OPENAI_EMBEDDING_MODEL:
                deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            else:
                raise Exception(f"Model {model} not supported. Check if you have the correct env variables set.")
            result = {
                "resource": resource,
                "endpoint": f"https://{resource}.openai.azure.com",
                "deployment": deployment,
                "model": model,  # ex: 'gpt-35-turbo-16k', 'gpt-4', 'gpt-4-32k', 'gpt-4o'
                "api_version": os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-03-01-preview",
                "api_key": token.token
            }

    return result

async def get_next_resource(model):
    # define resource
    resources = os.environ.get("AZURE_OPENAI_RESOURCE")
    resources = get_list_from_string(resources)

    if not AZURE_OPENAI_LOAD_BALANCING or model == AZURE_OPENAI_EMBEDDING_MODEL:
        return resources[0]
    else:
        start_time = time.time()
        async with AsyncDefaultAzureCredential() as credential:
            async with AsyncCosmosClient(AZURE_DB_URI, credential) as db_client:
                db = db_client.get_database_client(database=AZURE_DB_NAME)
                container = db.get_container_client('models')
                try:
                    keyvalue = await container.read_item(item=model, partition_key=model)
                    # check if there's an update in the resource list and update cache
                    if set(keyvalue["resources"]) != set(resources):
                        keyvalue["resources"] = resources
                except Exception:
                    logging.info(f"[util__module] get_next_resource: first time execution (keyvalue store with '{model}' id does not exist, creating a new one).")
                    keyvalue = {
                        "id": model,
                        "resources": resources
                    }
                    keyvalue = await container.create_item(body=keyvalue)
                resources = keyvalue["resources"]

                # get the first resource and move it to the end of the list
                resource = resources.pop(0)
                resources.append(resource)

                # update cache
                keyvalue["resources"] = resources
                await container.replace_item(item=model, body=keyvalue)

        response_time = round(time.time() - start_time, 2)
        logging.info(f"[util__module] get_next_resource: model '{model}' resource {resource}. {response_time} seconds")
        return resource
    
@retry(wait=wait_random_exponential(min=20, max=60), stop=stop_after_attempt(6), reraise=True)
async def call_semantic_function(kernel, function, arguments):
    function_result = await kernel.invoke(function, arguments)
    return function_result

def get_list_from_string(string):
    result = string.split(',')
    result = [item.strip() for item in result]
    return result
