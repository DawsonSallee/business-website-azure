from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This tells pydantic to load variables from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Define your application settings
    # The types (str, int, etc.) are important for validation
    google_api_key: str
    db_server: str
    db_name: str
    db_user: str
    db_password: str
    function_url: str
    function_key: str

# Create a single, reusable instance of the settings
settings = Settings()