# ==============================================================================
# main.py
#
# This file defines the backend API for the business website.
# It uses the FastAPI framework to create two primary endpoints:
# 1. A direct proxy to an Azure Function for simple order status lookups.
# 2. A secure proxy to a powerful Azure AI Agent for handling complex chat.
# ==============================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import httpx
from config import settings

# ==============================================================================
# 2. APP INITIALIZATION & MIDDLEWARE
# Here, we create the main FastAPI application instance and configure its
# global security settings, such as Cross-Origin Resource Sharing (CORS).
# ==============================================================================
app = FastAPI(title="Business Website Backend API")

# --------- CORS Middleware ---------
# The origins list acts as a security whitelist. Only websites on this list
# are allowed to make requests to this API. This prevents other malicious
# sites from using your backend.
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "https://proud-ground-0066a270f.6.azurestaticapps.net"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 3. PYDANTIC MODELS (Data Contracts)
# These classes define the expected JSON structure for API requests and
# responses. FastAPI uses them to automatically validate data, which is a
# key security and reliability feature.
# =============================================================================
class OrderStatusResponse(BaseModel):
    customerName: str
    orderDate: str | None
    readyDate: str | None
    calledDate: str | None
    pickupDate: str | None
    mountPrice: float
    boardPrice: float
    depositCash: float
    depositCheck: float
    paymentCash: float
    paymentCheck: float
    balance: float
    lastUpdatedAt: str | None

class AgentChatRequest(BaseModel):
    message: str

class AgentChatResponse(BaseModel):
    reply: str

# ==============================================================================
# 4. API ENDPOINTS
# These are the functions that handle incoming web requests to specific URLs.
# ==============================================================================
@app.get("/")
def read_root():
    """A simple endpoint to check if the server is running."""
    return {"Status": "Online"}

@app.get("/api/order-status/{customer_name}", response_model=OrderStatusResponse, summary="Get Order Status Directly")
async def get_order_status(customer_name: str):
    """
    Acts as a secure proxy to call the GetOrderStatusFuzzy Azure Function.
    It authenticates using an API key and then robustly cleans the
    returned data before validation.
    """

    # Configuration is loaded securely from the settings object.
    target_url = f"{settings.function_url}?customer_name={customer_name}"
    headers = {
        'x-functions-key': settings.function_key
    }

    try:
        # The `async with` block ensures the HTTP client connection is properly closed.
        async with httpx.AsyncClient() as client:
            # 2. THE EXECUTION CHANGE: Send the request WITH the headers.
            response = await client.get(target_url, headers=headers)

            # A more robust way to check for errors. This will automatically raise
            # an exception for any 4xx (client) or 5xx (server) error codes.
            response.raise_for_status()

            # If we get here, the request was successful (status 200 OK).
            messy_data = response.json()

        # This nested helper function makes our endpoint resilient.
        def to_float(value):
            if value is None or value == '':
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        # Create the clean dictionary, safely getting values and cleaning numbers.
        clean_data = {
            "customerNumber": messy_data.get("customerNumber"), # Assuming function returns this
            "customerName": messy_data.get("customerName"),
            "phoneNumber": messy_data.get("phoneNumber"),
            "orderDate": messy_data.get("orderDate"),
            "species": messy_data.get("species"),
            "boardType": messy_data.get("boardType"),
            "mountPrice": to_float(messy_data.get("mountPrice")),
            "boardPrice": to_float(messy_data.get("boardPrice")),
            "depositCash": to_float(messy_data.get("depositCash")),
            "depositCheck": to_float(messy_data.get("depositCheck")),
            "paymentCash": to_float(messy_data.get("paymentCash")),
            "paymentCheck": to_float(messy_data.get("paymentCheck")),
            "readyDate": messy_data.get("readyDate"),
            "calledDate": messy_data.get("calledDate"),
            "pickupDate": messy_data.get("pickupDate"),
            "balance": to_float(messy_data.get("balance")),
            "lastUpdatedAt": messy_data.get("lastUpdatedAt")
        }
        
        # FastAPI validates our `clean_data` against the `OrderStatusResponse` model before sending.
        return clean_data

    except httpx.HTTPStatusError as e:
        # This catches errors from the function call itself (e.g., function returned 404).
        print(f"Azure Function returned an error: {e.response.status_code}")
        raise HTTPException(status_code=502, detail="The order status service is currently unavailable.")
    except Exception as e:
        # This is a general catch-all for any other unexpected errors.
        print(f"An unexpected error occurred in get_order_status: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.post("/api/chat-with-agent", response_model=AgentChatResponse)
async def chat_proxy_to_azure_agent(request: AgentChatRequest):
    """
    This endpoint acts as a secure proxy to the Azure Agent.
    It takes a user's message and uses the Azure SDK to get a reply.
    """
    try:
        # 1. Connect to your Azure AI Project using the secure DefaultAzureCredential
        #    This automatically finds your credentials from your environment.
        project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=settings.azure_ai_project_endpoint
        )
        agent = project.agents.get_agent(settings.azure_ai_agent_name)

        # 3. Create a new, clean conversation thread for this interaction
        thread = project.agents.threads.create()

        # 4. Add the user's message to the new thread
        project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=request.message # Use the message from the frontend request
        )

        # 5. Run the agent and wait for it to process the message
        run = project.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id
        )

        if run.status == "failed":
            print(f"Azure Agent run failed: {run.last_error}")
            raise HTTPException(status_code=500, detail="The AI agent failed to process the request.")

        # 6. Get all messages from the thread to find the assistant's reply
        messages = project.agents.messages.list(thread_id=thread.id)
        
        # 7. Find the last message from the assistant and extract its text
        assistant_reply = "Sorry, I couldn't get a response."
        for message in messages:
            # The agent's response is the first message where the role is 'assistant'
            if message.role == "assistant" and message.text_messages:
                assistant_reply = message.text_messages[-1].text.value
                break # We found the reply, so we can stop looking

        # 8. Clean up the thread we created
        project.agents.threads.delete(thread.id)

        # 9. Send the clean text reply back to our frontend
        return AgentChatResponse(reply=assistant_reply)

    except Exception as e:
        print(f"An error occurred while calling the Azure Agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to communicate with the AI agent.")