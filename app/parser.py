import json
import os

from datetime import datetime
from typing import Any, List

import httpx

from app.config import Settings
from app.exceptions import AccessBlockedException, RateLimitException
from app.logging import app_logger


class GitHubAPI:
    def __init__(self):
        access_token = Settings().access_token
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.retry_number = 5
    
    async def _get_request(self, url: str) -> Any:
        #Performs GET request to GitHub API
        app_logger.info(f"Request to {url}")

        #Retry-construction
        for i in range(self.retry_number + 1):
            try:
                async with httpx.AsyncClient(headers=self.headers, verify=False) as client:
                    response = await client.get(url=url)
                app_logger.info(f"Successfull request. Response: {response}")

                #These exceptions provide a simpler way 
                #To handle data retrieval problems.
                if response.status_code == 403:
                    content = json.loads(response.content)
                    if content.get('message', '').startswith("API rate limit exceeded"):
                        raise RateLimitException
                    if content.get('message', '') == "Repository access blocked":
                        raise AccessBlockedException
                return response
            
            #Reraise data retrieval problems exceptions
            except AccessBlockedException:
                raise AccessBlockedException
            except RateLimitException:
                raise RateLimitException

            #Retry-construction
            except httpx.HTTPError as http_ex:
                if i == self.retry_number:
                    raise http_ex
                continue
            
            except Exception as ex:
                app_logger.error("RequestError", exc_info=True)
                raise ex

    async def repos_list(self, since: int) -> List[dict]:
        app_logger.info("Getting list of repositories")
        
        url = f"https://api.github.com/repositories?since={since}"
        response = await self._get_request(url=url)
        repos_list = response.json()
        return repos_list
    
    async def repo_detail(self, repo: dict) -> dict:
        app_logger.info(f"Getting {repo['owner']['login']}/{repo['name']} detail")
        
        url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}"
        response = await self._get_request(url=url)
        repo_detail = response.json()
        return repo_detail

    async def repo_activities(self, repo: dict) -> dict:
        app_logger.info(f"Getting activity of /{repo['owner']['login']}/{repo['name']}")
        
        url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}/activity?per_page=100"
        try:
            response = await self._get_request(url=url)
        except httpx.HTTPError as ex:
            app_logger.error("HTTPError", exc_info=True)
            return []
        activities_list = response.json()

        while True:
            #Link header format: '<URL>; rel="RELATION_TYPE"'
            link = response.headers.get('link')
            if not link:
                return activities_list

            url, rel = link.split(';')
            url = url.strip(' <>')
            rel = rel[6:-1]
            if rel != "next":
                return activities_list
            
            try:
                response = await self._get_request(url=url)
            except httpx.HTTPError as ex:
                app_logger.error("HTTPError", exc_info=True)
                return activities_list

            activities = response.json()
            activities_list += activities

github = GitHubAPI()    
