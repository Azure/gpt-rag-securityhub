import azure.functions as func
import os
import safety_checks.safety_checks as safety_checks
import logging
import asyncio
import json
from shared.util import get_secret
from azure.core.credentials import AzureKeyCredential
from azure.ai.contentsafety.aio import ContentSafetyClient
from azure.identity.aio import DefaultAzureCredential


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")
APIM_ENABLED=os.environ.get("APIM_ENABLED", "false").lower() == "true"

@app.route(route="QuestionChecks")
async def security_hub(req: func.HttpRequest) -> func.HttpResponse:
    # Extract question, answer, and sources from the request
    try:
        req_body = req.get_json()
        question = req_body.get('question')
    except ValueError:
        return func.HttpResponse("Invalid request", status_code=400)

    if not question:
        return func.HttpResponse("Missing question in the request", status_code=400)
    logging.info(f"Received params: question={question[:100]}")
    #Call content safety functions
    if APIM_ENABLED:
        content_safety_key=await get_secret("apimSubscriptionKey")
        key=AzureKeyCredential(content_safety_key)
        endpoint=os.environ.get("APIM_ENDPOINT")
    else:
        content_safety_key=await get_secret("contentSafetyKey")
        endpoint=CONTENT_SAFETY_ENDPOINT
    async with DefaultAzureCredential() as credential:
        if(APIM_ENABLED):
            content_safety_credential=key
        else:
            content_safety_credential=credential
        async with ContentSafetyClient(endpoint=endpoint, credential=content_safety_credential) as client:
            checks = [
                safety_checks.prompt_shield_wrapper(question,client),
                safety_checks.jailbreak_detection_wrapper(question,client),
                safety_checks.analyze_text_wrapper(question,client)
            ]
            check_names = ["promptShield", "jailbreak","TextAnalysis"]
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

        # Prepare the response object
        response_data = {
            "results": check_results,
            "details":details
        }

        # Return a JSON response
        return func.HttpResponse(json.dumps(response_data), status_code=200, mimetype="application/json")

@app.route(route="AnswerChecks")
async def answer_checks(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        question = req_body.get('question')
        answer = req_body.get('answer')
        sources = req_body.get('sources')
    except ValueError:
        return func.HttpResponse("Invalid request", status_code=400)

    if not question or not answer or not sources:
        return func.HttpResponse("Missing question, answer, or sources in the request", status_code=400)
    logging.info(f"Received params: question={question[:100]}, answer={answer[:100]}, sources={sources[:100]}")
    #Call content safety functions
    if APIM_ENABLED:
        content_safety_key=await get_secret("apimSubscriptionKey")
        endpoint=os.environ.get("APIM_ENDPOINT")
    else:
        content_safety_key=await get_secret("contentSafetyKey")
        endpoint=CONTENT_SAFETY_ENDPOINT
    key=AzureKeyCredential(content_safety_key)
    
    async with ContentSafetyClient(endpoint=endpoint, credential=key) as client:
        checks = [
            safety_checks.groundedness_check_wrapper(question, answer, sources,client),
            safety_checks.protected_material_detection_wrapper(answer,client),
            safety_checks.analyze_text_wrapper(answer,client)
        ]
        check_names = ["groundedness","protectedMaterial","TextAnalysis"]
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

    # Prepare the response object
    response_data = {
        "results": check_results,
        "details":details
    }

    # Return a JSON response
    return func.HttpResponse(json.dumps(response_data), status_code=200, mimetype="application/json")