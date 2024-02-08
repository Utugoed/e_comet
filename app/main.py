import bisect
import json
import logging
import os

from typing import Any, List, Union

import httpx
import ssl

from dotenv import load_dotenv
from fastapi import FastAPI

from app.db import Database
from app.parser import GitHubAPI
from app.schemas import Activity, Repository


load_dotenv(".env")

app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)

log_handler = logging.StreamHandler()
log_formatter = logging.Formatter("%(name)s - %(asctime)s - %(levelname)s: %(message)s")

log_handler.setFormatter(log_formatter)
app_logger.addHandler(log_handler)


app = FastAPI()
github = GitHubAPI()
db = Database()

@app.get("/")#, response_model=List[Repository])
async def read_root():
    repos_list = await github.repos_list()
    top_100 = await db.get_repos()
    new_top = top_100.copy()
    
    #Inserting new repositories to top
    #While maintaining order
    for new_repo in repos_list:
        #Check if repository already in top
        for repo in new_top:
            if (repo['owner'] == new_repo['owner'] and repo['repo'] == new_repo['repo']):
                new_top.remove(repo)
                break
        bisect.insort(new_top, new_repo, key=lambda x: -x['stars'])

    for i, repo in enumerate(top_100, start=1):
        repo['position_cur'], repo['position_prev'] = i, i+1

    if top_100 == new_top[:100]:
        return new_top
    
    await db.update_repos(top_100)
    return top_100


@app.get("/items/{item_id}", response_model=Activity)
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
