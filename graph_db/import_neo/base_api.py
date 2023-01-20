"""Import API responses to Neo4j"""
import requests
from import_neo.base import BaseNeoImporter


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
