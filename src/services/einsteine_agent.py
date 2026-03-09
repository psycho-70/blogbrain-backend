"""
Einsteine™ - Main Website Agent Chatbot (LangGraph).
Guides users, provides tours, answers questions, and navigates content.
"""
from typing import Annotated, TypedDict, Literal, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.llm.config import get_llm
from src.models.blog_model import BlogModel
from src.models.category_model import CategoryModel


# --- Tools for Einsteine Agent ---

def get_website_context():
    """Get current website content for context (blogs, categories)."""
    try:
        categories = CategoryModel.query.filter_by(is_active=True).all()
        blogs = BlogModel.query.filter_by(is_published=True).order_by(
            BlogModel.created_at.desc()
        ).limit(20).all()
        
        cats_str = ", ".join([c.name for c in categories]) if categories else "No categories yet"
        blogs_list = [
            f"- {b.title} → /blogs/{b.slug}"
            for b in blogs
        ]
        blogs_str = "\n".join(blogs_list) if blogs_list else "No published blogs yet"
        
        return {
            "categories": cats_str,
            "blogs": blogs_str,
            "has_content": len(blogs) > 0,
        }
    except Exception:
        return {"categories": "", "blogs": "", "has_content": False}


@tool
def get_content_catalog() -> str:
    """
    Get the list of available blog categories and recent articles.
    Use this when user asks what content is available, wants to explore, or needs a tour.
    """
    ctx = get_website_context()
    if not ctx["has_content"]:
        return "The blog doesn't have published content yet. Feel free to explore the site structure!"
    return f"""Available content on this platform:

Categories: {ctx['categories']}

Recent Articles:
{ctx['blogs']}

IMPORTANT: When listing blogs, always show the full path exactly as given (e.g. /blogs/some-slug). Do NOT shorten or modify the path."""


@tool
def search_content(query: str) -> str:
    """
    Search for blog posts by topic, keyword, or theme.
    Use when user is looking for specific information or content.
    Args:
        query: Search term (topic, keyword, or subject)
    """
    try:
        blogs = BlogModel.query.filter(
            BlogModel.is_published == True,
            (BlogModel.title.ilike(f"%{query}%")) |
            (BlogModel.content.ilike(f"%{query}%")) |
            (BlogModel.excerpt.ilike(f"%{query}%")) |
            (BlogModel.tags.ilike(f"%{query}%"))
        ).limit(10).all()
        
        if not blogs:
            return f"No articles found matching '{query}'. Try a different topic or browse the catalog."
        
        results = "\n".join([
            f"- {b.title} → /blogs/{b.slug}"
            for b in blogs
        ])
        return f"Found articles about '{query}':\n{results}"
    except Exception:
        return "Search is temporarily unavailable. Try asking for the content catalog instead."


@tool
def get_content_by_level(level: Literal["beginner", "intermediate", "advanced"]) -> str:
    """
    Get content recommendations by experience level.
    Use when user says they want content for their level.
    Args:
        level: beginner, intermediate, or advanced
    """
    ctx = get_website_context()
    if not ctx["has_content"]:
        return "There's no content published yet. Check back soon!"
    cats = ctx["categories"]
    blogs = ctx["blogs"]
    return f"For {level} level readers, here's what we have:\n\nCategories: {cats}\n\nRecent Articles:\n{blogs}"


# --- Agent State & Graph ---

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]


EINSTEINE_SYSTEM = """You are Einsteine™, the intelligent AI host of this blogging platform.

Your personality:
- Friendly, warm, and helpful (use "Salam/Hello" for multicultural greeting)
- Concise - keep responses short and actionable (2-4 sentences unless explaining something complex)
- You guide users through the site, recommend content, and answer questions

You can:
1. Give a quick 30-second tour of the platform
2. Help users find content by topic, level, or interest
3. Answer questions about the website, blogs, or general topics (stick to what you know from tools)
4. Recommend articles and suggest next steps

IMPORTANT FORMATTING RULES:
- Use the tools to get real content - never invent blog titles or URLs
- If you don't have tool results, say so politely
- When listing blogs, format each as: Title → /blogs/slug  (keep the exact path from tools, never shorten it)
- Do NOT use markdown bold (**text**) in your responses - write plain text only
- Do NOT wrap URLs in parentheses - write the path directly after the arrow →
- Always suggest a clear next action (e.g., "Visit /blogs to see all articles")
"""


def create_einsteine_agent():
    """Build the LangGraph agent for Einsteine."""
    llm = get_llm(temperature=0.7, max_tokens=800)
    
    tools = [get_content_catalog, search_content, get_content_by_level]
    llm_with_tools = llm.bind_tools(tools)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", EINSTEINE_SYSTEM),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    def agent_node(state: AgentState):
        result = llm_with_tools.invoke(
            prompt.format_messages(messages=state["messages"])
        )
        return {"messages": [result]}
    
    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "__end__"
    
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "__end__": END}
    )
    graph.add_edge("tools", "agent")
    
    return graph.compile()


# Singleton agent
_agent = None


def get_einsteine_agent():
    global _agent
    if _agent is None:
        _agent = create_einsteine_agent()
    return _agent


class EinsteineAgentService:
    """Service wrapper for Einsteine agent."""
    
    def chat(
        self,
        user_message: str,
        chat_history: list[dict] | None = None,
        entry_source: str | None = None,
        landing_context: str | None = None,
    ) -> str:
        """Process user message and return Einsteine's response."""
        agent = get_einsteine_agent()
        
        messages = []
        if chat_history:
            for msg in chat_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        
        # Add context from entry source if provided
        if entry_source or landing_context:
            ctx = []
            if entry_source:
                ctx.append(f"User came from: {entry_source}")
            if landing_context:
                ctx.append(f"Landing context: {landing_context}")
            user_message = f"[Context: {'; '.join(ctx)}]\n\n{user_message}"
        
        messages.append(HumanMessage(content=user_message))
        
        config = {"configurable": {}}
        result = agent.invoke({"messages": messages}, config)
        
        # Get last AI message
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content
        
        return "I'm here to help! What would you like to explore?"
