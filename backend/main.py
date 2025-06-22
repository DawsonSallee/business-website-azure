import pyodbc
from config import settings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import httpx


# Load API key
genai.configure(api_key=settings.google_api_key)


# Create the FastAPI app instance
app = FastAPI()

# --- CORS Middleware ---
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

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    message: str
    # You could add history here later: history: list = []

class ChatResponse(BaseModel):
    reply: str


# --- API Endpoints ---
@app.get("/")
def read_root():
    """A simple endpoint to check if the server is running."""
    return {"Status": "Online"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    The main endpoint for the chatbot.
    Accepts a user's message and returns the AI's reply.
    """
    try:
        # Initialize the Generative Model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # --- TODO: Add your RAG logic here ---
        # 1. For now, we are just sending the message directly to the model.
        # 2. Later, you will first retrieve relevant context from your documents
        #    and then create a more detailed prompt like:
        #    prompt = f"Context: {retrieved_context}\n\nQuestion: {request.message}\n\nAnswer:"
        
        prompt = request.message

        # Generate content
        response = model.generate_content(prompt)

        # Return the generated text
        return ChatResponse(reply=response.text)
    except Exception as e:
        # If anything goes wrong, return a server error
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response from AI model.")

@app.get("/models")
async def list_models():
    """An endpoint to list all available Gemini models."""
    try:
        model_list = []
        for m in genai.list_models():
            # We only care about models that support the 'generateContent' method
            if 'generateContent' in m.supported_generation_methods:
                model_list.append({"name": m.name, "description": m.description})
        return {"models": model_list}


    except Exception as e:
        # If anything goes wrong, return a server error
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response from AI model.")
    

# --- New Database Endpoint ---

# This Pydantic model now exactly matches the `result` dictionary
# in your GetOrderStatusFuzzy function code.
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

@app.get("/api/order-status/{customer_name}", response_model=OrderStatusResponse)
async def get_order_status(customer_name: str):
    """
    Acts as a proxy to call the GetOrderStatusFuzzy Azure Function,
    and then robustly cleans the returned data before validation.
    """
    target_url = f"{settings.function_url}?customer_name={customer_name}"
    headers = {}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(target_url, headers=headers)

            if response.status_code != 200:
                error_detail = response.json().get("detail", response.text)
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            # Get the raw JSON data from the function, which we know might be messy.
            messy_data = response.json()

            # Define our own robust cleaning function right here.
            def to_float(value):
                if value is None or value == '':
                    return 0.0
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0

            # Create a new, clean dictionary by applying the fix to every field.
            # The .get() method safely handles missing keys from the messy data.
            clean_data = {
                "customerName": messy_data.get("customerName"),
                "orderDate": messy_data.get("orderDate"),
                "readyDate": messy_data.get("readyDate"),
                "calledDate": messy_data.get("calledDate"),
                "pickupDate": messy_data.get("pickupDate"),
                "mountPrice": to_float(messy_data.get("mountPrice")),
                "boardPrice": to_float(messy_data.get("boardPrice")),
                "depositCash": to_float(messy_data.get("depositCash")),
                "depositCheck": to_float(messy_data.get("depositCheck")),
                "paymentCash": to_float(messy_data.get("paymentCash")),
                "paymentCheck": to_float(messy_data.get("paymentCheck")),
                "balance": to_float(messy_data.get("balance")),
                "lastUpdatedAt": messy_data.get("lastUpdatedAt")
            }
            
            # Now, return the CLEAN data. FastAPI's automatic validation will
            # run on this clean_data dictionary and it will succeed.
            return clean_data

    except httpx.RequestError as e:
        print(f"HTTP request to Azure Function failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable: Could not connect to the order status service.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# --- Pydantic Models for the new endpoint ---
class AgentChatRequest(BaseModel):
    message: str

class AgentChatResponse(BaseModel):
    reply: str

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
            endpoint="https://businessaiagents-resource.services.ai.azure.com/api/projects/businessaiagents"
        )

        # 2. Get a reference to your specific agent by its ID
        #    (You can hard-code this ID from the Azure portal)
        agent = project.agents.get_agent("asst_k3iT84MhPHG4sk7jhMb3eDzv")

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
