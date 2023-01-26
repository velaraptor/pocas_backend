"""Base Neo4j API"""
import os
from neo4j import GraphDatabase


class BaseNeo:
    """Base Neo4j API"""

    def __init__(self):
        self.__host = os.getenv("NEO_HOST", "0.0.0.0")
        self.__port = os.getenv("NEO_PORT", "7687")
        self.__user = os.getenv("NEO_USER", "neo4j")
        self.__pwd = os.getenv("NEO_PWD")
        self.driver = GraphDatabase.driver(
            f"bolt://{self.__host}:{self.__port}", auth=(self.__user, self.__pwd)
        )
        self.max_date = None

    def find_max_date(self):
        """Find Import Max Date"""

        with self.driver.session() as session:
            data = session.run(
                """
                MATCH (n:Import)
                RETURN MAX(n.date) as date
                """
            )
            self.max_date = data.data()[0]["date"]

    def run_services_disconnected(self):
        """Get Tags disconnected to Questions"""
        with self.driver.session() as session:
            data = session.run(
                """
                    MATCH (n:Services)-[:TAGGED]->(n1:Tags)
                WHERE NOT (n1)-[:TAGGED]-(:Questions)
                // Young Adult Resources is tied by Age Question
                      AND n1.name <> 'Young Adult Resources'
                      AND NOT (n)-[:TAGGED]-(n1)-[:TAGGED]-(:Questions)
                      AND n.date = n1.date = $max_date
                RETURN n.id as service_id, n.name as service, COLLECT(n1.name) as tags
                ORDER BY tags;
                """,
                max_date=self.max_date,
            )
            df = data.to_df().to_dict(orient="records")
            return df

    def run_tags_disconnected(self):
        """Get Services disconnected to Questions"""
        with self.driver.session() as session:
            data = session.run(
                """
                MATCH (n:Services)-[:TAGGED]->(n1:Tags)
                WHERE NOT (n1)-[:TAGGED]-(:Questions)
                // Young Adult Resources is tied by Age Question
                      AND n1.name <> 'Young Adult Resources'
                      AND n.date = n1.date = $max_date
                WITH n1.name as tags
                RETURN tags as name, COUNT(*) as value
                ORDER BY name;
                """,
                max_date=self.max_date,
            )
            tag = data.to_df().to_dict(orient="records")
            return tag

    def get_network(self):
        """
        Get network and in format for D3 Network Graph
        """
        with self.driver.session() as session:
            data = session.run(
                """
                MATCH p=(a)-[]->(b)
                WHERE LABELS(a) in [['Services'], ['Tags'], ['Questions']]
                AND LABELS(b) in [['Services'], ['Tags'], ['Questions']]
                AND a.date = b.date = $max_date
                WITH p unwind nodes(p) as n unwind relationships(p) as r
                WITH collect( distinct {id: ID( n), name: n.name, group: LABELS(n)[0] }) as nl,
                     collect( distinct {source: ID(startnode(r)), target: ID(endnode(r)) }) as rl
                RETURN {nodes: nl, links: rl} as payload
                """,
                max_date=self.max_date,
            )
            return data.data()[0]["payload"]
