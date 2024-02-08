import logging
import os
from typing import Any, List

import asyncpg


app_logger = logging.getLogger('app')


class Database:
    def __init__(self):
        self.conn_string = os.getenv("CONNECTION_STRING")
        self.top_table = 'top_100'
        
    async def get_connection(self) -> asyncpg.Connection:
        app_logger.info("Connecting to Database")
        conn = await asyncpg.connect(self.conn_string)
        app_logger.info("Database was connected successfully")
        return conn

    async def _db_query(self, method: callable, query: str) -> Any:
        #Internal method for applying to the database 
        #and ensuring the connection is closed
        conn = await self.get_connection()
        try:
            data = await getattr(conn, method)(query)
            return data
        except Exception as ex:
            app_logger.error("DB Error", exc_info=True)
        finally:
            await conn.close()
            app_logger.info("Connection was closed")

    async def get_repos(self) -> List[dict]:
        app_logger.info("Getting top 100 repos from DB")
        data = await self._db_query(
            'fetch',
            """
                SELECT *
                FROM top_100
                ORDER BY stars DESC
            """
        )
        dicted_data = [dict(row) for row in data]
        return dicted_data
    
    async def update_repos(self, repos_list: List[dict]) -> None:
        app_logger.info("Updating top 100 table")
        
        #Marking positions
        sorted_list = sorted(repos_list, key=lambda x: x['stars'], reverse=True)
        for i, repo in enumerate(sorted_list, start=1):
            repo['position_cur'] = i
            repo['position_prev'] = i + 1
        
        last_in_top = sorted_list[99]

        #Preparing values tuples
        values_list = []
        for repo in sorted_list:
            values_list.append(tuple(value for _, value in repo.items()))
        
        query = f"""
            BEGIN;
                INSERT INTO {self.top_table}
                VALUES {','.join([str(values) for values in values_list])}
                ON CONFLICT (repo, "owner") DO UPDATE SET
                    position_cur=EXCLUDED.position_cur,
                    position_prev=EXCLUDED.position_prev,
                    stars=EXCLUDED.stars,
                    watchers=EXCLUDED.watchers,
                    open_issues=EXCLUDED.open_issues,
                    "language"=EXCLUDED."language";
                
                DELETE FROM {self.top_table}
                WHERE position_cur > 100;
            COMMIT;
        """
        await self._db_query('execute', query)
