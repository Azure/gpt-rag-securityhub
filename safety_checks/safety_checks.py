import os
import logging
from azure.ai.contentsafety.aio import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions,AnalyzeTextResult
from azure.core.rest import HttpRequest
import asyncio
from shared.util import divide_string
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")
CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
BLOCK_LIST_CHECK = os.environ.get("BLOCK_LIST_CHECK", "false").lower() == "true"
BLOCK_LISTS_NAMES = os.environ.get("BLOCK_LISTS_NAMES", "").split(",")
#API hard limits
MAX_PROMPTSHIELD_LENGTH = 10000
MAX_GROUNDEDNESS_SOURCES_LENGTH = 55000
MAX_GROUNDEDNESS_ANSWER_LENGTH = 6000
MAX_GROUNDEDNESS_QUESTION_LENGTH = 1500
MAX_PROTECTED_MATERIAL_LENGTH = 1000
MIN_PROTECTED_MATERIAL_LENGTH = 110
MAX_ANALYZE_TEXT_LENGTH = 10000
MAX_JAILBREAK_LENGTH = 1000

async def groundedness_check(question, answer, sources, client: ContentSafetyClient):
    url = "/text:detectGroundedness"
    json_payload = {
        "task": "QnA",
        "text": answer,
        "groundingSources": [sources],
        "qna": {"query": question},
    }
    params = {"api-version": CONTENT_SAFETY_API_VERSION}
    request = HttpRequest("POST", url, json=json_payload, params=params)
    
    response = await client.send_request(request)
    try:
        response.raise_for_status()  # Raises an error for bad status
        json_response = response.json()
        check_result = json_response.get("ungroundedDetected")
        return check_result,json_response
    finally:
        await response.close()  # Ensure the response is closed

# Wrapper function to handle the splitting of the input strings within API limits
async def groundedness_check_wrapper(question, answer, sources, client: ContentSafetyClient):
    sources=divide_string(sources, max_chars=MAX_GROUNDEDNESS_SOURCES_LENGTH)
    question=divide_string(question, max_chars=MAX_GROUNDEDNESS_QUESTION_LENGTH)
    answer=divide_string(answer, max_chars=MAX_GROUNDEDNESS_ANSWER_LENGTH)
    checks=[]
    for source in sources:
        for q in question:
            for a in answer:
                checks.append(groundedness_check(q,a,source,client))
    results=await asyncio.gather(*checks,return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Error occurred during groundedness check: {result}")
            return False, f"Prompt failed groundedness check with exception {result}"
        else:
            check_result, check_details = result
            if check_result:
                return check_result, check_details
    return False, "Prompt passed groundedness check"
    
    
    
async def prompt_shield(question, client: ContentSafetyClient):
    url = "/text:shieldPrompt"
    json_payload = {"userPrompt": question}
    params = {"api-version": CONTENT_SAFETY_API_VERSION}
    request = HttpRequest("POST", url, json=json_payload, params=params)
    
    response = await client.send_request(request)
    try:
        response.raise_for_status()  # Raises an error for bad status
        json_response = response.json()
        check_result = json_response.get("userPromptAnalysis").get("detected")
        return check_result,json_response
    finally:
        await response.close()  # Ensure the response is closed

# Wrapper function to handle the splitting of the input strings within API limits
async def prompt_shield_wrapper(question, client: ContentSafetyClient):
    question=divide_string(question, max_chars=MAX_PROMPTSHIELD_LENGTH)
    checks=[]
    for q in question:
        checks.append(prompt_shield(q,client))
    results=await asyncio.gather(*checks,return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Error occurred during prompt shield check: {result}")
            return False, f"Prompt failed prompt shield check with exception {result}"
        else:
            check_result, check_details = result
            if check_result:
                return check_result, check_details
    return False, "Prompt passed prompt shield check"

async def jailbreak_detection(question, client: ContentSafetyClient):
    url = "/text:detectJailbreak"
    json_payload = {"text": question}
    params = {"api-version": CONTENT_SAFETY_API_VERSION}
    request = HttpRequest("POST", url, json=json_payload, params=params)
    
    response = await client.send_request(request)
    try:
        response.raise_for_status()  # Raises an error for bad status
        json_response = response.json()
        check_result = json_response.get("jailbreakAnalysis").get("detected")
        return check_result,json_response
    except Exception as e:
        logging.error(f"Error occurred during jailbreak check: {e}")
        raise e
    finally:
        await response.close()  # Ensure the response is closed
        
# Wrapper function to handle the splitting of the input strings within API limits
async def jailbreak_detection_wrapper(question, client: ContentSafetyClient):
    question=divide_string(question, max_chars=MAX_JAILBREAK_LENGTH)
    checks=[]
    for q in question:
        checks.append(jailbreak_detection(q,client))
    results=await asyncio.gather(*checks,return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Error occurred during jailbreak check: {result}")
            return False, f"Prompt failed jailbreak check with exception {result}"
        else:
            check_result, check_details = result
            if check_result:
                logging.info(f"Jailbreak detected")
                return check_result, check_details
    return False, "Prompt passed jailbreak check"

async def protected_material_detection(answer, client: ContentSafetyClient):
    url = "/text:detectProtectedMaterial"
    json_payload = {
        "text": answer  # Max 1K characters
    }
    params = {"api-version": CONTENT_SAFETY_API_VERSION}
    request = HttpRequest("POST", url, json=json_payload, params=params)
    
    response = await client.send_request(request)
    try:
        response.raise_for_status()  # Raises an error for bad status
        json_response = response.json()
        check_result = json_response.get("protectedMaterialAnalysis", {}).get("detected")
        return check_result,json_response
    finally:
        await response.close()  # Ensure the response is closed

# Wrapper function to handle the splitting of the input strings within API limits
async def protected_material_detection_wrapper(answer, client: ContentSafetyClient):
    if(len(answer)<MIN_PROTECTED_MATERIAL_LENGTH):
        return True, f"Error: Answer is too short for protected material check(minimum length is {MIN_PROTECTED_MATERIAL_LENGTH} characters)"
    answer=divide_string(answer, min_chars=MIN_PROTECTED_MATERIAL_LENGTH, max_chars=MAX_PROTECTED_MATERIAL_LENGTH)
    checks=[]
    for a in answer:
        checks.append(protected_material_detection(a,client))
    results=await asyncio.gather(*checks,return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Error occurred during protected material check: {result}")
            return False, f"Prompt failed protected material check with exception {result}"
        else:
            check_result, check_details = result
            if check_result:
                return check_result, check_details
    return False, "Prompt passed protected material check"


async def analyze_text(text, client: ContentSafetyClient):
    if BLOCK_LIST_CHECK:
        options=AnalyzeTextOptions(text=text,blocklistNames=BLOCK_LISTS_NAMES)
    else:    
        options=AnalyzeTextOptions(text=text)
    result= await client.analyze_text(options=options)
    return False, result

# Wrapper function to handle the splitting of the input strings within API limits
async def analyze_text_wrapper(text, client: ContentSafetyClient):
    texts=divide_string(text, max_chars=MAX_ANALYZE_TEXT_LENGTH)
    checks=[]
    details={'blocklistsMatch': [], 'categoriesAnalysis': []}
    max_category_values={}
    for text in texts:
        checks.append(analyze_text(text,client))
    results=await asyncio.gather(*checks,return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logging.error(f"Error occurred during text analysis check: {result}")
            return True, f"Prompt failed text analysis check with exception {result}"
        else:
            check_result, check_details = result
            logging.info(f"check_details: {check_details}")
            # Update max_category_values with the maximum severity found for each category
            for category in check_details["categoriesAnalysis"]:
                max_category_values[category['category']] = max(max_category_values.get(category['category'], 0), category['severity'])

    # Update details["categoriesAnalysis"] with the maximum severity scores
    for category, severity in max_category_values.items():
        details["categoriesAnalysis"].append({'category': category, 'severity': severity})

    return False, details