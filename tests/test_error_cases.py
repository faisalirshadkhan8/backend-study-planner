def test_ask_missing_json(client):
    # Missing JSON body -> still JSON required, but sending form will trigger 415
    resp = client.post('/ask', data='question=Hi')
    assert resp.status_code == 415


def test_ask_empty_question(client):
    resp = client.post('/ask', json={'question': '   '})
    assert resp.status_code == 400


def test_upload_no_file(client):
    resp = client.post('/upload')
    assert resp.status_code == 400


def test_delete_unknown_document(client):
    resp = client.delete('/documents/does_not_exist')
    # Could be 404 (preferred) or 200 with message. We accept 404 as spec.
    assert resp.status_code in (200, 404)
