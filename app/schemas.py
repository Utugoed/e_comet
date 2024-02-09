from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class SortOrder(Enum):
    desc = "desc"
    asc = "asc"

class RepositorySortField(Enum):
    repo = "repo"
    owner = "owner"
    position = "position"
    stars = "stars"
    watchers = "watchers"
    forks = "forks"
    open_issues = "open_issues"
    language = "language"

class Repository(BaseModel):
    repo: str = Field(..., title="Repo's name", description="full_name in the GitHub API")
    owner: str = Field(..., title="Repo's owner")
    position_cur: int = Field(..., title="Top position")
    position_prev: int = Field(..., title="Previous top position")
    stars: int = Field(..., title="Number of stars")
    watchers: int = Field(..., title="Number of stars")
    forks: int = Field(..., title="Number of forks")
    open_issues: int = Field(..., title="Number of open issues")
    language: str = Field(..., title="Language")

class Activity(BaseModel):
    date: datetime = Field(..., title="Date")
    commits: int = Field(..., title="Number of commits")
    authors: List[str] = Field(..., title="List of developers", description="List of developers who made the commits")
