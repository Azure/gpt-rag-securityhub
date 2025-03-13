import azure.functions as func
import os
import logging
import datetime
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
CONTENT_SAFETY_ENDPOINT = os.environ.get("CONTENT_SAFETY_ENDPOINT")
CONTENT_SAFETY_API_VERSION = os.environ.get("CONTENT_SAFETY_API_VERSION", "2024-02-15-preview")
APIM_ENABLED=os.environ.get("APIM_ENABLED", "false").lower() == "true"
AZURE_DB_NAME=os.environ.get("AZURE_DB_NAME")
AZURE_DB_ID=os.environ.get("AZURE_DB_ID")
AZURE_DB_URI = f"https://{AZURE_DB_ID}.documents.azure.com:443/"
AZURE_DB_CONTAINER_NAME = os.environ.get("AZURE_DB_CONTAINER_NAME")
PLUGINS_FOLDER = f"plugins"
RESPONSABLE_AI_CHECK=os.environ.get("RESPONSABLE_AI_CHECK", "false").lower() == "true"

async def audit_to_db(conversation_id, question, answer, sources, security_checks):
    async with DefaultAzureCredential() as credential:       
        async with CosmosClient(AZURE_DB_URI, credential=credential) as db_client:
            db = db_client.get_database_client(database=AZURE_DB_NAME)
            container = db.get_container_client(AZURE_DB_CONTAINER_NAME)
            try:
                conversation = await container.read_item(item=conversation_id, partition_key=conversation_id)
                logging.info(f"[orchestrator] conversation {conversation_id} retrieved.")
            except Exception as e:
                logging.info(f"[orchestrator] customer sent an inexistent conversation_id, saving new conversation_id")        
                conversation = await container.create_item(body={"id": conversation_id})
            # get conversation data
            conversation_data = conversation.get('conversation_data', 
                                                {'start_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'interactions': []})
            # Append the question and answer to the respective arrays
            interaction = {
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'question': question, 
                'answer': answer, 
                'sources': sources,
                "security_checks": security_checks
            }
            conversation_data['interactions'].append(interaction)
            conversation['conversation_data'] = conversation_data
            # Update the item in the container
            await container.replace_item(item=conversation, body=conversation)
            logging.info(f"[orchestrator] conversation {conversation_id} updated with new interaction.")
    return   