import azure.functions as func
import os
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import TextCategory
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.ai.contentsafety.models import AnalyzeTextOptions
from azure.core.rest import HttpRequest
import logging
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")


async def groundedness_check(question,answer,sources,safety_client: ContentSafetyClient):
    request = HttpRequest(method="POST",
    url="/text:detectGroundedness",
    json={
        "task": "QnA",
        "text": answer,     
        "groundingSources": [sources],
        "qna": {"query": question}, 
    },
    params={"api-version": CONTENT_SAFETY_API_VERSION})
    response = await safety_client.send_request(request)
    status_code = response.status_code
    json_response = response.json()
    check_result = json_response.get("ungroundedDetected")
    return "ungrounded",status_code, check_result

async def prompt_shield(question,sources,safety_client: ContentSafetyClient):
    request = HttpRequest(method="POST",
    url="/text:shieldPrompt",
    json={
        "userPrompt": question,
        "documents": [sources] 
    },
    params={"api-version": CONTENT_SAFETY_API_VERSION})
    response = await safety_client.send_request(request)
    status_code = response.status_code
    json_response = response.json()
    check_result = json_response.get("userPromptAnalysis").get("attackDetected")
    return "promptShield",status_code, check_result
        
async def jailbreak_detection(question,safety_client: ContentSafetyClient):
    request = HttpRequest(method="POST",
    url="/text:detectJailbreak",
    json={
        "text": question  #Max 1K characters
    },
    params={"api-version": CONTENT_SAFETY_API_VERSION})
    response = await safety_client.send_request(request)
    status_code = response.status_code
    json_response = response.json()
    check_result = json_response.get("jailbreakAnalysis").get("detected")
    return "jailbreak",status_code, check_result
        
async def protected_material_detection(question,safety_client: ContentSafetyClient):
    if(question.__len__()>100): #Protected material detection requires more than 100 characters
        request = HttpRequest(method="POST",
        url="/text:detectProtectedMaterial",
        json={
            "text": question  #Max 1K characters
        },
        params={"api-version": CONTENT_SAFETY_API_VERSION})
        response = await safety_client.send_request(request)
        status_code = response.status_code
        json_response = response.json()
        check_result = json_response.get("protectedMaterialAnalysis").get("detected")
        return "protectedMaterial",status_code, check_result