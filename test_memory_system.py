#!/usr/bin/env python
"""
Test script for the enhanced chatbot memory system
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from chatbot.models import Conversation, Message, ConversationMemory, UserPersonality
from chatbot.memory_manager import MemoryManager, ContextManager

User = get_user_model()

def test_memory_system():
    """Test the memory management system"""
    print("🧠 Testing Chatbot Memory System...")
    
    # Create a test user if not exists
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        print(f"✅ Created test user: {user.username}")
    else:
        print(f"✅ Using existing test user: {user.username}")
    
    # Initialize memory manager
    memory_manager = MemoryManager(user)
    print("✅ Memory manager initialized")
    
    # Test user personality
    personality = memory_manager.get_user_personality()
    print(f"✅ User personality: {personality['communication_style']}")
    
    # Store some test memories
    memory1 = memory_manager.store_short_term_memory(
        title="User likes coffee",
        content="The user mentioned they love drinking coffee in the morning",
        importance=0.8
    )
    print(f"✅ Stored short-term memory: {memory1.title}")
    
    memory2 = memory_manager.store_long_term_memory(
        title="User is a software developer",
        content="The user works as a software developer and enjoys coding",
        importance=0.9
    )
    print(f"✅ Stored long-term memory: {memory2.title}")
    
    # Test memory retrieval
    short_term = memory_manager.get_short_term_memory()
    long_term = memory_manager.get_long_term_memory()
    
    print(f"✅ Retrieved {len(short_term)} short-term memories")
    print(f"✅ Retrieved {len(long_term)} long-term memories")
    
    # Create a test conversation
    conversation = Conversation.objects.create(
        user=user,
        title="Test Memory Conversation"
    )
    print(f"✅ Created test conversation: {conversation.title}")
    
    # Test context manager
    context_manager = ContextManager(conversation.id, user)
    
    # Build context for AI
    context = context_manager.build_context_for_ai("I need some help with programming")
    print(f"✅ Built AI context with {len(context['relevant_memories'])} relevant memories")
    
    # Test message creation and analysis
    message = Message.objects.create(
        conversation=conversation,
        content="I really love drinking coffee while coding in Python",
        is_from_user=True
    )
    
    message_info = memory_manager.extract_important_information(
        message.content,
        is_from_user=True
    )
    print(f"✅ Message importance score: {message_info['importance_score']}")
    
    print("\n🎉 All memory system tests passed!")
    print("\n📊 Memory System Summary:")
    print(f"   - Short-term memories: {len(short_term)}")
    print(f"   - Long-term memories: {len(long_term)}")
    print(f"   - User personality style: {personality['communication_style']}")
    print(f"   - Test conversation ID: {conversation.id}")

if __name__ == "__main__":
    test_memory_system()
