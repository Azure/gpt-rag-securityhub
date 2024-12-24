
import os
import safety_checks.safety_checks as safety_checks
import logging
import asyncio
from shared.util import get_secret,create_kernel
from azure.core.credentials import AzureKeyCredential
from azure.ai.contentsafety.aio import ContentSafetyClient
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.functions import KernelPlugin
from plugins.ResponsibleAI.wrapper import fairness

CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")
APIM_ENABLED=os.environ.get("APIM_ENABLED", "false").lower() == "true"
AZURE_DB_URI=os.environ.get("AZURE_DB_URI")
AZURE_DB_NAME=os.environ.get("AZURE_DB_NAME")
AZURE_DB_ID=os.environ.get("AZURE_DB_ID")
AZURE_DB_URI = f"https://{AZURE_DB_ID}.documents.azure.com:443/"
PLUGINS_FOLDER = f"plugins"
RESPONSABLE_AI_CHECK=os.environ.get("RESPONSABLE_AI_CHECK", "false").lower() == "true"
async def question_checks(question):
    if APIM_ENABLED:
        content_safety_key=await get_secret("apimSubscriptionKey")
        key=AzureKeyCredential(content_safety_key)
        endpoint=os.environ.get("APIM_ENDPOINT")
    else:
        endpoint=CONTENT_SAFETY_ENDPOINT
    async with DefaultAzureCredential() as credential:
        if(APIM_ENABLED):
            content_safety_credential=key
        else:
            content_safety_credential=credential
        async with ContentSafetyClient(endpoint=endpoint, credential=content_safety_credential) as client:
            checks = [
                safety_checks.prompt_shield_wrapper(question=question,client=client),
                safety_checks.jailbreak_detection_wrapper(question,client),
                safety_checks.analyze_text_wrapper(question,client)
            ]
            check_names = ["promptShield(Question)", "jailbreak","TextAnalysis"]
            check_results = {}
            details = {}
            logging.info("Starting content safety checks")
            results = await asyncio.gather(*checks, return_exceptions=True)
            for index, result in enumerate(results):
                check_name = check_names[index]
                if isinstance(result, Exception):
                    # Handle the exception
                    logging.error(f"Error occurred during {check_name} content safety check: {result}")
                    check_results[check_name] = "Failed"
                    check_details = f"Error: Failed check with exception {result}"
                else:
                    # Assuming result is now a tuple (check_result, check_details)
                    check_result, check_details = result
                    logging.info(f"Checking {check_name}, result: {check_result}, details: {check_details}")
                    # If the check_result indicates a failure, record the failure
                    if check_result:
                        check_results[check_name] = "Failed"
                        details[check_name] = check_details  # Correctly update details with check_details
                    else:
                        check_results[check_name] = "Passed"
                        details[check_name] = check_details  # Correctly update details even if check passed
    return check_results, details

async def answer_checks(answer,question,sources):
    if APIM_ENABLED:
        content_safety_key=await get_secret("apimSubscriptionKey")
        key=AzureKeyCredential(content_safety_key)
        endpoint=os.environ.get("APIM_ENDPOINT")
    else:
        endpoint=CONTENT_SAFETY_ENDPOINT
    async with DefaultAzureCredential() as credential:
        if(APIM_ENABLED):
            content_safety_credential=key
        else:
            content_safety_credential=credential
        async with ContentSafetyClient(endpoint=endpoint, credential=content_safety_credential) as client:
            checks = [
                safety_checks.groundedness_check_wrapper(question, answer, sources,client),
                safety_checks.protected_material_detection_wrapper(answer,client),
                safety_checks.analyze_text_wrapper(answer,client),
                safety_checks.prompt_shield_wrapper(sources=sources,client=client)
            ]
            check_names = ["groundedness","protectedMaterial","TextAnalysis","promptShield(sources)"]
            if(RESPONSABLE_AI_CHECK==True):
                kernel=await create_kernel()
                raiPlugin = kernel.add_plugin(KernelPlugin.from_directory(parent_directory=f"{PLUGINS_FOLDER}/ResponsibleAI",plugin_name="Semantic"))
                arguments=KernelArguments(answer=answer)
                checks.append(fairness(kernel, raiPlugin, arguments))
                check_names.append("fairness")
            check_results = {}
            details = {}
            logging.info("Starting content safety checks")
            results = await asyncio.gather(*checks, return_exceptions=True)
            for index, result in enumerate(results):
                check_name = check_names[index]
                if isinstance(result, Exception):
                    # Handle the exception
                    logging.error(f"Error occurred during {check_name} content safety check: {result}")
                    check_results[check_name] = "Failed"
                    check_details = f"Error: Failed check with exception {result}"
                else:
                    # Assuming result is now a tuple (check_result, check_details)
                    check_result, check_details = result
                    # If the check_result indicates a failure, record the failure
                    if check_result:
                        check_results[check_name] = "Failed"
                        details[check_name] = check_details  # Correctly update details with check_details
                    else:
                        check_results[check_name] = "Passed"
                        details[check_name] = check_details  # Correctly update details even if check passed
    return check_results, details