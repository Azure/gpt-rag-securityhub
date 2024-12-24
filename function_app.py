import azure.functions as func
import os
import logging
import json
import safety_checks.check_execution as check_execution
import auditing.audit as auditing


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")
APIM_ENABLED=os.environ.get("APIM_ENABLED", "false").lower() == "true"
AZURE_DB_URI=os.environ.get("AZURE_DB_URI")
AZURE_DB_NAME=os.environ.get("AZURE_DB_NAME")
AZURE_DB_ID=os.environ.get("AZURE_DB_ID")
AZURE_DB_URI = f"https://{AZURE_DB_ID}.documents.azure.com:443/"
PLUGINS_FOLDER = f"plugins"
RESPONSABLE_AI_CHECK=os.environ.get("RESPONSABLE_AI_CHECK", "false").lower() == "true"

logging.basicConfig(level=logging.INFO)
@app.route(route="QuestionChecks")
async def cf_question_checks(req: func.HttpRequest) -> func.HttpResponse:
    # Extract question, answer, and sources from the request
    try:
        req_body = req.get_json()
        question = req_body.get('question')
    except ValueError:
        return func.HttpResponse("Invalid request", status_code=400)

    if not question:
        return func.HttpResponse("Missing question in the request", status_code=400)
    logging.info(f"Received params: question={question[:100]}")
    check_results,details=await check_execution.question_checks(question)

    # Prepare the response object
    response_data = {
        "results": check_results,
        "details":details
    }

    # Return a JSON response
    return func.HttpResponse(json.dumps(response_data), status_code=200, mimetype="application/json")

@app.route(route="AnswerChecks")
async def cf_answer_checks(req: func.HttpRequest) -> func.HttpResponse:
    
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
    check_results,details=await check_execution.answer_checks(answer,question,sources)
    # Prepare the response object
    response_data = {
        "results": check_results,
        "details":details
    }

    # Return a JSON response
    return func.HttpResponse(json.dumps(response_data), status_code=200, mimetype="application/json")

@app.route(route="Audit")
async def audit(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        question = req_body.get('question')
        answer = req_body.get('answer')
        sources = req_body.get('sources')
        security_checks = req_body.get('security_checks')
        conversation_id = req_body.get('conversation_id')
    except ValueError:
        return func.HttpResponse("Invalid request", status_code=400)
    try:
        await auditing.audit_to_db(conversation_id, question, answer, sources, security_checks)
    except Exception as e:
        return func.HttpResponse(f"Error auditing to db: {e}", status_code=400)
    return func.HttpResponse("Logging updated", status_code=200)