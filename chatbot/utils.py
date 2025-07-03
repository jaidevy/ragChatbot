from datetime import datetime, timezone
from typing import Any, Dict


def time_since(dt):
    """
    Returns string representing "time since" e.g.
    """
    now = datetime.now(timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()
    minutes = int(seconds // 60)
    hours = int(minutes // 60)
    days = int(hours // 24)
    months = int(days // 30)
    years = int(days // 365)

    if years > 0:
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif months > 0:
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif days > 0:
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return f"{int(seconds)} second{'s' if seconds > 1 else ''} ago"


def format_rag_memory_response(rag_content: str, memory_content: str, user_query: str) -> str:
    """
    Format a response that smoothly integrates RAG and memory content
    """
    formatted_response = ""
    
    # Determine if we have both RAG and memory content
    has_rag = bool(rag_content and rag_content.strip())
    has_memory = bool(memory_content and memory_content.strip())
    
    if has_rag and has_memory:
        # Both sources available - integrate smoothly
        formatted_response = f"Based on our previous conversations and the available information, {memory_content} Additionally, {rag_content}"
    elif has_rag:
        # Only RAG content
        formatted_response = rag_content
    elif has_memory:
        # Only memory content
        formatted_response = f"From our previous conversations, I remember that {memory_content}"
    else:
        # No specific content - provide general response
        formatted_response = f"Regarding your question about '{user_query}', "
    
    return formatted_response


def extract_key_information(text: str) -> Dict[str, Any]:
    """
    Extract key information from text for memory storage
    """
    # Simple implementation - can be enhanced with NLP
    key_info = {
        'has_question': '?' in text,
        'word_count': len(text.split()),
        'has_personal_info': any(word in text.lower() for word in ['i', 'my', 'me', "i'm", "i've"]),
        'has_specific_request': any(word in text.lower() for word in ['please', 'could', 'would', 'can you']),
    }
    
    # Calculate importance based on key indicators
    importance = 0.3  # base importance
    if key_info['has_question']:
        importance += 0.2
    if key_info['has_personal_info']:
        importance += 0.3
    if key_info['word_count'] > 20:
        importance += 0.1
    if key_info['has_specific_request']:
        importance += 0.1
    
    key_info['suggested_importance'] = min(importance, 1.0)
    
    return key_info
