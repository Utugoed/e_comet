import json
import logging
import os
from typing import Any, List

import httpx

from app.exceptions import AccessBlockedException, RateLimitException


app_logger = logging.getLogger('app')

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
    
    def _filter_repo_detail(self, repo_detail: dict) -> dict:
        #Leaving just needed fields
        result = {
            'repo': repo_detail['name'],
            'owner': repo_detail['owner']['login'],
            'position_cur': 0,
            'position_prev': 0,
            'stars': repo_detail['stargazers_count'],
            'watchers': repo_detail['watchers_count'],
            'forks': repo_detail['forks'],
            'open_issues': repo_detail['open_issues'],
            'language': repo_detail['language'] if repo_detail['language'] else "NULL",
        }
        return result

    async def repos_list(self) -> List[dict]:
        #Receive repos list from GitHub
        app_logger.info("Getting list of repositories")
        
        try:
            url = f"https://api.github.com/repositories?since={self.since}"
            response = await self._get_request(url=url)
        except RateLimitException:
            return []

        #If no more repositories
        #starting from the begining
        repos_list = json.loads(response.content)
        if len(repos_list) == 0:
            self.since = 1
        
        #GitHub API does not provide detail repository info
        #Checking it manually for each one and preparing a new list
        #And filtering important info
        formatted_list = []
        for repo in repos_list:
            try:
                detail_url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}"
                detail_response = await self._get_request(url=detail_url)
            except RateLimitException:
                break
            except AccessBlockedException:
                continue

            repo_detail = json.loads(detail_response.content)
            repo_dict = self._filter_repo_detail(repo_detail)
            formatted_list.append(repo_dict)
            self.since = repo_detail['id']

        return formatted_list
