"""
Test script to verify RAG chatbot setup
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 60)
print("RAG CHATBOT SETUP VERIFICATION")
print("=" * 60)

# 1. Check Python version
print(f"\n✓ Python version: {sys.version.split()[0]}")

# 2. Check required packages
print("\n📦 Checking Required Packages:")
required_packages = [
    'flask',
    'flask_cors',
    'pypdf',
    'faiss',
    'sentence_transformers',
    'google.generativeai',
    'python-dotenv',
]

missing = []
for pkg in required_packages:
    try:
        if pkg == 'python-dotenv':
            __import__('dotenv')
        else:
            __import__(pkg.replace('-', '_'))
        print(f"  ✓ {pkg}")
    except ImportError:
        print(f"  ✗ {pkg} - MISSING")
        missing.append(pkg)

if missing:
    print(f"\n⚠️  Missing packages: {', '.join(missing)}")
    print("Install with: pip install " + ' '.join(missing))
else:
    print("\n✓ All required packages installed")

# 3. Check environment variables
print("\n🔧 Environment Configuration:")
env_vars = {
    'LLM_PROVIDER': os.getenv('LLM_PROVIDER'),
    'GEMINI_API_KEY': '***' + os.getenv('GEMINI_API_KEY', '')[-4:] if os.getenv('GEMINI_API_KEY') else 'NOT SET',
    'DEFAULT_MODEL': os.getenv('DEFAULT_MODEL'),
    'CHUNK_SIZE': os.getenv('CHUNK_SIZE'),
    'TOP_K_RESULTS': os.getenv('TOP_K_RESULTS'),
    'SIMILARITY_THRESHOLD': os.getenv('SIMILARITY_THRESHOLD'),
}

for key, value in env_vars.items():
    status = "✓" if value and value != "NOT SET" else "✗"
    print(f"  {status} {key}: {value}")

# 4. Test RAG components
print("\n🔍 Testing RAG Components:")
try:
    from rag.config import RAGConfig
    config = RAGConfig.from_env()
    print(f"  ✓ RAGConfig loaded")
    print(f"    - LLM Provider: {config.llm_provider}")
    print(f"    - Model: {config.default_model}")
    print(f"    - Chunk Size: {config.chunk_size}")
    print(f"    - Similarity Threshold: {config.similarity_threshold}")
except Exception as e:
    print(f"  ✗ RAGConfig failed: {e}")

try:
    from rag.vector_store import VectorStore
    vs = VectorStore(config)
    stats = vs.get_stats()
    print(f"  ✓ VectorStore initialized")
    print(f"    - Total vectors: {stats.get('total_vectors', 0)}")
    print(f"    - Index type: {stats.get('index_type', 'N/A')}")
except Exception as e:
    print(f"  ✗ VectorStore failed: {e}")

# 5. Test Gemini connection
print("\n🤖 Testing Gemini API:")
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel(config.default_model)
    response = model.generate_content("Say 'Hello' in one word")
    print(f"  ✓ Gemini API connected successfully")
    print(f"    Response: {response.text[:50]}")
except Exception as e:
    print(f"  ✗ Gemini API test failed: {e}")

# 6. Check directories
print("\n📁 Directory Structure:")
dirs = ['documents/raw', 'documents/processed', 'documents/metadata', 'vector_store']
for d in dirs:
    exists = os.path.exists(d)
    status = "✓" if exists else "○"
    print(f"  {status} {d} {'(exists)' if exists else '(will be created on first use)'}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)

# Summary
if not missing:
    print("\n✅ Setup looks good! You can now:")
    print("   1. Run: python app.py")
    print("   2. Upload documents via /upload endpoint")
    print("   3. Ask questions via /ask endpoint")
else:
    print("\n⚠️  Please install missing packages first")
