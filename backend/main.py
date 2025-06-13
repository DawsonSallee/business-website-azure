import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API with your key
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    # In a real app, you might want to handle this more gracefully
    # For now, we'll let it raise an error if the key is missing.

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