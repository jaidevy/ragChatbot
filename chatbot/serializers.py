from rest_framework import serializers

from .models import Conversation, Message, ConversationMemory, UserPersonality, ConversationContext
from .utils import time_since


class MessageSerializer(serializers.ModelSerializer):
    """
    Message serializer with memory enhancements.
    """
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'content', 'is_from_user', 'in_reply_to', 
            'created_at', 'created_at_formatted', 'importance_score', 
            'emotions', 'entities', 'intent'
        ]
        read_only_fields = ['importance_score', 'emotions', 'entities', 'intent']
    
    def get_created_at_formatted(self, obj):
        return time_since(obj.created_at)


class ConversationContextSerializer(serializers.ModelSerializer):
    """
    Serializer for conversation context
    """
    
    class Meta:
        model = ConversationContext
        fields = [
            'current_topic', 'user_mood', 'conversation_flow', 
            'active_memories', 'context_variables'
        ]


class ConversationSerializer(serializers.ModelSerializer):
    """
    Conversation serializer with memory enhancements.
    """
    messages = MessageSerializer(many=True, read_only=True)
    created_at = serializers.SerializerMethodField()
    context = ConversationContextSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'favourite', 'archive', 'created_at', 'messages',
            'conversation_summary', 'key_topics', 'sentiment_analysis', 'context'
        ]
        read_only_fields = ['conversation_summary', 'key_topics', 'sentiment_analysis']

    def get_created_at(self, obj):
        return time_since(obj.created_at)


class ConversationMemorySerializer(serializers.ModelSerializer):
    """
    Serializer for ConversationMemory model
    """
    created_at = serializers.SerializerMethodField()
    last_accessed = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationMemory
        fields = ['id', 'memory_type', 'title', 'content', 'context', 
                 'importance_score', 'access_count', 'last_accessed', 'created_at']
    
    def get_created_at(self, obj):
        return time_since(obj.created_at)
    
    def get_last_accessed(self, obj):
        return time_since(obj.last_accessed)


class UserPersonalitySerializer(serializers.ModelSerializer):
    """
    Serializer for UserPersonality model
    """
    
    class Meta:
        model = UserPersonality
        fields = ['communication_style', 'interests', 'preferences', 'conversation_patterns']
