from google.cloud import bigquery
from google.api_core import exceptions

# --- Configuration ---
# Make sure these match your GCP project and BigQuery dataset
PROJECT_ID = "ccibt-hack25ww7-721"
DATASET_ID = "client_data"
#TABLE_TO_TEST = "user_map"  # Change this to 'reports_plan' to test the other table
TABLE_TO_TEST = "report_plan"


def test_connection_and_query():
    """
    Initializes the BigQuery client, runs a simple query, and prints the results.
    """
    print("Attempting to connect to BigQuery...")
    try:
        # When running locally, this uses your gcloud Application Default Credentials.
        client = bigquery.Client(project=PROJECT_ID)
        print("BigQuery client initialized successfully.")
    except Exception as e:
        print(f"Error: Could not initialize BigQuery client.\nDetails: {e}")
        print(
            "\nPlease ensure you have authenticated by running 'gcloud auth application-default login'"
        )
        return

    # Construct a simple SQL query to fetch a few rows from the table.
    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_TO_TEST}`
        LIMIT 5
    """

    print(f"\nExecuting query:\n---\n{query}\n---")

    try:
        # Execute the query and get the results
        results = list(client.query(query).result())

        if not results:
            print(f"Query executed successfully, but the table '{TABLE_TO_TEST}' appears to be empty.")
        else:
            print("Query successful! Here are the first 5 rows:")
            for row in results:
                print(dict(row))

    except exceptions.NotFound as e:
        print(f"\nError: The table or dataset was not found.\nDetails: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during the query.\nDetails: {e}")

if __name__ == "__main__":
    test_connection_and_query()