import os
import dotenv
import httpx
import json

dotenv.load_dotenv('.env')

access_token = os.getenv("ACCESS_TOKEN")
headers = {
    "Authorization": f"token {access_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
import datetime

x = "2024-02-02T08:33:54Z"
print(x)
print(str(x))