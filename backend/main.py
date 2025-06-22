import pyodbc
from config import settings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai


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

class OrderStatusResponse(BaseModel):
    customerNumber: int
    customerName: str
    phoneNumber: str | None
    orderDate: str | None
    species: str | None
    boardType: str | None
    mountPrice: float
    boardPrice: float
    depositCash: float
    depositCheck: float
    paymentCash: float
    paymentCheck: float
    readyDate: str | None
    calledDate: str | None
    pickupDate: str | None
    balance: float
    lastUpdatedAt: str


# --- NEW, COMPLETE API Endpoint ---
@app.get("/api/order-status/{customer_name}", response_model=OrderStatusResponse)
async def get_order_status(customer_name: str):
    """
    Retrieves the complete status of an order from the database by customer name.
    """
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={settings.db_server};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password}"
    )
    
    # The query now selects every single column (*)
    query = "SELECT * FROM Orders WHERE CustomerName LIKE '%' + ? + '%'"
    
    row = None
    try:
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, customer_name)
                row = cursor.fetchone()

    except Exception as e:
        print(f"An error occurred during DB query: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")

    if not row:
        raise HTTPException(status_code=404, detail=f"Order with customer name '{customer_name}' not found.")

    # Helper function to safely convert dates to strings
    def format_date(date_obj):
        return str(date_obj) if date_obj else None

    # We now map every column from the database row to our Pydantic model
    order_data = OrderStatusResponse(
        customerNumber=row.CustomerNumber,
        customerName=row.CustomerName,
        phoneNumber=row.PhoneNumber,
        orderDate=format_date(row.OrderDate),
        species=row.Species,
        boardType=row.BoardType,
        mountPrice=row.MountPrice,
        boardPrice=row.BoardPrice,
        depositCash=row.DepositCash,
        depositCheck=row.DepositCheck,
        paymentCash=row.PaymentCash,
        paymentCheck=row.PaymentCheck,
        readyDate=format_date(row.ReadyDate),
        calledDate=format_date(row.CalledDate),
        pickupDate=format_date(row.PickupDate),
        balance=row.Balance,
        lastUpdatedAt=format_date(row.LastUpdatedAt)
    )
    return order_data

# =================================================================
# START: NEW AZURE AGENT PROXY ENDPOINT
# =================================================================
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

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
# =================================================================
# END: NEW AZURE AGENT PROXY ENDPOINT
# =================================================================
