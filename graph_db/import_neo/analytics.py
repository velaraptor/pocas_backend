"""Import API Analytics to Neo4j"""
import requests
from import_neo.base import BaseNeoImporter


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
