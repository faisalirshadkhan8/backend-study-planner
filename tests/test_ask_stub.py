def test_ask_stub_before_upload(client):
    resp = client.post('/ask', json={'question': 'Hello there'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'answer' in data
    assert 'sources' in data and isinstance(data['sources'], list)
    assert 'meta' in data
