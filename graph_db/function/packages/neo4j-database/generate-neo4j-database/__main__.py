"""Base Importer using S3"""
import os
import pickle
from datetime import datetime
from bson import json_util
from neo4j import GraphDatabase
import boto3
import requests


class S3Importer:
    """Import from Digital Ocean"""

    def __init__(self):
        self.session = boto3.session.Session()
        self.env_pocas = os.getenv("POCAS_ENV", "prod")
        self.region = os.getenv("SPACES_REGION")
        self.client = self.session.client(
            "s3",
            endpoint_url=f"https://{self.region}.digitaloceanspaces.com",
            region_name=self.region,  # Use the region in your endpoint.
            aws_access_key_id=os.getenv("SPACES_KEY_ID"),
            # Access key pair. You can create access key pairs using the control panel or API.
            aws_secret_access_key=os.getenv("SPACES_SECRET"),
        )

    def get_object(self, path, space="mongodb"):
        """Get Object from path"""
        payload = self.client.get_object(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Key=f"{self.env_pocas}/{space}/{path}",
        )
        data = pickle.loads(payload["Body"].read())
        return data

    def find_recent(self, space="mongodb"):
        """Find most recent directory in bucket"""
        paginator = self.client.get_paginator("list_objects")
        dates = []
        result = paginator.paginate(
            Bucket=os.getenv("SPACES_BUCKET", "mhpportal"),
            Delimiter="/",
            Prefix=f"{self.env_pocas}/{space}/",
        )
        for prefix in result.search("CommonPrefixes"):
            folder = datetime.strptime(prefix.get("Prefix").split("/")[-2], "%m_%d_%Y")
            dates.append(folder)
        max_date = max(dates)
        return datetime.strftime(max_date, "%m_%d_%Y")


class BaseNeoImporter:
    """Base Neo4j Importer"""

    def __init__(self, node_type="Services", space="mongodb"):
        self.__host = os.getenv("NEO_HOST", "0.0.0.0")
        self.__port = os.getenv("NEO_PORT", "7687")
        self.__user = os.getenv("NEO_USER", "neo4j")
        self.__pwd = os.getenv("NEO_PWD")
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
        if self.space_type == "mongo":
            self.get_mongo_data()
        elif self.space_type == "api":
            self.get_api_data()
        self.get_tags()
        self.import_graph()
        self.close()


"""Import API responses to Neo4j"""


class API2NeoImporter(BaseNeoImporter):
    """MHP-API to Neo4j Importer"""

    def __init__(self, node_type="Service", api_path="https://mhpportal.app"):
        super().__init__(node_type)
        self.api_path = api_path

    def get_api_data(self):
        """Get API data"""
        resp = requests.get(
            f"{self.api_path}/api/v1/{self.node_type.lower()}", timeout=10
        )
        data = resp.json()
        for d in data[self.node_type.lower()]:
            if "id" in d:
                d["mongo_id"] = d["id"]
            if "general_topic" in d:
                d["main_tag"] = d["general_topic"]
            if "question" in d:
                d["name"] = d["question"]
            self.data.append(d)

    def run(self):
        """Run Neo4j Importer"""
        self.get_api_data()
        self.get_tags()
        self.import_graph()
        self.close()


class Analytics2NeoImporter(BaseNeoImporter):
    """MHP-API Analytics to Neo4j Importer"""

    def __init__(self, node_type="User", api_path="https://mhpportal.app"):
        super().__init__(node_type)
        self.api_path = api_path

    def get_api_data(self):
        """Get API data"""
        zip_codes_url = f"{self.api_path}/api/v1/platform/zip_codes"
        data_zip_url = f"{self.api_path}/api/v1/platform/data/%s"
        resp = requests.get(zip_codes_url)
        z_c = resp.json()
        json_data = []
        for z in z_c:
            resp = requests.get(data_zip_url % z["id"])
            json_data = json_data + resp.json()
        self.data = json_data

    def import_graph(self):
        """Import Data to Neo4j"""
        nodes_written = 0
        rels = 0
        with self.driver.session() as session:
            for d in self.data:
                session.execute_write(self._create_node_message, message=d)
                nodes_written += 1
                for service in d["top_services"]:
                    session.execute_write(
                        self.__create_node_tag_rel_user, message=d, service=service
                    )
                    rels += 1
        print({"nodes": nodes_written, "rel": rels})

    def __create_node_tag_rel_user(self, tx, message, service):
        """Create a relatioship with user to Service"""
        result = tx.run(
            """
            MATCH
              (a:%s {id: $message.name}),
              (t:Services {id: $service})
            MERGE (a)-[r:HIT]->(t)
            RETURN a
            """
            % self.node_type,
            message=message,
            service=service,
        )
        return result.single()[0]

    def _create_node_message(self, tx, message):
        """Create a standard Node"""
        result = tx.run(
            """
            MERGE (t:%s {id: $message.name})
            ON CREATE
                  SET t.created = timestamp()
                  SET t.zip_code = $message.zip_code
                  SET t.dob = $message.dob
                  SET t.time = $message.time
            RETURN t.name, t.created
            """
            % self.node_type,
            message=message,
        )
        return result.single()[0]

    def run(self):
        """Run Neo4j Importer"""
        self.get_api_data()
        self.import_graph()
        self.close()


def main():
    neo = BaseNeoImporter(node_type="Services")
    with neo.driver.session() as session:
        session.run("""MATCH (n) DETACH DELETE n;""")

    api_path = "https://mhpportal.app"
    print(f"Using API: {api_path}")
    q = API2NeoImporter(node_type="Questions", api_path=api_path)
    print("Questions Data \n")
    q.run()
    print(q.data[0])
    print(q.tags)

    s = API2NeoImporter(node_type="Services", api_path=api_path)
    print("\nServices Data \n")
    s.run()
    print(s.data[0])
    print(s.tags)

    a = Analytics2NeoImporter()
    a.run()
