"""
Django management command to initialize memory system for existing users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from chatbot.models import UserPersonality, ConversationMemory
from chatbot.memory_manager import MemoryManager

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize memory system for existing users and conversations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Initialize memory for a specific user ID',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old memories while initializing',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        cleanup = options.get('cleanup', False)

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                self.initialize_user_memory(user, cleanup)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {user_id} does not exist')
                )
        else:
            # Initialize memory for all users
            users = User.objects.all()
            self.stdout.write(f'Initializing memory system for {users.count()} users...')
            
            for user in users:
                self.initialize_user_memory(user, cleanup)
            
            self.stdout.write(
                self.style.SUCCESS('Successfully initialized memory system for all users')
            )

    def initialize_user_memory(self, user, cleanup=False):
        """Initialize memory system for a specific user"""
        self.stdout.write(f'Initializing memory for user: {user.username}')
        
        # Create UserPersonality if it doesn't exist
        personality, created = UserPersonality.objects.get_or_create(
            user=user,
            defaults={
                'communication_style': 'casual',
                'interests': [],
                'preferences': {},
                'conversation_patterns': {}
            }
        )
        
        if created:
            self.stdout.write(f'  Created personality profile for {user.username}')
        
        # Initialize memory manager
        memory_manager = MemoryManager(user)
        
        # Clean up old memories if requested
        if cleanup:
            memory_manager._cleanup_short_term_memory()
            self.stdout.write(f'  Cleaned up old memories for {user.username}')
        
        # Get user's conversations and analyze for important information
        conversations = user.conversation_set.all()
        self.stdout.write(f'  Analyzing {conversations.count()} conversations for {user.username}')
        
        for conversation in conversations:
            self.analyze_conversation_for_memory(conversation, memory_manager)
        
        self.stdout.write(
            self.style.SUCCESS(f'  Successfully initialized memory for {user.username}')
        )

    def analyze_conversation_for_memory(self, conversation, memory_manager):
        """Analyze a conversation and extract important information for memory"""
        messages = conversation.message_set.all()
        
        # Look for important user messages
        important_messages = []
        for message in messages:
            if message.is_from_user:
                message_info = memory_manager.extract_important_information(
                    message.content, 
                    is_from_user=True
                )
                if message_info['importance_score'] > 0.5:
                    important_messages.append((message, message_info))
        
        # Store important messages as memories
        for message, info in important_messages:
            memory_title = f"Important from {conversation.title}: {message.content[:50]}..."
            
            # Check if similar memory already exists
            existing_memories = memory_manager.get_long_term_memory(
                query=message.content[:100], 
                limit=5
            )
            
            # Only create if no similar memory exists
            similar_exists = any(
                memory['content'][:100] in message.content or 
                message.content[:100] in memory['content']
                for memory in existing_memories
            )
            
            if not similar_exists:
                memory_manager.store_long_term_memory(
                    title=memory_title,
                    content=message.content,
                    context={
                        'conversation_id': conversation.id,
                        'message_id': message.id,
                        'conversation_title': conversation.title
                    },
                    importance=info['importance_score']
                )
