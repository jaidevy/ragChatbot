"""
Memory management utilities for the chatbot
Handles short-term and long-term memory operations
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.db.models import Q, F
from django.conf import settings
from .models import ConversationMemory, UserPersonality, Conversation, Message, ConversationContext

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages short-term and long-term memory for the chatbot
    """
    
    def __init__(self, user):
        self.user = user
        self.short_term_limit = getattr(settings, 'CHATBOT_SHORT_TERM_MEMORY_LIMIT', 20)
        self.long_term_importance_threshold = getattr(settings, 'CHATBOT_LONG_TERM_IMPORTANCE_THRESHOLD', 0.7)
    
    def get_short_term_memory(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve short-term memory items
        """
        if limit is None:
            limit = self.short_term_limit
        
        memories = ConversationMemory.objects.filter(
            user=self.user,
            memory_type='short_term'
        ).order_by('-last_accessed')[:limit]
        
        return [self._memory_to_dict(memory) for memory in memories]
    
    def get_long_term_memory(self, query: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve long-term memory items, optionally filtered by query
        """
        queryset = ConversationMemory.objects.filter(
            user=self.user,
            memory_type='long_term'
        )
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(content__icontains=query)
            )
        
        memories = queryset.order_by('-importance_score', '-last_accessed')[:limit]
        
        # Increment access count for retrieved memories
        for memory in memories:
            memory.increment_access()
        
        return [self._memory_to_dict(memory) for memory in memories]
    
    def store_short_term_memory(self, title: str, content: str, context: Dict = None, importance: float = 0.5):
        """
        Store a short-term memory item
        """
        # Set expiration for short-term memory (24 hours)
        expires_at = timezone.now() + timedelta(hours=24)
        
        memory = ConversationMemory.objects.create(
            user=self.user,
            memory_type='short_term',
            title=title,
            content=content,
            context=context or {},
            importance_score=importance,
            expires_at=expires_at
        )
        
        # Clean up old short-term memories
        self._cleanup_short_term_memory()
        
        return memory
    
    def store_long_term_memory(self, title: str, content: str, context: Dict = None, importance: float = 0.8):
        """
        Store a long-term memory item
        """
        memory = ConversationMemory.objects.create(
            user=self.user,
            memory_type='long_term',
            title=title,
            content=content,
            context=context or {},
            importance_score=importance
        )
        
        return memory
    
    def promote_to_long_term(self, short_term_memory_id: int):
        """
        Promote a short-term memory to long-term storage
        """
        try:
            memory = ConversationMemory.objects.get(
                id=short_term_memory_id,
                user=self.user,
                memory_type='short_term'
            )
            
            # Only promote if importance score is above threshold
            if memory.importance_score >= self.long_term_importance_threshold:
                memory.memory_type = 'long_term'
                memory.expires_at = None  # Remove expiration for long-term memory
                memory.save()
                logger.info(f"Promoted memory {memory.id} to long-term storage")
                return True
            
        except ConversationMemory.DoesNotExist:
            logger.warning(f"Short-term memory {short_term_memory_id} not found")
        
        return False
    
    def get_conversation_context(self, conversation_id: int) -> Dict[str, Any]:
        """
        Get conversation context including recent messages and active memories
        """
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=self.user)
            context, created = ConversationContext.objects.get_or_create(
                conversation=conversation,
                defaults={
                    'current_topic': '',
                    'user_mood': 'neutral',
                    'conversation_flow': [],
                    'active_memories': [],
                    'context_variables': {}
                }
            )
            
            # Get recent messages for context
            recent_messages = conversation.get_recent_context(limit=10)
            
            # Get relevant memories based on conversation content
            relevant_memories = self._get_relevant_memories(conversation)
            
            return {
                'conversation_id': conversation_id,
                'current_topic': context.current_topic,
                'user_mood': context.user_mood,
                'conversation_flow': context.conversation_flow,
                'recent_messages': [
                    {
                        'content': msg.content,
                        'is_from_user': msg.is_from_user,
                        'created_at': msg.created_at.isoformat(),
                        'importance_score': msg.importance_score
                    }
                    for msg in recent_messages
                ],
                'relevant_memories': relevant_memories,
                'context_variables': context.context_variables
            }
            
        except Conversation.DoesNotExist:
            return {}
    
    def update_conversation_context(self, conversation_id: int, **kwargs):
        """
        Update conversation context with new information
        """
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=self.user)
            context, created = ConversationContext.objects.get_or_create(
                conversation=conversation
            )
            
            for key, value in kwargs.items():
                if hasattr(context, key):
                    setattr(context, key, value)
            
            context.save()
            
        except Conversation.DoesNotExist:
            logger.warning(f"Conversation {conversation_id} not found")
    
    def extract_important_information(self, message: str, is_from_user: bool) -> Dict[str, Any]:
        """
        Extract important information from a message for memory storage
        This is a placeholder for more sophisticated NLP processing
        """
        importance_keywords = [
            'remember', 'important', 'never forget', 'always', 'prefer',
            'like', 'dislike', 'love', 'hate', 'birthday', 'anniversary',
            'work', 'job', 'family', 'hobby', 'goal', 'dream'
        ]
        
        message_lower = message.lower()
        importance_score = 0.0
        
        # Calculate importance based on keywords
        for keyword in importance_keywords:
            if keyword in message_lower:
                importance_score += 0.1
        
        # User messages about preferences are generally more important
        if is_from_user:
            importance_score += 0.2
        
        # Clamp importance score between 0 and 1
        importance_score = min(1.0, importance_score)
        
        return {
            'importance_score': importance_score,
            'contains_personal_info': any(keyword in message_lower for keyword in ['my', 'i am', 'i like', 'i prefer']),
            'is_question': message.strip().endswith('?'),
            'is_request': any(word in message_lower for word in ['please', 'can you', 'could you', 'would you'])
        }
    
    def get_user_personality(self) -> Dict[str, Any]:
        """
        Get user personality profile
        """
        try:
            personality = UserPersonality.objects.get(user=self.user)
            return {
                'communication_style': personality.communication_style,
                'interests': personality.interests,
                'preferences': personality.preferences,
                'conversation_patterns': personality.conversation_patterns
            }
        except UserPersonality.DoesNotExist:
            # Create default personality profile
            personality = UserPersonality.objects.create(
                user=self.user,
                communication_style='casual',
                interests=[],
                preferences={},
                conversation_patterns={}
            )
            return {
                'communication_style': personality.communication_style,
                'interests': personality.interests,
                'preferences': personality.preferences,
                'conversation_patterns': personality.conversation_patterns
            }
    
    def update_user_personality(self, **kwargs):
        """
        Update user personality profile
        """
        personality, created = UserPersonality.objects.get_or_create(
            user=self.user,
            defaults={
                'communication_style': 'casual',
                'interests': [],
                'preferences': {},
                'conversation_patterns': {}
            }
        )
        
        for key, value in kwargs.items():
            if hasattr(personality, key):
                setattr(personality, key, value)
        
        personality.save()
    
    def _memory_to_dict(self, memory: ConversationMemory) -> Dict[str, Any]:
        """
        Convert memory object to dictionary
        """
        return {
            'id': memory.id,
            'title': memory.title,
            'content': memory.content,
            'context': memory.context,
            'importance_score': memory.importance_score,
            'access_count': memory.access_count,
            'last_accessed': memory.last_accessed.isoformat(),
            'created_at': memory.created_at.isoformat()
        }
    
    def _get_relevant_memories(self, conversation: Conversation) -> List[Dict[str, Any]]:
        """
        Get memories relevant to the current conversation
        """
        # Get key topics from conversation
        key_topics = conversation.key_topics or []
        
        # Search memories based on topics
        relevant_memories = []
        for topic in key_topics:
            memories = ConversationMemory.objects.filter(
                user=self.user
            ).filter(
                Q(title__icontains=topic) | Q(content__icontains=topic)
            )[:3]  # Limit to 3 memories per topic
            
            relevant_memories.extend([self._memory_to_dict(memory) for memory in memories])
        
        return relevant_memories[:10]  # Limit total relevant memories
    
    def _cleanup_short_term_memory(self):
        """
        Clean up expired short-term memories
        """
        # Remove expired memories
        expired_memories = ConversationMemory.objects.filter(
            user=self.user,
            memory_type='short_term',
            expires_at__lt=timezone.now()
        )
        
        expired_count = expired_memories.count()
        if expired_count > 0:
            expired_memories.delete()
            logger.info(f"Cleaned up {expired_count} expired short-term memories")
        
        # Keep only the most recent/important short-term memories
        excess_memories = ConversationMemory.objects.filter(
            user=self.user,
            memory_type='short_term'
        ).order_by('-importance_score', '-last_accessed')[self.short_term_limit:]
        
        if excess_memories.exists():
            excess_count = excess_memories.count()
            excess_memories.delete()
            logger.info(f"Cleaned up {excess_count} excess short-term memories")
    
    def get_rag_enhanced_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get memories that are most relevant to the current query for RAG enhancement
        """
        try:
            # Get both short-term and long-term memories relevant to the query
            relevant_memories = []
            
            # Search in long-term memories using embeddings
            long_term_memories = self.get_long_term_memory(query=query, limit=limit//2)
            
            # Get recent short-term memories
            short_term_memories = self.get_short_term_memory(limit=limit//2)
            
            # Filter short-term memories by relevance to query
            if query:
                filtered_short_term = []
                query_lower = query.lower()
                for memory in short_term_memories:
                    if (query_lower in memory.get('title', '').lower() or 
                        query_lower in memory.get('content', '').lower()):
                        filtered_short_term.append(memory)
                short_term_memories = filtered_short_term[:limit//2]
            
            # Combine and sort by relevance
            relevant_memories = long_term_memories + short_term_memories
            
            # Format memories for RAG context
            formatted_memories = []
            for memory in relevant_memories:
                formatted_memories.append({
                    'content': memory.get('content', ''),
                    'context': memory.get('context', {}),
                    'importance': memory.get('importance_score', 0),
                    'type': 'personal_memory'
                })
            
            return formatted_memories
            
        except Exception as e:
            logger.error(f"Error getting RAG enhanced memories: {e}")
            return []
    
    def merge_rag_and_memory_context(self, rag_docs: List[Any], memories: List[Dict[str, Any]]) -> str:
        """
        Merge RAG document results with user memories for enhanced context
        """
        merged_context = ""
        
        # Add personal memories first (higher priority)
        if memories:
            merged_context += "Personal context from previous conversations:\n"
            for memory in memories[:3]:  # Limit to top 3 memories
                merged_context += f"- {memory['content']}\n"
            merged_context += "\n"
        
        # Add RAG document context
        if rag_docs:
            merged_context += "Relevant information from knowledge base:\n"
            for doc in rag_docs:
                merged_context += f"{doc.page_content}\n\n"
        
        return merged_context


class ContextManager:
    """
    Manages conversation context and flow
    """
    
    def __init__(self, conversation_id: int, user):
        self.conversation_id = conversation_id
        self.user = user
        self.memory_manager = MemoryManager(user)
    
    def build_context_for_ai(self, current_message: str) -> Dict[str, Any]:
        """
        Build comprehensive context for AI response generation
        """
        # Get conversation context
        context = self.memory_manager.get_conversation_context(self.conversation_id)
        
        # Get user personality
        personality = self.memory_manager.get_user_personality()
        
        # Get relevant memories
        relevant_memories = self.memory_manager.get_long_term_memory(
            query=current_message, 
            limit=5
        )
        
        # Extract information from current message
        message_info = self.memory_manager.extract_important_information(
            current_message, 
            is_from_user=True
        )
        
        return {
            'conversation_context': context,
            'user_personality': personality,
            'relevant_memories': relevant_memories,
            'current_message_info': message_info,
            'short_term_memory': self.memory_manager.get_short_term_memory(limit=10)
        }
    
    def process_ai_response(self, ai_response: str, user_message: str):
        """
        Process AI response and update memories/context
        """
        # Store important information as memories
        user_info = self.memory_manager.extract_important_information(user_message, True)
        ai_info = self.memory_manager.extract_important_information(ai_response, False)
        
        # Store user message as short-term memory if important
        if user_info['importance_score'] > 0.3:
            self.memory_manager.store_short_term_memory(
                title=f"User message: {user_message[:50]}...",
                content=user_message,
                context={'conversation_id': self.conversation_id},
                importance=user_info['importance_score']
            )
        
        # Update conversation context if needed
        if user_info['contains_personal_info']:
            self.memory_manager.update_conversation_context(
                self.conversation_id,
                context_variables={
                    'has_personal_info': True,
                    'last_personal_info': user_message
                }
            )
