from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DISCOUNT_TIME: int
    model_config = SettingsConfigDict(env_file=".env")

# Instanciamos para exportar
settings = Settings()
