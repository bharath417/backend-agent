from unittest.mock import MagicMock, PropertyMock

def test_webhook_get_report_entitled(client, mock_bq_client):
    """
    Tests the /webhook endpoint for a user who IS entitled.
    """
    # Mock the return value of the BigQuery query result
    mock_result = MagicMock()
    type(mock_result).entitled = PropertyMock(return_value=True)
    mock_bq_client.query.return_value.result.return_value = iter([mock_result])

    response = client.post("/webhook", json={
        "queryResult": {
            "intent": {"displayName": "GetReport"},
            "parameters": {"user_id": "test_user", "feature": "test_feature"}
        }
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert "You have access" in json_data["fulfillmentText"]
    assert "https://your-reporting-system.com/reports/test_feature/test_user" in json_data["fulfillmentText"]

def test_webhook_get_report_not_entitled(client, mock_bq_client):
    """
    Tests the /webhook endpoint for a user who is NOT entitled.
    """
    mock_result = MagicMock()
    type(mock_result).entitled = PropertyMock(return_value=False)
    type(mock_result).required_plan = PropertyMock(return_value="premium")
    mock_bq_client.query.return_value.result.return_value = iter([mock_result])

    response = client.post("/webhook", json={
        "queryResult": {
            "intent": {"displayName": "GetReport"},
            "parameters": {"user_id": "test_user", "feature": "premium_feature"}
        }
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert "This feature requires the 'premium' plan" in json_data["fulfillmentText"]

def test_webhook_upgrade_plan_success(client, mock_bq_client):
    """
    Tests the /webhook endpoint for a successful plan upgrade.
    """
    # Mock the DML statement result
    mock_query_job = MagicMock()
    type(mock_query_job).num_dml_affected_rows = PropertyMock(return_value=1)
    mock_bq_client.query.return_value = mock_query_job

    response = client.post("/webhook", json={
        "queryResult": {
            "intent": {"displayName": "UpgradePlan"},
            "parameters": {"user_id": "test_user", "new_plan": "premium"}
        }
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert "successfully upgraded to the 'premium' plan" in json_data["fulfillmentText"]

def test_webhook_upgrade_plan_user_not_found(client, mock_bq_client):
    """
    Tests the /webhook endpoint for a plan upgrade where the user is not found.
    """
    mock_query_job = MagicMock()
    type(mock_query_job).num_dml_affected_rows = PropertyMock(return_value=0)
    mock_bq_client.query.return_value = mock_query_job

    response = client.post("/webhook", json={
        "queryResult": {
            "intent": {"displayName": "UpgradePlan"},
            "parameters": {"user_id": "non_existent_user", "new_plan": "premium"}
        }
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert "We could not find your user account to upgrade" in json_data["fulfillmentText"]

def test_webhook_missing_user_id(client):
    """
    Tests that a helpful message is returned if user_id is missing.
    """
    response = client.post("/webhook", json={
        "queryResult": {
            "intent": {"displayName": "GetReport"},
            "parameters": {"feature": "test_feature"} # Missing user_id
        }
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert "Sorry, I could not identify the user." in json_data["fulfillmentText"]

def test_webhook_unknown_intent(client):
    """
    Tests the response for an unhandled intent.
    """
    response = client.post("/webhook", json={
        "queryResult": {
            "intent": {"displayName": "UnknownIntent"},
            "parameters": {"user_id": "test_user"}
        }
    })

    assert response.status_code == 200
    json_data = response.get_json()
    assert "Sorry, I don't know how to handle the intent: UnknownIntent" in json_data["fulfillmentText"]
