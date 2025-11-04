import io


def test_upload_then_ask_flow(client, sample_text_file):
    file_content, filename = sample_text_file
    data = {
        'file': (file_content, filename)
    }
    upload_resp = client.post('/upload', data=data, content_type='multipart/form-data')
    assert upload_resp.status_code == 201
    upload_json = upload_resp.get_json()
    assert 'document_id' in upload_json
    assert upload_json['chunks_indexed'] >= 1

    # Stats should reflect vectors
    stats_resp = client.get('/rag/stats')
    assert stats_resp.status_code == 200
    stats_json = stats_resp.get_json()
    total_vectors = stats_json.get('vector_store_stats', {}).get('total_vectors', 0)
    assert total_vectors >= 1

    # Ask a question using RAG context
    ask_resp = client.post('/ask', json={'question': 'What does the sample document talk about?'})
    assert ask_resp.status_code == 200
    ask_json = ask_resp.get_json()
    assert 'answer' in ask_json
    assert isinstance(ask_json.get('sources'), list)
