"""
Tests for Odia (ଓଡ଼ିଆ) Speech & Clinical Language Conversion
"""

import pytest
from fastapi.testclient import TestClient
from disease_prediction.api.main import app
from disease_prediction.api.voice_service.odia_service import (
    convert_to_odia,
    is_odia_text,
    ODIA_CLINICAL_LEXICON
)

client = TestClient(app)

def test_is_odia_text():
    assert is_odia_text("ଜ୍ୱର") is True
    assert is_odia_text("ମୋର ମୁଣ୍ଡ ବିନ୍ଧୁଛି") is True
    assert is_odia_text("High fever since yesterday") is False
    assert is_odia_text("") is False

def test_convert_to_odia_lexicon():
    # Symptoms
    res = convert_to_odia("jwara")
    assert res == "ଜ୍ୱର"
    assert is_odia_text(res)

    res2 = convert_to_odia("fever")
    assert res2 == "ଜ୍ୱର"

    res3 = convert_to_odia("munda bindhuchi")
    assert res3 == "ମୁଣ୍ଡ ବିନ୍ଧୁଛି"

    res4 = convert_to_odia("mora munda bindhuchi")
    assert res4 == "ମୋର ମୁଣ୍ଡ ବିନ୍ଧୁଛି"

def test_convert_odia_endpoint():
    response = client.post("/api/voice/convert-odia", json={"text": "jwara"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["odia_text"] == "ଜ୍ୱର"
    assert data["is_odia"] is True

def test_convert_odia_empty():
    response = client.post("/api/voice/convert-odia", json={"text": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["odia_text"] == ""
