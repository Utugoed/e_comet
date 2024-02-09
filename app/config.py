import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_repositories_since: int
    activity_table: str
    top_table: str
    access_token: str
    connection_string: str

    @staticmethod
    def set_since(since: int):
        os.environ['GITHUB_REPOSITORIES_SINCE'] = str(since)

    model_config = SettingsConfigDict(env_file=".env")