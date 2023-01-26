"""Main Function"""
from datetime import datetime
from utils.api2neo import API2NeoImporter, Analytics2NeoImporter


def main():
    """Main Function to import API data to Neo4j"""
    static_date = int(datetime.now().timestamp())
    api_path = "https://mhpportal.app"
    print(f"Import Node: {static_date}")
    print(f"Using API: {api_path}")
    q = API2NeoImporter(
        node_type="Questions", api_path=api_path, static_date=static_date
    )
    q.execute_date_node()
    print("Questions Data \n")
    q.run()
    print(q.data[0])
    print(q.tags)

    s = API2NeoImporter(
        node_type="Services", api_path=api_path, static_date=static_date
    )
    print("\nServices Data \n")
    s.run()
    print(s.data[0])
    print(s.tags)
    print("\nAnalytics Data \n")

    a = Analytics2NeoImporter(static_date=static_date)
    a.execute_date_node(finished=True)
    a.run()
