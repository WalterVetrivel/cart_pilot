import io

from docx import Document


def _docx_bytes(*lines: str) -> bytes:
    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_requires_auth(client):
    assert client.post("/api/parse", data={"text": "milk"}).status_code == 401


def test_parse_text(dev_client, fake_parser):
    res = dev_client.post("/api/parse", data={"text": "thakkali 1 kg\natta 5kg"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["source_type"] == "text"
    assert body["detected_language"] == "mixed"
    assert [i["canonical_name"] for i in body["items"]] == ["tomato", "wheat flour", "dragon fruit"]
    assert fake_parser.calls == [{"text": "thakkali 1 kg\natta 5kg", "blob": None, "mime_type": None}]

    tomato, atta, dragon = body["items"]
    assert body["matches"][tomato["id"]] and body["matches"][atta["id"]]
    assert body["matches"][dragon["id"]] == []


def test_parse_image_sends_bytes(dev_client, fake_parser):
    res = dev_client.post("/api/parse", files={"file": ("list.jpg", b"\xff\xd8fake", "image/jpeg")})
    assert res.status_code == 200
    assert res.json()["source_type"] == "image"
    assert fake_parser.calls[0]["blob"] == b"\xff\xd8fake"
    assert fake_parser.calls[0]["mime_type"] == "image/jpeg"


def test_parse_browser_recording_strips_codec(dev_client, fake_parser):
    res = dev_client.post("/api/parse", files={"file": ("voice.webm", b"webm", "audio/webm;codecs=opus")})
    assert res.status_code == 200
    assert res.json()["source_type"] == "audio"
    assert fake_parser.calls[0]["mime_type"] == "audio/webm"


def test_parse_pdf_and_extension_fallback(dev_client, fake_parser):
    res = dev_client.post("/api/parse", files={"file": ("list.pdf", b"%PDF-1.4", "application/octet-stream")})
    assert res.status_code == 200
    assert res.json()["source_type"] == "pdf"
    assert fake_parser.calls[0]["mime_type"] == "application/pdf"


def test_parse_docx_is_converted_to_text(dev_client, fake_parser):
    data = _docx_bytes("Rice 5 kg", "Toor dal 1 kg")
    res = dev_client.post("/api/parse", files={"file": ("list.docx", data, "application/octet-stream")})
    assert res.status_code == 200
    assert res.json()["source_type"] == "docx"
    call = fake_parser.calls[0]
    assert call["blob"] is None and call["mime_type"] is None
    assert call["text"] == "Rice 5 kg\nToor dal 1 kg"


def test_parse_rejects_unsupported_and_empty(dev_client):
    res = dev_client.post("/api/parse", files={"file": ("list.csv", b"a,b", "text/csv")})
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "unsupported_file"
    res = dev_client.post("/api/parse", data={"text": "   "})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "empty_list"


def test_parse_rejects_large_files(dev_client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    res = dev_client.post("/api/parse", files={"file": ("big.png", b"0" * (1024 * 1024 + 1), "image/png")})
    assert res.status_code == 413


def test_parser_failure_is_a_clean_502(dev_client, fake_parser):
    async def boom(*_):
        raise RuntimeError("model down")

    fake_parser.parse = boom
    res = dev_client.post("/api/parse", data={"text": "milk"})
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "parse_failed"
    assert "RuntimeError: model down" in res.json()["error"]["message"]


def test_get_and_update_list(dev_client):
    created = dev_client.post("/api/parse", data={"text": "x"}).json()
    list_id = created["list_id"]

    fetched = dev_client.get(f"/api/lists/{list_id}").json()
    assert fetched["items"] == created["items"]

    items = created["items"][:1]
    items[0]["quantity"] = 3
    items.append({"canonical_name": "milk", "original_text": "milk", "unit": "l", "quantity": 2, "optional": True})
    res = dev_client.put(f"/api/lists/{list_id}", json={"items": items, "detected_language": "en"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert [i["canonical_name"] for i in body["items"]] == ["tomato", "milk"]
    assert body["items"][1]["optional"] is True
    milk_id = body["items"][1]["id"]
    assert all(c["qty"] == 2 for c in body["matches"][milk_id] if c["pack_unit"] == "l" and c["pack_size"] == 1)
    assert dev_client.get(f"/api/lists/{list_id}").json()["items"][0]["quantity"] == 3


def test_missing_list_is_404(dev_client):
    assert dev_client.get("/api/lists/nope").status_code == 404
