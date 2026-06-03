import pytest
import io
import json
from unittest.mock import patch

from invoices.vision_service import VisionOCRService

def test_vision_ocr_service_initialization(app):
    with app.app_context():
        service = VisionOCRService()
        assert service.ai_provider in ["ollama", "gemini"]

def test_vision_ocr_mock_fallback(app):
    """Test the smart mock fallback when no real AI is available."""
    with app.app_context():
        service = VisionOCRService()
        # Force it not to call real AI
        service.ai_provider = "none"
        
        result = service.extract_invoice_data(b"fake_image_bytes", "test.jpg", "image/jpeg")
        
        assert "number" in result
        assert "seller_mst" in result
        assert result["total_amount"] == 11000000
        assert result["is_vision_extracted"] is True
        assert result["filename"] == "test.jpg"

def test_api_vision_upload_unauthorized(client):
    """Ensure endpoint is protected."""
    response = client.post("/api/invoices/vision-upload")
    assert response.status_code == 401

def test_api_vision_upload_missing_file(client, logged_in_client):
    """Ensure it handles missing files."""
    response = logged_in_client.post("/api/invoices/vision-upload")
    assert response.status_code == 400
    assert "No file uploaded" in response.get_json()["error"]

def test_api_vision_upload_invalid_extension(client, logged_in_client):
    """Ensure it validates file extensions."""
    data = {
        'file': (io.BytesIO(b"fake content"), 'test.txt')
    }
    response = logged_in_client.post("/api/invoices/vision-upload", data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "Only JPG, PNG, and PDF files are supported" in response.get_json()["error"]

@patch('invoices.vision_service.VisionOCRService.extract_invoice_data')
def test_api_vision_upload_success(mock_extract, client, logged_in_client):
    """Test successful image upload and data extraction."""
    mock_extract.return_value = {
        "number": "0001234",
        "total_amount": 5500000,
        "is_vision_extracted": True
    }
    
    data = {
        'file': (io.BytesIO(b"fake image content"), 'invoice.jpg')
    }
    response = logged_in_client.post("/api/invoices/vision-upload", data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["status"] == "success"
    assert res_data["data"]["number"] == "0001234"
    assert res_data["data"]["is_vision_extracted"] is True
    
    # Verify mock was called
    mock_extract.assert_called_once()
