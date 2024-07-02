import azure.functions as func
import os
import safety_checks.safety_checks as safety_checks
import logging
import asyncio
import json
import aiohttp


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

import azure.functions as func
import logging
import requests  # You might need to install this dependency

CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_KEY = os.environ.get("CONTENT_SAFETY_KEY")
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")

# Initialize your Azure Function
@app.route(route="SecurityHub")
async def security_hub(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(f"Processing request")
    # Extract question, answer, and sources from the request
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
    headers={
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": CONTENT_SAFETY_KEY
        }
    async with aiohttp.ClientSession(headers=headers,base_url=CONTENT_SAFETY_ENDPOINT) as session:
        checks = [
            safety_checks.groundedness_check(question, answer, sources, session),
            safety_checks.prompt_shield(question, session),
            safety_checks.jailbreak_detection(question, session),
            safety_checks.protected_material_detection(answer, session)
        ]
        check_results = {}
        logging.info("Starting content safety checks")
        successful=True
        for check in asyncio.as_completed(checks):
            try:
                check_name, status_code, check_result = await check
                # If the status code is not 200, record the error and continue to the next check
                if status_code != 200:
                    check_results[check_name] = f"Error: {check_name} Failed request with code {status_code}"
                    successful=False
                # If the check_result indicates a failure, record the failure
                elif check_result:
                    check_results[check_name] = f"Prompt failed {check_name} check"
                    successful=False
                else:
                    logging.info(f"Prompt passed {check_name} check")
                    check_results[check_name] = f"Prompt passed {check_name} check"
            except Exception as e:
                logging.error(f"Error occurred during content safety check: {e}")
                check_results[check_name] = f"Error: {check_name} Failed with exception {e}"
                successful=False
    # Prepare the response object
    response_data = {
        "successful": successful,
        "details": check_results
    }

    # Return a JSON response
    return func.HttpResponse(json.dumps(response_data), status_code=200, mimetype="application/json")
