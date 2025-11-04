import io


def test_document_scoped_retrieval(client, sample_text_file):
    """Test that document_id parameter limits retrieval to specified document."""
    
    # Upload first document
    file_content1, filename1 = sample_text_file
    data1 = {'file': (file_content1, 'doc1.txt')}
    resp1 = client.post('/upload', data=data1, content_type='multipart/form-data')
    assert resp1.status_code == 201
    doc1_id = resp1.get_json()['document_id']
    
    # Upload second document with different content
    file_content2 = io.BytesIO(b"This is a completely different document about Python programming and web development.")
    data2 = {'file': (file_content2, 'doc2.txt')}
    resp2 = client.post('/upload', data=data2, content_type='multipart/form-data')
    assert resp2.status_code == 201
    doc2_id = resp2.get_json()['document_id']
    
    # Query with document_id filter for first document
    ask_resp = client.post('/ask', json={
        'question': 'What does the document talk about?',
        'document_id': doc1_id
    })
    assert ask_resp.status_code == 200
    ask_json = ask_resp.get_json()
    
    # Verify sources only come from first document
    sources = ask_json.get('sources', [])
    if sources:
        for source in sources:
            # Check if source has document_id (retrieval source) or path (fallback source)
            if 'document_id' in source:
                assert source['document_id'] == doc1_id, f"Expected {doc1_id}, got {source['document_id']}"
            elif 'path' in source:
                # For fallback sources, check the path contains the doc id
                assert doc1_id in source['path'], f"Expected {doc1_id} in path {source['path']}"
