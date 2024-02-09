import json
import os

from datetime import datetime
from typing import Any, List

import httpx

from app.exceptions import AccessBlockedException, RateLimitException
from app.logging import app_logger


class GitHubAPI:
    def __init__(self):
        access_token = os.getenv("ACCESS_TOKEN")
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.since = 1
    
    async def _get_request(self, url: str) -> Any:
        #Perform GET request to GitHub API
        app_logger.info(f"Request to {url}")
        try:
            async with httpx.AsyncClient(headers=self.headers, verify=False) as client:
                response = await client.get(url=url)
            app_logger.info(f"Successfull request. Response: {response}")

            if response.status_code == 403:
                content = json.loads(response.content)
                if content.get('message', '').startswith("API rate limit exceeded"):
                    raise RateLimitException
                if content.get('message', '') == "Repository access blocked":
                    raise AccessBlockedException
            return response
        
        except AccessBlockedException:
            raise AccessBlockedException
        
        except RateLimitException:
            raise RateLimitException
        
        except Exception as ex:
            app_logger.error("RequestError", exc_info=True)

    async def repos_list(self, since: int) -> List[dict]:
        #Receive repos list from GitHub
        app_logger.info("Getting list of repositories")
        
        url = f"https://api.github.com/repositories?since={since}"
        response = await self._get_request(url=url)
        repos_list = response.json()
        return repos_list
    
    async def repo_detail(self, repo: dict) -> dict:
        app_logger.info(f"Getting {repo['owner']['login']}/{repo['name']} detail")
        
        detail_url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}"
        detail_response = await self._get_request(url=detail_url)
        repo_detail = detail_response.json()
        return repo_detail

    async def repo_activities(self, repo: dict) -> dict:
        activities_list = []
        check_activities = True
        while check_activities:
            url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}/activity?per_page=100"
            response = await self._get_request(url=url)
            activities = response.json()
            
            activities_list += activities
            check_activities = len(activities) == 100

        return activities_list

github = GitHubAPI()    
