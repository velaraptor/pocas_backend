"""Base Neo4j Importer"""
import os
from datetime import datetime
from bson import json_util
from neo4j import GraphDatabase
from .s3 import S3Importer


class BaseNeoImporter:
    """Base Neo4j Importer"""

    def __init__(
        self,
        node_type="Services",
        static_date=int(datetime.now().timestamp()),
        space="mongodb",
    ):
        self.__host = os.getenv("NEO_HOST", "0.0.0.0")
        self.__port = os.getenv("NEO_PORT", "7687")
        self.__user = os.getenv("NEO_USER", "neo4j")
        self.__pwd = os.getenv("NEO_PWD", "chris2023")
        self.driver = GraphDatabase.driver(
            f"bolt://{self.__host}:{self.__port}", auth=(self.__user, self.__pwd)
        )
        self.data = []
        self.tags = []
        self.space_type = space
        if node_type not in ["Services", "Questions", "User"]:
            raise ValueError(
                "Value of node_type should be either: Services, Users, or Questions!"
            )
        self.node_type = node_type
        self.date = static_date

    def close(self):
        """Close Neo4j Driver"""
        self.driver.close()

    def get_api_data(self):
        """Get API backup data from S3 Bucket"""
        space = S3Importer()
        date_max = space.find_recent("api")
        data = space.get_object(
            f"{date_max}/{self.node_type.lower()}/data.json.gzip", space="api"
        )
        for d_dict in data[self.node_type.lower()]:
            d_dict["mongo_id"] = d_dict["id"]
            if "general_topic" in d_dict:
                d_dict["main_tag"] = d_dict["general_topic"]
            if "question" in d_dict:
                d_dict["name"] = d_dict["question"]

            self.data.append(d_dict)

    def get_mongo_data(self):
        """Get MongoDB backup data from S3 Bucket"""
        # get recent space
        # download data from pickle
        space = S3Importer()
        date_max = space.find_recent("mongodb")
        data = space.get_object(
            f"{date_max}/results/{self.node_type.lower()}.json.gzip"
        )
        for d in data:
            d_dict = json_util.loads(d.decode("utf-8"))
            d_dict["mongo_id"] = str(d_dict["_id"])
            if "general_topic" in d_dict:
                d_dict["main_tag"] = d_dict["general_topic"]
            if "question" in d_dict:
                d_dict["name"] = d_dict["question"]

            self.data.append(d_dict)

    def get_tags(self):
        """Get Tags from POCAS API and get unique ones"""

        g_t = list({d["main_tag"] for d in self.data})
        tags = list({tag for d in self.data for tag in d["tags"]})
        values = set(g_t + tags)
        values = sorted(values)
        self.tags = values

    def import_graph(self):
        """Import Data to Neo4j"""
        tags_written = 0
        nodes_written = 0
        with self.driver.session() as session:
            session.execute_write(self._merge_tags, self.tags)
            tags_written += len(self.data)

            session.execute_write(self._create_node, message=self.data)
            nodes_written += len(self.data)

            session.execute_write(self._create_node_tag_rel, message=self.data)
            session.execute_write(self._create_node_tag_rel_main, message=self.data)
        print({"tag_nodes": tags_written, "nodes": nodes_written})

    def _merge_tags(self, tx, tags):
        """Merge Tags into Database"""
        result = tx.run(
            """
                UNWIND $tags AS tag
                MERGE (t:Tags {name: tag, date: $date})
                ON CREATE
                  SET t.created = timestamp()
                RETURN t.name, t.created
                """,
            tags=tags,
            date=self.date,
        )
        return result

    def execute_date_node(self, finished=False):
        """Execute Date Node"""
        with self.driver.session() as session:
            session.execute_write(self.create_date_node, finished=finished)

    def create_date_node(self, tx, finished=False):
        """Create Date Node"""
        result = tx.run(
            """
            MERGE (t:Import {date: $date})
            ON CREATE
                  SET t.created = timestamp()
                  SET t.finished = $finished
            RETURN t.date, t.created
            """,
            date=self.date,
            finished=finished,
        )
        return result

    def _create_node(self, tx, message):
        """Create a standard Node"""
        result = tx.run(
            """
            UNWIND $data AS message
            MERGE (t:%s {id: message.mongo_id, date: $date})
            ON CREATE
                  SET t.created = timestamp()
                  SET t.name = message.name
                  SET t.lat = message.lat
                  SET t.lon = message.lon
                  SET t.address = message.address
                  SET t.zip_code = message.zip_code
                  SET t.city = message.city
            RETURN t.name, t.created
            """
            % self.node_type,
            data=message,
            date=self.date,
        )
        return result

    def _create_node_tag_rel_main(self, tx, message):
        """Create TAGGED from main_tag relationship"""
        result = tx.run(
            """
            UNWIND $message as message
            MATCH
              (a:%s {id: message.mongo_id, date: $date}),
              (t:Tags {name: message.main_tag, date: $date})
            MERGE (a)-[r:TAGGED]->(t)
            RETURN a
            """
            % self.node_type,
            message=message,
            date=self.date,
        )
        return result

    def _create_node_tag_rel(self, tx, message):
        """Create TAGGED relationship"""
        result = tx.run(
            """
            UNWIND $message as message
            UNWIND message.tags as tag
            MATCH
              (a:%s {id: message.mongo_id, date: $date}),
              (t:Tags {name: tag, date: $date})
            MERGE (a)-[r:TAGGED]->(t)
            RETURN a
            """
            % self.node_type,
            message=message,
            date=self.date,
        )
        return result

    def run(self):
        """Run Neo4j Importer"""
        if self.space_type == "mongo":
            self.get_mongo_data()
        elif self.space_type == "api":
            self.get_api_data()
        self.get_tags()
        self.import_graph()
        self.close()
