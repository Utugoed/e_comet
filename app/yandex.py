from typing import List

from app.config import Settings
from app.db import Database
from app.exceptions import AccessBlockedException, RateLimitException
from app.logging import app_logger
from app.parser import GitHubAPI


github = GitHubAPI()
db = Database()

def filter_repo_detail(repo_detail: dict) -> dict:
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

def group_activities(activities: List[dict], repo_name: str, owner: str) -> List[dict]:
    groupped_dict = {}
    for activity in activities:
        activity_date = activity['timestamp'][:10]
        date_activities = groupped_dict.get(
            activity_date,
            {
                'commits': 0,
                'authors': set(),
                'repo': repo_name,
                'owner': owner
            }
        )
        date_activities['commits'] += 1
        date_activities['authors'].add(activity['actor']['login'])
        groupped_dict[activity_date] = date_activities
    
    groupped_list = [
        {
            'repo': groupped_dict[activity_date]['repo'],
            'owner': groupped_dict[activity_date]['owner'],
            'date': activity_date,
            'commits': groupped_dict[activity_date]['commits'],
            'authors': f"ARRAY {list(groupped_dict[activity_date]['authors'])}"
        }
        for activity_date in groupped_dict.keys()
    ]
    return groupped_list

async def parse_handler():
    since = Settings().github_repositories_since
    try:
        repos_list = await github.repos_list(since)
    except RateLimitException:
        return []
    except httpx.HTTPError as ex:
        app_logger.error("HTTPError", exc_info=True)
        return {
            "OK": False,
            "error": ex
        }
    
    #GitHub API does not provide detail repository info
    #Checking it manually for each one
    detailed_repos_list = []
    for repo in repos_list:
        try:
            repo_detail = await github.repo_detail(repo)
        except RateLimitException:
            break
        except AccessBlockedException:
            continue
        except httpx.HTTPError as ex:
            app_logger.error("HTTPError", exc_info=True)
            continue
        
        try:
            activities = await github.repo_activities(repo)
        except RateLimitException:
            break
        app_logger.info(f"{activities=}")
        if activities:
            groupped_activities = group_activities(
                activities=activities,
                repo_name=repo['name'],
                owner=repo['owner']['login']
            )
            app_logger.info(f"{groupped_activities=}")
            app_logger.info(f"{','.join([str(v) for v in groupped_activities[0].values()])}")
            await db.update_activity(groupped_activities)

        filtered_repo = filter_repo_detail(repo_detail)
        detailed_repos_list.append(filtered_repo)
        since = repo['id'] + 1

    if detailed_repos_list:
        await db.update_repos(detailed_repos_list)
        Settings.set_since(since)
    
    return detailed_repos_list
