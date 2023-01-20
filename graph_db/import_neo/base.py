"""Base Importer using S3"""
# pylint: disable=C0209
import os
from bson import json_util
from neo4j import GraphDatabase
import pandas as pd
from s3_client import S3Importer


class BaseNeoImporter:
    """Base Neo4j Importer"""

    def __init__(self, node_type="Services"):
        self.__host = os.getenv("NEO_HOST", "0.0.0.0")
        self.__port = os.getenv("NEO_PORT", "7687")
        self.__user = os.getenv("NEO_USER", "neo4j")
        self.__pwd = os.getenv("NEO_PWD")
        self.driver = GraphDatabase.driver(
            f"bolt://{self.__host}:{self.__port}", auth=(self.__user, self.__pwd)
        )
        self.data = []
        self.tags = []
        if node_type not in ["Services", "Questions", "User"]:
            raise ValueError(
                "Value of node_type should be either: Services, Users, or Questions!"
            )
        self.node_type = node_type

    def close(self):
        """Close Neo4j Driver"""
        self.driver.close()

    def get_mongo_data(self):
        """Get MongoDB backup data from S3 Bucket"""
        # get recent space
        # download data from pickle
        space = S3Importer()
        date_max = space.find_recent_mongo()
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
        d = pd.DataFrame(self.data)
        g_t = d.main_tag.dropna().unique().tolist()
        tags = d.tags.explode().dropna().unique().tolist()
        values = set(g_t + tags)
        values = sorted(values)
        self.tags = values

    def import_graph(self):
        """Import Data to Neo4j"""
        tags_written = 0
        nodes_written = 0
        tagged_rels = 0
        with self.driver.session() as session:
            for tag in self.tags:
                session.execute_write(self._merge_tags, tag)
                tags_written += 1
            for d in self.data:
                session.execute_write(self._create_node, message=d)
                nodes_written += 1
                for tag in d["tags"]:
                    session.execute_write(
                        self._create_node_tag_rel, tag=tag, mongo_id=d["mongo_id"]
                    )
                    tagged_rels += 1
                session.execute_write(
                    self._create_node_tag_rel, tag=d["main_tag"], mongo_id=d["mongo_id"]
                )
                tagged_rels += 1
        print({"tag_nodes": tags_written, "nodes": nodes_written, "rel": tagged_rels})

    @staticmethod
    def _merge_tags(tx, tag):
        """Merge Tags into Database"""
        result = tx.run(
            """
                MERGE (t:Tags {name: $tag})
                ON CREATE
                  SET t.created = timestamp()
                RETURN t.name, t.created
                """,
            tag=tag,
        )
        return result

    def _create_node(self, tx, message):
        """Create a standard Node"""
        result = tx.run(
            """
            MERGE (t:%s {id: $message.mongo_id})
            ON CREATE
                  SET t.created = timestamp()
                  SET t.name = $message.name
                  SET t.lat = $message.lat
                  SET t.lon = $message.lon
                  SET t.zip_code = $message.zip_code
                  SET t.city = $message.city
            RETURN t.name, t.created
            """
            % self.node_type,
            message=message,
        )
        return result.single()[0]

    def _create_node_tag_rel(self, tx, tag, mongo_id):
        """Create TAGGED relationship"""
        result = tx.run(
            """
            MATCH
              (a:%s {id: $mongo_id}),
              (t:Tags {name: $tag})
            MERGE (a)-[r:TAGGED]->(t)
            RETURN a
            """
            % self.node_type,
            tag=tag,
            mongo_id=mongo_id,
        )
        return result

    def run(self):
        """Run Neo4j Importer"""
        self.get_mongo_data()
        self.get_tags()
        self.import_graph()
        self.close()
