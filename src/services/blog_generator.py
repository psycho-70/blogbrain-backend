"""
Admin Blog Generator Chatbot Service.
Generates blog drafts, titles, excerpts, FAQs, and SEO-optimized content.
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import json
import re

from src.llm.config import get_llm


BLOG_SYSTEM_PROMPT = """You are an expert content writer and SEO specialist for the Einsteine AI blog platform.
Your role is to help admins create high-quality, engaging blog posts that are:
- Well-structured with clear headings and subheadings
- SEO-optimized with relevant keywords
- Engaging and informative for the target audience
- Suitable for beginner, intermediate, or advanced readers based on context

You can:
1. Generate full blog drafts from a topic or outline
2. Suggest compelling titles and meta descriptions
3. Create excerpts and key points
4. Generate FAQ sections for structured data
5. Optimize existing content for SEO
6. Suggest internal linking opportunities

Always respond in a helpful, professional tone. Format your output with proper Markdown (headers, lists, bold)."""


class BlogGeneratorService:
    """Service for AI-powered blog content generation."""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.8, max_tokens=2000)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", BLOG_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def generate(
        self,
        user_input: str,
        chat_history: list[dict] | None = None,
        category_hint: str | None = None,
        level_hint: str | None = None,
    ) -> str:
        """Generate blog content or respond to admin request."""
        messages = []
        if chat_history:
            for msg in chat_history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))
        
        context = ""
        if category_hint:
            context += f"Category context: {category_hint}. "
        if level_hint:
            context += f"Target audience level: {level_hint}. "
        if context:
            user_input = f"{context}\n\n{user_input}"
        
        result = self.chain.invoke({
            "chat_history": messages,
            "input": user_input,
        })
        return result

    def generate_json(
        self,
        topic: str,
        category: str | None = None,
        level: str | None = None,
    ) -> dict:
        """Generate a structured blog post in JSON format."""
        try:
            # Use dynamic variables in prompt to avoid empty invoke issues
            json_prompt = ChatPromptTemplate.from_messages([
                ("system", BLOG_SYSTEM_PROMPT + "\n\nYou must return only a VALID JSON object. " +
                 "Output only the JSON, no conversation, no markdown blocks. " +
                 "The 'content' field must be a complete, high-quality blog post (800-1000 words) with Markdown formatting. " +
                 "The JSON keys must be exactly: title, content, excerpt, meta_title, meta_description, tags."),
                ("human", "Write a comprehensive, professional, and detailed blog post about: '{topic}'. " +
                 "Category: {category}. Target Level: {level}. " +
                 "Make it highly engaging and ready to publish."),
            ])
            
            # Use a higher max_tokens for full blog generation
            # Enable JSON mode for Groq to ensure valid JSON structure
            llm = get_llm(
                temperature=0.7, 
                max_tokens=4000, 
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            chain = json_prompt | llm | StrOutputParser()
            
            # Pass variables explicitly
            response = chain.invoke({
                "topic": topic,
                "category": category or "General",
                "level": level or "Beginner"
            })
            
            if not response:
                raise ValueError("Empty response from AI")
            
            print(f"DEBUG: Raw AI Response length: {len(response)}") 

            # Clean possible markdown code blocks and thought tags
            clean_response = response.strip()
            
            # Remove <thought> tags if present
            clean_response = re.sub(r'<thought>.*?</thought>', '', clean_response, flags=re.DOTALL).strip()
            
            # Remove markdown JSON wrappers
            if '```' in clean_response:
                clean_response = re.sub(r'```json\n?|\n?```', '', clean_response).strip()
            
            # Try to handle unescaped control characters/newlines that break json.loads
            # (especially common in the 'content' field with markdown)
            def fix_json_strings(s):
                # This is a basic attempt to find JSON string values and escape real newlines
                # but it's tricky with regex. Instead, let's try a more robust cleaning.
                return s.replace('\x00', '').replace('\x01', '').replace('\x02', '')

            clean_response = fix_json_strings(clean_response)

            try:
                # Find the FIRST { and LAST } to extract JSON
                first_brace = clean_response.find('{')
                last_brace = clean_response.rfind('}')
                
                if first_brace != -1 and last_brace != -1:
                    json_str = clean_response[first_brace:last_brace+1]
                    return json.loads(json_str)
                else:
                    return json.loads(clean_response)
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON parse failed, attempting strict cleaning: {str(e)}")
                # If it's an "Unterminated string" error, it's often due to real newlines.
                # Let's try to replace real newlines with \n inside the content
                # This is risky but often works for AI generated JSON
                try:
                    # Match "content": "..." where ... contains real newlines
                    # This is a very rough approach
                    import ast
                    # Sometimes ast.literal_eval is more forgiving for single vs double quotes
                    # but it's not JSON. Let's try raw string escaping.
                    return json.loads(clean_response, strict=False)
                except:
                    raise e

        except Exception as e:
            # Fallback or error handling
            import traceback
            error_msg = str(e)
            print(f"CRITICAL ERROR in generate_json: {error_msg}")
            traceback.print_exc()
            
            return {
                "title": f"Blog: {topic}",
                "content": f"## {topic}\n\n[Generation error: {error_msg}]\n\nWe encountered an issue with the AI generator. Please try again or check your API connection.",
                "excerpt": f"An error occurred while generating content for '{topic}'.",
                "meta_title": topic,
                "meta_description": f"Article about {topic}",
                "tags": ["Draft", "Correction Required"]
            }
