from django.contrib import admin
from .models import Conversation, Message, ConversationMemory, UserPersonality, ConversationContext


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin site configuration for Conversation model.
    """
    list_display = ('id', 'title', 'user', 'favourite', 'archive', 'created_at', 'updated_at', 'memory_count')
    list_filter = ('created_at', 'updated_at', 'favourite', 'archive',)
    search_fields = ('user__username', 'title', 'key_topics')
    readonly_fields = ('conversation_summary', 'key_topics', 'sentiment_analysis', 'context_window', 'memory_anchors')
    
    def memory_count(self, obj):
        return obj.user.memories.count()
    memory_count.short_description = 'Memories'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin site configuration for Message model.
    """
    list_display = ('id', 'conversation', 'content_preview', 'is_from_user', 'importance_score', 'created_at')
    list_filter = ('is_from_user', 'conversation__user__username', 'created_at', 'importance_score')
    search_fields = ('content', 'entities', 'intent')
    readonly_fields = ('embedding_vector', 'importance_score', 'emotions', 'entities', 'intent')
    ordering = ('-created_at',)
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(ConversationMemory)
class ConversationMemoryAdmin(admin.ModelAdmin):
    """
    Admin site configuration for ConversationMemory model.
    """
    list_display = ('id', 'user', 'memory_type', 'title', 'importance_score', 
                   'access_count', 'created_at', 'last_accessed')
    list_filter = ('memory_type', 'importance_score', 'created_at', 'last_accessed')
    search_fields = ('title', 'content', 'user__username')
    readonly_fields = ('access_count', 'last_accessed')
    ordering = ('-importance_score', '-last_accessed')


@admin.register(UserPersonality)
class UserPersonalityAdmin(admin.ModelAdmin):
    """
    Admin site configuration for UserPersonality model.
    """
    list_display = ('user', 'communication_style', 'created_at', 'updated_at')
    list_filter = ('communication_style', 'created_at')
    search_fields = ('user__username',)


@admin.register(ConversationContext)
class ConversationContextAdmin(admin.ModelAdmin):
    """
    Admin site configuration for ConversationContext model.
    """
    list_display = ('conversation', 'current_topic', 'user_mood')
    list_filter = ('user_mood',)
    search_fields = ('conversation__title', 'current_topic')
