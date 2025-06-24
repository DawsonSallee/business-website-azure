from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    # --- Settings for the /api/order-status endpoint ---
    # The full URL of your GetOrderStatusFuzzy Azure Function.
    function_url: str
    # The secret API key required to call the Azure Function.
    function_key: str

    # --- Settings for the /api/chat-with-agent endpoint ---
    # The endpoint URL of your Azure AI Project resource.
    azure_ai_project_endpoint: str
    # The unique name/ID of your deployed agent (e.g., "asst_...").
    azure_ai_agent_name: str

    # This tells Pydantic to look for a file named .env and that the variable
    # names in that file are case-sensitive.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# This creates a single, global instance of the settings that our app can use.
settings = Settings()