from django.db import models
from django.conf import settings
import secrets
import json


def generate_secure_random_id():
    min_value = 10 ** 10  # Minimum value of the range (inclusive)
    max_value = 10 ** 11 - 1  # Maximum value of the range (exclusive)
    return secrets.randbelow(max_value - min_value) + min_value


class ConversationMemory(models.Model):
    """
    Model to store conversation-level memory and context
    """
    MEMORY_TYPE_CHOICES = [
        ('short_term', 'Short Term'),
        ('long_term', 'Long Term'),
        ('episodic', 'Episodic'),
        ('semantic', 'Semantic'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memories')
    memory_type = models.CharField(max_length=20, choices=MEMORY_TYPE_CHOICES)
    title = models.CharField(max_length=255, help_text="Title or key for the memory")
    content = models.TextField(help_text="Memory content")
    context = models.JSONField(default=dict, help_text="Additional context data")
    importance_score = models.FloatField(default=0.0, help_text="Memory importance score (0-1)")
    access_count = models.IntegerField(default=0, help_text="How many times this memory was accessed")
    last_accessed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this memory expires")
    
    class Meta:
        ordering = ['-importance_score', '-last_accessed']
        indexes = [
            models.Index(fields=['user', 'memory_type']),
            models.Index(fields=['importance_score']),
            models.Index(fields=['last_accessed']),
        ]
    
    def __str__(self):
        return f"{self.memory_type} memory: {self.title}"
    
    def increment_access(self):
        """Increment access count and update last accessed time"""
        self.access_count += 1
        self.save(update_fields=['access_count', 'last_accessed'])


class UserPersonality(models.Model):
    """
    Model to store user personality traits and preferences
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personality')
    communication_style = models.CharField(max_length=50, default='casual', help_text="formal, casual, friendly, professional")
    interests = models.JSONField(default=list, help_text="List of user interests")
    preferences = models.JSONField(default=dict, help_text="User preferences and settings")
    conversation_patterns = models.JSONField(default=dict, help_text="Learned conversation patterns")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Personality profile for {self.user.username}"


class Conversation(models.Model):
    """
    Conversation model representing a chat conversation.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('ended', 'Ended'),
    ]

    id = models.BigIntegerField(primary_key=True, default=generate_secure_random_id, editable=False)
    title = models.CharField(max_length=255, default="Empty")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    favourite = models.BooleanField(default=False)
    archive = models.BooleanField(default=False)
    
    # Memory and context fields
    conversation_summary = models.TextField(blank=True, help_text="AI-generated summary of the conversation")
    key_topics = models.JSONField(default=list, help_text="Important topics discussed")
    sentiment_analysis = models.JSONField(default=dict, help_text="Overall sentiment of conversation")
    context_window = models.JSONField(default=list, help_text="Recent context for memory")
    memory_anchors = models.JSONField(default=list, help_text="Important message IDs for memory retrieval")

    # status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation {self.title} - {self.user.username}"
    
    def get_recent_context(self, limit=10):
        """Get recent messages for context"""
        return self.message_set.order_by('-created_at')[:limit]
    
    def update_conversation_summary(self):
        """Update conversation summary based on recent messages"""
        # This will be implemented in the tasks.py file
        pass


class Message(models.Model):
    """
    Message model representing a message within a conversation.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_from_user = models.BooleanField(default=True)
    in_reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    
    # Memory and context enhancement fields
    embedding_vector = models.JSONField(null=True, blank=True, help_text="Message embedding for similarity search")
    importance_score = models.FloatField(default=0.0, help_text="Message importance for memory retention")
    emotions = models.JSONField(default=dict, help_text="Detected emotions in the message")
    entities = models.JSONField(default=list, help_text="Named entities extracted from message")
    intent = models.CharField(max_length=100, blank=True, help_text="Detected user intent")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['importance_score']),
        ]

    def __str__(self):
        return f"Message in {self.conversation.title}"


class ConversationContext(models.Model):
    """
    Model to store dynamic conversation context
    """
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='context')
    current_topic = models.CharField(max_length=255, blank=True)
    user_mood = models.CharField(max_length=50, blank=True)
    conversation_flow = models.JSONField(default=list, help_text="Flow of conversation topics")
    active_memories = models.JSONField(default=list, help_text="Currently active memory IDs")
    context_variables = models.JSONField(default=dict, help_text="Dynamic context variables")
    
    def __str__(self):
        return f"Context for {self.conversation.title}"
