"""
Response Generator Module

Handles LLM integration and response generation with source citations.
"""

from typing import Dict, Any, List, Optional
import logging
import time

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available. Install with: pip install openai")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Gemini library not available. Install with: pip install google-generativeai")

from .config import RAGConfig


logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates AI responses using retrieved context."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.client = None
        self.gemini_model = None
        if (self.config.llm_provider or "openai").lower() == "gemini":
            self._setup_gemini()
        else:
            self._setup_openai()
    
    def _setup_openai(self) -> None:
        """Initialize OpenAI client if available and configured."""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available. Responses will be rule-based.")
            return
        
        if not self.config.openai_api_key or self.config.openai_api_key == "your_openai_key_here":
            logger.warning("OpenAI API key not configured. Responses will be rule-based.")
            return
        
        try:
            self.client = openai.OpenAI(api_key=self.config.openai_api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")

    def _setup_gemini(self) -> None:
        """Initialize Gemini client if available and configured."""
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini not available. Responses will be rule-based.")
            return
        if not self.config.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured. Responses will be rule-based.")
            return
        try:
            genai.configure(api_key=self.config.gemini_api_key)
            # default_model may contain a Gemini model name like 'gemini-1.5-flash'
            model_name = self.config.default_model or "gemini-1.5-flash"
            self.gemini_model = genai.GenerativeModel(model_name)
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
    
    def generate_response(self, query: str, context: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate response using context and sources.
        
        Args:
            query: User question
            context: Retrieved context
            sources: Source information
            
        Returns:
            Response dictionary with answer and metadata
        """
        start_time = time.time()
        
        try:
            use_openai = self.client is not None and (self.config.llm_provider or "openai").lower() == "openai"
            use_gemini = self.gemini_model is not None and (self.config.llm_provider or "openai").lower() == "gemini"

            if (use_openai or use_gemini) and context.strip():
                # Generate AI response
                if use_gemini:
                    response_data = self._generate_gemini_response(query, context, sources)
                else:
                    response_data = self._generate_ai_response(query, context, sources)
            else:
                # Fall back to rule-based response
                response_data = self._generate_fallback_response(query, context, sources)
            
            # Add timing
            response_data['meta']['generation_time_ms'] = int((time.time() - start_time) * 1000)
            
            return response_data
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return {
                'answer': f"I apologize, but I encountered an error while processing your question: {str(e)}",
                'sources': sources,
                'meta': {
                    'model': 'error',
                    'tokens_used': 0,
                    'generation_time_ms': int((time.time() - start_time) * 1000),
                    'has_sources': len(sources) > 0,
                    'error': str(e)
                }
            }
    
    def _generate_ai_response(self, query: str, context: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate response using OpenAI."""
        system_prompt = self._create_system_prompt()
        user_prompt = self._create_user_prompt(query, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # Add source references to answer if sources exist
            if sources:
                answer += self._format_source_references(sources)
            
            return {
                'answer': answer,
                'sources': sources,
                'meta': {
                    'model': self.config.default_model,
                    'tokens_used': tokens_used,
                    'has_sources': len(sources) > 0,
                    'context_length': len(context)
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            # Fall back to rule-based response
            return self._generate_fallback_response(query, context, sources)

    def _generate_gemini_response(self, query: str, context: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate response using Gemini."""
        try:
            prompt = self._create_system_prompt() + "\n\n" + self._create_user_prompt(query, context)
            resp = self.gemini_model.generate_content(prompt)
            # Handle streaming or non-streaming responses
            answer = ""
            if hasattr(resp, 'text') and resp.text is not None:
                answer = resp.text
            elif hasattr(resp, 'candidates') and resp.candidates:
                # Fallback: concatenate parts
                parts = []
                for cand in resp.candidates:
                    if getattr(cand, 'content', None) and getattr(cand.content, 'parts', None):
                        for part in cand.content.parts:
                            parts.append(getattr(part, 'text', '') or '')
                answer = "\n".join([p for p in parts if p])

            if sources:
                answer += self._format_source_references(sources)

            return {
                'answer': answer or "",
                'sources': sources,
                'meta': {
                    'model': self.config.default_model or 'gemini-1.5-flash',
                    'tokens_used': 0,  # google-generativeai doesn't expose tokens consistently
                    'has_sources': len(sources) > 0,
                    'context_length': len(context)
                }
            }
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            return self._generate_fallback_response(query, context, sources)
    
    def _generate_fallback_response(self, query: str, context: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate rule-based response when AI is not available."""
        if context.strip():
            # We have relevant context
            answer = f"Based on the available documents, here's what I found regarding '{query}':\n\n"
            
            # Add a summary of the context
            context_preview = context[:500] + "..." if len(context) > 500 else context
            answer += context_preview
            
            if sources:
                answer += f"\n\nThis information comes from {len(sources)} document source(s)."
                answer += self._format_source_references(sources)
        else:
            # No relevant context found
            answer = f"I couldn't find specific information about '{query}' in the uploaded documents. "
            answer += "You might want to:\n"
            answer += "1. Upload more relevant documents\n"
            answer += "2. Try rephrasing your question\n"
            answer += "3. Ask about topics covered in your uploaded documents"
        
        return {
            'answer': answer,
            'sources': sources,
            'meta': {
                'model': 'fallback',
                'tokens_used': 0,
                'has_sources': len(sources) > 0,
                'context_length': len(context)
            }
        }
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for AI model."""
        return """You are a helpful AI assistant that answers questions based on provided document context.

INSTRUCTIONS:
1. Answer the user's question using ONLY the information provided in the context.
2. Be accurate and specific.
3. If the context doesn't contain enough information to fully answer the question, say so.
4. Cite specific information from the context when possible.
5. Keep your response concise but comprehensive.
6. Do not make up information not found in the context.
7. If the user asks to explain or summarize a story, do this:
   - Start with one short sentence of setup (who/what) for context.
   - Use simple, clear language.
   - End with a single concise line beginning with "Moral:" if a moral is present in the context.

Remember: You are answering based on specific documents the user has uploaded."""
    
    def _create_user_prompt(self, query: str, context: str) -> str:
        """Create user prompt with query and context."""
        return f"""CONTEXT FROM USER'S DOCUMENTS:
{context}

USER QUESTION: {query}

Please answer the question based on the context provided above."""
    
    def _format_source_references(self, sources: List[Dict[str, Any]]) -> str:
        """Format source references for inclusion in response."""
        if not sources:
            return ""
        
        references = "\n\n---\n**Sources:**\n"
        
        # Group sources by document
        by_document = {}
        for source in sources:
            doc_id = source.get('document_id', 'unknown')
            if doc_id not in by_document:
                by_document[doc_id] = []
            by_document[doc_id].append(source)
        
        for doc_id, doc_sources in by_document.items():
            references += f"• **{doc_id}** "
            
            pages = set()
            for source in doc_sources:
                page = source.get('page', 1)
                if page:
                    pages.add(page)
            
            if pages:
                if len(pages) == 1:
                    references += f"(page {list(pages)[0]})"
                else:
                    references += f"(pages {', '.join(map(str, sorted(pages)))})"
            
            references += "\n"
        
        return references
    
    def test_connection(self) -> Dict[str, Any]:
        """Test OpenAI connection and return status."""
        if not self.client:
            return {
                'status': 'not_configured',
                'message': 'OpenAI client not initialized',
                'available': False
            }
        
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.config.default_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            return {
                'status': 'connected',
                'message': 'OpenAI API connection successful',
                'available': True,
                'model': self.config.default_model
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection failed: {str(e)}',
                'available': False
            }
