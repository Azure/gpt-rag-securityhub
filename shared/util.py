import os
from azure.keyvault.secrets.aio import SecretClient as AsyncSecretClient
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

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