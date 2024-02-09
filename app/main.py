from datetime import date
from typing import List, Optional

from fastapi import FastAPI

from app.db import Database
from app.logging import app_logger
from app.parser import GitHubAPI
from app.schemas import Activity, Repository, RepositorySortField, SortOrder


app = FastAPI()
github = GitHubAPI()
db = Database()


@app.get("/repos/top100", response_model=List[Repository])
async def repositories_top(sort_by: Optional[RepositorySortField]=None, order: Optional[SortOrder]=None):
    sort_by = sort_by if not sort_by else sort_by.value
    order = order if not order else order.value

    repos_list = await db.get_repos_top(sort_by, order)
    return repos_list

@app.get("/repos/{owner}/{repo}/activity", response_model=List[Activity])
async def read_item(
    owner: str, repo: str, since: date=date(1980, 1, 1), until: date=date(3000, 1, 1)
):
    activity = await db.get_activity(
        repo=repo, owner=owner, since=since, until=until
    )
    response_data = [Activity.parse_obj(el) for el in activity]
    return response_data
