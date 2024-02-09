from datetime import date
from typing import Any, List

import asyncpg

from app.config import Settings
from app.logging import app_logger


class Database:
    def __init__(self):
        self.conn_string = Settings().connection_string
        self.top_table = Settings().top_table
        self.activity_table = Settings().activity_table
        
    async def _get_connection(self) -> asyncpg.Connection:
        app_logger.info("Connecting to Database")
        conn = await asyncpg.connect(self.conn_string)
        app_logger.info("Database was connected successfully")
        return conn

    async def _db_query(self, method: callable, query: str) -> Any:
        #Internal method for applying to the database 
        #and ensuring the connection is closed
        conn = await self._get_connection()
        try:
            data = await getattr(conn, method)(query)
            return data
        except Exception as ex:
            app_logger.error("DB Error", exc_info=True)
        finally:
            await conn.close()
            app_logger.info("Connection was closed")

    async def get_repos_top(self, sort_by: str="stars", order: str="desc") -> List[dict]:
        app_logger.info("Getting top 100 repos from DB")
        if sort_by == "position":
            query = f"""
                SELECT *
                FROM {self.top_table}
                ORDER BY position_cur {order}
                LIMIT 100
            """
        else:
            query = f"""
                SELECT *
                FROM {self.top_table}
                ORDER BY {sort_by} {order}
                LIMIT 100
            """
        
        data = await self._db_query('fetch', query)
        dicted_data = [dict(row) for row in data]
        return dicted_data
    
    async def update_repos(self, repos_list: List[dict]) -> None:
        app_logger.info("Updating top 100 table")
        
        #Marking positions
        sorted_list = sorted(repos_list, key=lambda x: x['stars'], reverse=True)
        for i, repo in enumerate(sorted_list, start=1):
            repo['position_cur'] = i
            repo['position_prev'] = i + 1

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
                
                DO
                $$
                DECLARE
                    repos_cursor CURSOR FOR 
                        SELECT repo, "owner", stars
                        FROM {self.top_table}
                        ORDER BY stars DESC;
                    repo_record RECORD;
                    counter INTEGER;
                BEGIN
                    counter := 1;
                    OPEN repos_cursor;
                    LOOP
                        FETCH NEXT FROM repos_cursor INTO repo_record;
                        EXIT WHEN NOT FOUND;
                        EXECUTE 'UPDATE {self.top_table} 
                            SET position_cur = $1, position_prev = $2
                            WHERE repo = $3 AND "owner" = $4'
                        USING counter, counter + 1, repo_record.repo, repo_record."owner";
                        counter := counter + 1;
                    END LOOP;
                    CLOSE repos_cursor;
                END;
                $$
                LANGUAGE PLPGSQL;

                DELETE FROM {self.top_table}
                WHERE position_cur > 100;
            COMMIT;
        """
        await self._db_query('execute', query)
    
    async def get_activity(self, repo: str, owner: str, since: date, until: date) -> List[dict]:
        app_logger.info(f"Getting activity of /{owner}/{repo} from {since} to {until}")
        query = f"""
            SELECT *
            FROM {self.activity_table}
            WHERE repo = '{repo}'
                AND "owner" = '{owner}'
                AND "date" BETWEEN '{since}' AND '{until}'
        """
        data = await self._db_query('fetch', query)
        dicted_data = [dict(row) for row in data]
        return dicted_data
    
    async def update_activity(self, activity_list: List[dict]) -> None:
        app_logger.info("Updating activity")
        values_list = []
        for activity in activity_list:
            values_list.append(
                f"('{activity['repo']}', '{activity['owner']}', \
                    '{activity['date']}', {activity['commits']}, {activity['authors']})"
            )
        
        query = f"""
            INSERT INTO {self.activity_table}
            VALUES {','.join([values for values in values_list])}
            ON CONFLICT ("repo", "owner", "date") DO UPDATE SET
                commits = EXCLUDED.commits,
                authors = EXCLUDED.authors;
        """
        await self._db_query('execute', query)


db = Database()
