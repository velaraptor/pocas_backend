"""MHP-API to Neo4j Importer"""
import os
from datetime import datetime
import requests
from .neo import BaseNeoImporter


class API2NeoImporter(BaseNeoImporter):
    """MHP-API to Neo4j Importer"""

    def __init__(
        self,
        node_type="Service",
        api_path="https://mhpportal.app",
        static_date=int(datetime.now().timestamp()),
    ):
        super().__init__(node_type=node_type, static_date=static_date)
        self.api_path = api_path

    def get_api_data(self):
        """Get API data"""
        resp = requests.get(
            f"{self.api_path}/api/v1/{self.node_type.lower()}", timeout=10
        )
        data = resp.json()
        key = self.node_type.lower()
        if self.node_type.lower() == "questions":
            key = "items"

        for d in data[key]:
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

    def __init__(
        self,
        node_type="User",
        api_path="https://mhpportal.app",
        static_date=int(datetime.now().timestamp()),
    ):
        super().__init__(node_type=node_type, static_date=static_date)
        self.api_path = api_path

    def get_api_data(self):
        """Get API data"""
        s = requests.Session()
        s.auth = (
            os.getenv("API_USER"),
            os.getenv("API_PASS"),
        )
        zip_codes_url = f"{self.api_path}/api/v1/platform/zip_codes"
        data_zip_url = f"{self.api_path}/api/v1/platform/data/%s"
        question_url = f"{self.api_path}/api/v1/questions"
        resp = s.get(zip_codes_url)
        z_c = resp.json()
        json_data = []
        resp_question = s.get(question_url)
        question_data = resp_question.json().get("items")
        question_data = sorted(question_data, key=lambda d: d["id"])

        # TODO: map answers to sorted questions id and merge nodes with that! only ones that are 1s (answered)
        for z in z_c:
            resp = s.get(data_zip_url % z["id"])
            json_data = json_data + resp.json()
        for data in json_data:
            data["questions"] = question_data[data["answers"]]
        self.data = json_data

    def import_graph(self):
        """Import Data to Neo4j"""
        nodes_written = 0
        with self.driver.session() as session:
            session.execute_write(self._create_node_message, message=self.data)
            nodes_written += len(self.data)
            session.execute_write(self.__create_node_tag_rel_user, message=self.data)
            session.execute_write(self.__create_node_questions_rel, message=self.data)
        print({"nodes": nodes_written})

    def __create_node_tag_rel_user(self, tx, message):
        """Create a relationship with user to Service"""
        result = tx.run(
            """
            UNWIND $message as message
            UNWIND message.top_services as service
            MATCH
              (a:%s {id: message.name, date: $date}),
              (t:Services {id: service, date: $date})
            MERGE (a)-[r:HIT]->(t)
            RETURN a
            """
            % self.node_type,
            message=message,
            date=self.date,
        )
        return result

    def __create_node_questions_rel(self, tx, message):
        """Create a relationship with user to Service"""
        result = tx.run(
            """
            UNWIND $message as message
            UNWIND message.questions as question
            MATCH
              (a:%s {id: message.name, date: $date}),
              (t:Questions {id: question.id, date: $date})
            MERGE (a)-[r:REC]->(t)
            RETURN a
            """
            % self.node_type,
            message=message,
            date=self.date,
        )
        return result

    def _create_node_message(self, tx, message):
        """Create a standard Node"""
        result = tx.run(
            """
            UNWIND $message as message
            MERGE (t:%s {id: message.name, date: $date})
            ON CREATE
                  SET t.created = timestamp()
                  SET t.zip_code = message.zip_code
                  SET t.dob = message.dob
                  SET t.time = message.time
                  SET t.answers = message.answers
            RETURN t.name, t.created
            """
            % self.node_type,
            message=message,
            date=self.date,
        )
        return result

    def run(self):
        """Run Neo4j Importer"""
        self.get_api_data()
        self.import_graph()
        self.close()
