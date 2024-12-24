# imports
import json
import logging
from shared.util import call_semantic_function

async def fairness(kernel, rai_plugin, arguments):
    """
    This function is used to evaluate the fairness of a given context. 
    It calls a semantic function that returns a response indicating whether the context is fair or not.
    The response is then parsed and returned in a dictionary format.
   
    Returns:
    dict: A dictionary containing the fairness evaluation response. The response includes the fairness status, answer, prompt tokens, and completion tokens.
        'fair' (bool): A flag indicating whether the context is fair or not. Defaults to True if not found.
        'answer' (str): The answer to the request. Defaults to an empty string if not found.
        'prompt_tokens' (str): The prompt tokens for the request. Retrieved using the get_usage_tokens function.
        'completion_tokens' (str): The completion tokens for the request. Retrieved using the get_usage_tokens function.
        'bypass' (bool): A flag indicating whether to bypass the the reminder flow steps (in case of an error has occurred).
    """    
    function_result =  await call_semantic_function(kernel, rai_plugin["Fairness"], arguments)
    logging.info(f"[code_orchest] RAG flow (Fairness) response: {function_result}")
    message_content = str(function_result)
    logging.info(f"[code_orchest] RAG flow (Fairness) response: {message_content}")
    try:
        response = message_content.strip("`json\n`")
        response_json = json.loads(response)
    except json.JSONDecodeError:
        logging.error(f"[code_orchest] error when executing RAG flow (Fairness). Invalid json: {function_result}")
        raise Exception(f"Triage was not successful due to a JSON error. Invalid json: {function_result}")

    result=response_json.get('fair', True) 
    reason=response_json.get('reason', '')

    return not result, reason
