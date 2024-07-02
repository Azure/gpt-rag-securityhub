import os
import aiohttp
import logging
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")
CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")


async def groundedness_check(question,answer,sources,session: aiohttp.ClientSession):
    url="/contentsafety/text:detectGroundedness"
    json={
        "task": "QnA",
        "text": answer, #max 7,5K characters
        "groundingSources": [sources], #max 55K characters
        "qna": {"query": question}, #max 7,5K characters
    }
    params={"api-version": CONTENT_SAFETY_API_VERSION}
    async with session.post(url=url,json=json,params=params) as response:
        status_code = response.status
        json_response = await response.json()
        if status_code != 200:
            return "ungrounded",status_code, False
        check_result = json_response.get("ungroundedDetected")
    return "ungrounded",status_code, check_result

async def prompt_shield(question,session: aiohttp.ClientSession):
    url="/contentsafety/text:shieldPrompt"
    json={
        "userPrompt": question, #max 10K characters
    }
    params={"api-version": CONTENT_SAFETY_API_VERSION}
    async with session.post(url=url,json=json,params=params) as response:
        status_code = response.status
        json_response = await response.json()
        if status_code != 200:
            return "promptShield",status_code, False
        check_result = json_response.get("userPromptAnalysis").get("detected")
    return "promptShield",status_code, check_result
        
async def jailbreak_detection(question,session: aiohttp.ClientSession):
    url="/contentsafety/text:detectJailbreak"
    json={
        "text": question  #Max 1K characters
    }
    params={"api-version": CONTENT_SAFETY_API_VERSION}
    async with session.post(url=url,json=json,params=params) as response:
        status_code = response.status
        json_response = await response.json()
        if status_code != 200:
            return "jailbreak",status_code, False
        check_result = json_response.get("jailbreakAnalysis").get("detected")
    return "jailbreak",status_code, check_result
        
async def protected_material_detection(answer,session: aiohttp.ClientSession):
    if(answer.__len__()>100): #Protected material detection requires more than 100 characters
        url="/contentsafety/text:detectProtectedMaterial"
        json={
            "text": answer  #Max 1K characters
        }
        params={"api-version": CONTENT_SAFETY_API_VERSION}
        async with session.post(url=url,json=json,params=params) as response:
            status_code = response.status
            json_response = await response.json()
            if status_code != 200:
                return "protectedMaterial",status_code, False
            check_result = json_response.get("protectedMaterialAnalysis").get("detected")
        return "protectedMaterial",status_code, check_result
    else:
        raise ValueError("Question should have more than 100 characters for protected material detection")