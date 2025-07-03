"""
Memory management settings for the chatbot
"""

# Memory Management Settings
CHATBOT_MEMORY_SETTINGS = {
    # Short-term memory settings
    'SHORT_TERM_MEMORY_LIMIT': 20,  # Maximum number of short-term memories per user
    'SHORT_TERM_MEMORY_EXPIRY_HOURS': 24,  # Hours before short-term memories expire
    
    # Long-term memory settings
    'LONG_TERM_IMPORTANCE_THRESHOLD': 0.7,  # Minimum importance score for long-term storage
    'LONG_TERM_MEMORY_LIMIT': 100,  # Maximum number of long-term memories per user
    
    # Context settings
    'CONVERSATION_CONTEXT_LIMIT': 10,  # Number of recent messages to keep in context
    'RELEVANT_MEMORIES_LIMIT': 5,  # Number of relevant memories to include in AI context
    
    # Importance calculation settings
    'IMPORTANCE_KEYWORDS': [
        'remember', 'important', 'never forget', 'always', 'prefer',
        'like', 'dislike', 'love', 'hate', 'birthday', 'anniversary',
        'work', 'job', 'family', 'hobby', 'goal', 'dream', 'address',
        'phone', 'email', 'name', 'age', 'location', 'schedule'
    ],
    
    # Memory cleanup settings
    'CLEANUP_INTERVAL_HOURS': 24,  # How often to run memory cleanup
    'MEMORY_PROMOTION_THRESHOLD': 0.6,  # Minimum score for promoting to long-term
    
    # AI enhancement settings
    'ENHANCE_SYSTEM_PROMPT': True,  # Whether to enhance system prompt with memory
    'INCLUDE_PERSONALITY_CONTEXT': True,  # Whether to include personality in context
    'INCLUDE_CONVERSATION_HISTORY': True,  # Whether to include conversation history
    
    # Performance settings
    'MEMORY_SEARCH_LIMIT': 50,  # Maximum memories to search through
    'CONTEXT_GENERATION_TIMEOUT': 30,  # Timeout for context generation in seconds
}

# Default personality settings
DEFAULT_PERSONALITY = {
    'communication_style': 'casual',
    'interests': [],
    'preferences': {
        'response_length': 'medium',
        'formality': 'casual',
        'emoji_usage': 'moderate',
        'explanation_detail': 'balanced'
    },
    'conversation_patterns': {
        'typical_topics': [],
        'common_questions': [],
        'preferred_responses': []
    }
}

# Memory type configurations
MEMORY_TYPES = {
    'short_term': {
        'description': 'Recent conversation context and temporary information',
        'max_age_hours': 24,
        'max_count': 20,
        'auto_cleanup': True
    },
    'long_term': {
        'description': 'Important information and user preferences',
        'max_age_hours': None,  # No expiry
        'max_count': 100,
        'auto_cleanup': False
    },
    'episodic': {
        'description': 'Specific events and experiences',
        'max_age_hours': 168,  # 1 week
        'max_count': 50,
        'auto_cleanup': True
    },
    'semantic': {
        'description': 'Facts and general knowledge about the user',
        'max_age_hours': None,  # No expiry
        'max_count': 200,
        'auto_cleanup': False
    }
}

# AI prompt templates
MEMORY_PROMPT_TEMPLATES = {
    'system_enhancement': """
You are an AI assistant with enhanced memory capabilities. You remember past conversations, 
user preferences, and important information to provide personalized responses.

User Profile:
- Communication Style: {communication_style}
- Interests: {interests}
- Preferences: {preferences}

Relevant Memories:
{relevant_memories}

Recent Context:
{recent_context}

Instructions:
- Reference past conversations when relevant
- Adapt your communication style to match the user's preferences
- Remember and use important information the user has shared
- Be contextually aware and personalized in your responses
- If you remember something about the user, mention it naturally
""",
    
    'memory_extraction': """
Analyze the following conversation and extract:
1. Important information that should be remembered
2. User preferences mentioned
3. Key topics discussed
4. Emotional context
5. Any personal details shared

Conversation:
{conversation_text}

Return the analysis in JSON format with the following structure:
{
    "important_info": "string",
    "preferences": {},
    "topics": [],
    "emotional_context": "string",
    "personal_details": []
}
""",
    
    'context_summary': """
Create a brief summary of this conversation context for memory storage:

Messages:
{messages}

Provide a concise summary that captures the key points and context.
"""
}

# Export settings for Django settings integration
def get_memory_settings():
    """Get memory settings for Django settings"""
    return CHATBOT_MEMORY_SETTINGS

def get_default_personality():
    """Get default personality settings"""
    return DEFAULT_PERSONALITY

def get_memory_types():
    """Get memory type configurations"""
    return MEMORY_TYPES

def get_prompt_templates():
    """Get AI prompt templates"""
    return MEMORY_PROMPT_TEMPLATES
