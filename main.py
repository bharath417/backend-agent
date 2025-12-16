import os
from flask import Flask, request, jsonify
from google.cloud import bigquery

app = Flask(__name__)

# Initialize the BigQuery client.
# When running on Cloud Run, this will automatically use the
# associated service account for authentication.
try:
    project_id = "ccibt-hack25ww7-721"
    bq_client = bigquery.Client(pfroject=project_id)
    dataset_id = "client_data" # Replace with your dataset ID
except Exception as e:
    # Handle exceptions during client initialization, e.g., credentials not found
    # when running locally without being authenticated.
    print(f"Error initializing BigQuery client: {e}")
    bq_client = None
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    dataset_id = "client_data"


@app.route("/", methods=["GET"])
def health_check():
    """
    Health check endpoint to confirm the service is running.
    """
    return jsonify({"status": "ok"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Main webhook endpoint to handle requests from Dialogflow.
    """
    if not bq_client:
        return jsonify({"fulfillmentText": "Error: BigQuery client is not initialized."}), 500

    req = request.get_json(force=True)
    intent_name = req.get("queryResult", {}).get("intent", {}).get("displayName")
    parameters = req.get("queryResult", {}).get("parameters", {})
    user_id = parameters.get("user_id")

    if not user_id:
        return jsonify({"fulfillmentText": "Sorry, I could not identify the user."})

    response_data = {}

    if intent_name == "GetReport":
        feature = parameters.get("feature") # This should match the parameter name in Dialogflow
        response_data = handle_get_report(user_id, feature)
    elif intent_name == "UpgradePlan":
        new_plan = parameters.get("new_plan")
        response_data = handle_upgrade_plan(user_id, new_plan)
    else:
        response_data = {"fulfillmentText": f"Sorry, I don't know how to handle the intent: {intent_name}"}

    return jsonify(response_data)

def check_entitlement(user_id: str, requested_feature: str) -> dict:
    """
    Checks if a user is entitled to a specific feature by querying BigQuery.
    """
    query = f"""
    -- Unpivot the report_plan table to normalize it
    WITH Entitlements AS (
      SELECT Reports_Services, Plan
      FROM `{project_id}.{dataset_id}.report_plan`
      UNPIVOT(HasAccess FOR Plan IN (Bronze, Silver, Gold))
      WHERE HasAccess IS TRUE -- Assumes TRUE/non-null indicates access
    )
    -- Check if the user's plan is in the list of entitled plans for the feature
    SELECT EXISTS (
      SELECT 1
      FROM `{project_id}.{dataset_id}.user_map` um
      JOIN Entitlements e ON um.Plan = e.Plan
      WHERE um.User_ID = @user_id AND e.Reports_Services = @requested_feature
    ) as entitled
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
            bigquery.ScalarQueryParameter("requested_feature", "STRING", requested_feature),
        ]
    )

    try:
        query_job = bq_client.query(query, job_config=job_config)
        results = query_job.result()
        row = next(results)

        if row.entitled:
            return {"entitled": True, "message": "Access granted.", "suggested_plan": None}
        # If not entitled, we don't know the required plan from this query, so give a generic message.
        return {
            "entitled": False,
            "message": "This feature is not included in your current plan. Please contact support to upgrade.",
            "suggested_plan": None,
        }
    except StopIteration:
         # This case handles when the user or feature doesn't exist in the tables
        return {
            "entitled": False,
            "message": "We could not verify your subscription plan for this feature.",
            "suggested_plan": None,
        }
    except Exception as e:
        print(f"Error in check_entitlement: {e}")
        return {"entitled": False, "message": "An error occurred while checking entitlements.", "suggested_plan": None}

def handle_get_report(user_id: str, feature: str) -> dict:
    """
    Handles the 'GetReport' intent by checking entitlement and responding.
    """
    if not feature:
        return {"fulfillmentText": "Please specify which report you would like to access."}

    entitlement = check_entitlement(user_id, feature)
    if entitlement["entitled"]:
        # In a real application, you would generate a secure, short-lived URL
        report_url = f"https://your-reporting-system.com/reports/{feature}/{user_id}"
        message = f"You have access. Here is your report for '{feature}': {report_url}"
        return {"fulfillmentText": message}
    else:
        return {"fulfillmentText": entitlement["message"]}

def handle_upgrade_plan(user_id: str, new_plan: str) -> dict:
    """
    Handles the 'UpgradePlan' intent by updating the user's subscription in BigQuery.
    """
    if not new_plan:
        return {"fulfillmentText": "Please specify which plan you would like to upgrade to."}

    query = f"""
        UPDATE `{project_id}.{dataset_id}.user_map`
        SET Plan = @new_plan
        WHERE User_ID = @user_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("new_plan", "STRING", new_plan),
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
        ]
    )

    try:
        query_job = bq_client.query(query, job_config=job_config)
        query_job.result()  # Wait for the job to complete

        if query_job.num_dml_affected_rows > 0:
            message = f"Your subscription has been successfully upgraded to the '{new_plan}' plan."
        else:
            message = "We could not find your user account to upgrade. Please contact support."

        return {"fulfillmentText": message}
    except Exception as e:
        print(f"Error in handle_upgrade_plan: {e}")
        return {"fulfillmentText": "An error occurred while upgrading your plan. Please try again later."}

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
