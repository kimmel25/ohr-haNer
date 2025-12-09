import pytest
from fastapi.testclient import TestClient
from api_server_v7 import app

client = TestClient(app)

@pytest.fixture
def mock_analyze_query(mocker):
    """Mock the analyze_query function."""
    return mocker.patch("user_validation.analyze_query")

@pytest.fixture
def mock_apply_user_selection(mocker):
    """Mock the apply_user_selection function."""
    return mocker.patch("user_validation.apply_user_selection")

@pytest.fixture
def mock_get_dictionary(mocker):
    """Mock the get_dictionary function."""
    return mocker.patch("tools.word_dictionary.get_dictionary")

def test_confirm_selection_high_confidence(mock_analyze_query, mock_apply_user_selection, mock_get_dictionary):
    """Test the confirm_selection endpoint with high-confidence results."""
    # Mock WordValidation objects
    word_val_1 = type("WordValidation", (object,), {"best_match": "חזקת", "original": "chezkas"})()
    word_val_2 = type("WordValidation", (object,), {"best_match": "מרה", "original": "mara"})()
    word_val_3 = type("WordValidation", (object,), {"best_match": "קמא", "original": "kama"})()
    
    # Mock the analyze_query response with correct structure
    mock_analyze_query.return_value = type("ValidationResult", (object,), {
        "normalized": "chezkas mara kama",
        "word_validations": [word_val_1, word_val_2, word_val_3],
        "uncertain_word_indices": [1],  # "mara" is uncertain (index 1)
    })()

    # Mock the apply_user_selection response
    mock_apply_user_selection.return_value = "מרה"

    # Mock the dictionary add_entry method
    mock_get_dictionary.return_value.add_entry = lambda *args, **kwargs: None

    # Send the request
    response = client.post(
        "/decipher/confirm",
        json={
            "original_query": "chezkas mara kama",
            "selection_index": 1,
            "selected_hebrew": "מרה"
        }
    )

    # Assert the response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["hebrew_term"] == "חזקת מרה קמא"
    assert "Got it! Using: חזקת מרה קמא" in data["message"]