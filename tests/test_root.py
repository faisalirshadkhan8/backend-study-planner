def test_root_index(client):
    resp = client.get('/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('name') == 'basic-rag-chatbot-backend'
    assert isinstance(data.get('endpoints'), list)
