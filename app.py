import asyncio
import json
import logging
import os

from typing import Any, List, Union

import asyncpg
import httpx
import psycopg2
import ssl

from dotenv import load_dotenv
from fastapi import FastAPI

from e_comet.schemas import Activity, Repository


load_dotenv("./e_comet/.env")

app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)

log_handler = logging.StreamHandler()
log_formatter = logging.Formatter("%(name)s - %(asctime)s - %(levelname)s: %(message)s")

log_handler.setFormatter(log_formatter)
app_logger.addHandler(log_handler)


class Database:
    def __init__(self):
        self.conn_string = os.getenv("CONNECTION_STRING")
        
    async def get_connection(self) -> asyncpg.Connection:
        app_logger.info("Connecting to Database")
        conn = await asyncpg.connect(self.conn_string)
        app_logger.info("Database was connected successfully")
        return conn
    
    async def update_repos(self, repos_list: List[dict]) -> None:
        #Preparing values tuples from 
        values_list = []
        for repo in repos_list:
            name = repo['name']
            owner = repo['owner']['login']
            position_cur = 0
            position_prev = 0
            stars = repo['stargazers_count']
            watchers = repo['watchers_count']
            forks = repo['forks']
            open_issues = repo['open_issues']
            language = repo['language']
            values = (name, owner, position_cur, position_prev, stars, watchers, forks, open_issues, language)
            values_list.append(values)
        
        conn = await self.get_connection()
        try:
            await conn.execute(
                f"""
                    INSERT INTO skorynin_test.repos
                    VALUES {','.join([str(values) for values in values_list])}
                    ON CONFLICT DO UPDATE
                """
            )
        except Exception as ex:
            app_logger.error("DB Error", exc_info=True)
        finally:
            await conn.close()


class GitHubAPI:
    def __init__(self):
        access_token = os.getenv("ACCESS_TOKEN")
        app_logger.info(f"{access_token=}")
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def _get_request(self, url: str) -> Any:
        #Perform GET request to GitHub API
        app_logger.info(f"Request to {url}")
        try:
            async with httpx.AsyncClient(headers=self.headers, verify=False) as client:
                response = await client.get(url=url)
            app_logger.info(f"Successfull request. Response: {response}")
            return response
        
        except Exception as ex:
            app_logger.error("RequestError", exc_info=True)

    async def repos_list(self) -> List[dict]:
        #Receive repos list from GitHub
        app_logger.info("Getting list of repositories")
        url = "https://api.github.com/repositories"
        response = await self._get_request(url=url)
        repos_list = json.loads(response.content)

        #GitHub API does not provide detail repository info
        #Checking it manually for each one and preparing a new list
        detail_list = []
        for repo in repos_list[:5]:
            detail_url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}"
            detail_response = await self._get_request(url=detail_url)
            repo_detail = json.loads(detail_response.content)
            detail_list.append(repo_detail)
        
        return detail_list

app = FastAPI()
github = GitHubAPI()
db = Database()

@app.get("/")#, response_model=List[Repository])
async def read_root():
    context = ssl.create_default_context()
    repos_list = await github.repos_list()
    print(repos_list)
    repo = {
        "repo": "repo",
        "owner": "owner",
        "position_cur": 1,
        "position_prev": 0,
        "stars": 5,
        "watchers": 5,
        "forks": 3,
        "open_issues": 0,
        "language": "python"
    }
    await db.update_repos(repos_list=repos_list)
    return repos_list


@app.get("/items/{item_id}", response_model=Activity)
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
