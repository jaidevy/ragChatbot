"""
Django management command to demonstrate the memory system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from chatbot.models import Conversation, Message
from chatbot.memory_manager import MemoryManager, ContextManager
from chatbot.tasks import send_gpt_request_with_memory
import asyncio

User = get_user_model()


class Command(BaseCommand):
    help = 'Demonstrate the chatbot memory system with interactive conversation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to use for the demo (will create if not exists)',
            default='demo_user'
        )

    def handle(self, *args, **options):
        username = options['user']
        
        # Create or get demo user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': 'Demo',
                'last_name': 'User'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created demo user: {username}')
            )
        else:
            self.stdout.write(f'Using existing user: {username}')
        
        # Initialize memory system
        memory_manager = MemoryManager(user)
        
        # Set up user personality
        memory_manager.update_user_personality(
            communication_style='friendly',
            interests=['technology', 'AI', 'programming'],
            preferences={
                'response_length': 'medium',
                'formality': 'casual',
                'explanation_detail': 'comprehensive'
            }
        )
        
        # Add some sample memories
        self.setup_sample_memories(memory_manager)
        
        # Create a conversation
        conversation = Conversation.objects.create(
            user=user,
            title="Memory System Demo"
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created conversation: {conversation.id}')
        )
        
        # Interactive demo
        self.run_interactive_demo(user, conversation, memory_manager)

    def setup_sample_memories(self, memory_manager):
        """Set up sample memories for the demo"""
        
        # Long-term memories
        memory_manager.store_long_term_memory(
            title="User is a software developer",
            content="The user works as a full-stack developer with 5 years of experience, specializing in Python and React",
            importance=0.9
        )
        
        memory_manager.store_long_term_memory(
            title="User loves coffee",
            content="The user drinks coffee every morning and prefers dark roast. Favorite coffee shop is Blue Bottle",
            importance=0.6
        )
        
        memory_manager.store_long_term_memory(
            title="User has a pet dog",
            content="The user has a golden retriever named Max who is 3 years old",
            importance=0.7
        )
        
        # Short-term memories
        memory_manager.store_short_term_memory(
            title="Recent project discussion",
            content="User mentioned working on a React project with API integration challenges",
            importance=0.5
        )
        
        self.stdout.write(
            self.style.SUCCESS('✅ Sample memories created')
        )

    def run_interactive_demo(self, user, conversation, memory_manager):
        """Run an interactive demo of the memory system"""
        
        context_manager = ContextManager(conversation.id, user)
        
        self.stdout.write(
            self.style.WARNING('\n🧠 Memory System Demo Started!')
        )
        self.stdout.write(
            self.style.WARNING('Type "quit" to exit, "memories" to see stored memories\n')
        )
        
        # Sample conversation messages to establish context
        sample_messages = [
            "Hi! I'm having trouble with my React project.",
            "I need help integrating a REST API.",
            "The API calls are working but I'm having CORS issues."
        ]
        
        message_list = []
        
        for i, msg_content in enumerate(sample_messages):
            # Create user message
            message = Message.objects.create(
                conversation=conversation,
                content=msg_content,
                is_from_user=True
            )
            
            message_list.append({"role": "user", "content": msg_content})
            
            # Build context for AI
            ai_context = context_manager.build_context_for_ai(msg_content)
            
            self.stdout.write(f'User: {msg_content}')
            
            # Show memory context
            relevant_memories = ai_context.get('relevant_memories', [])
            if relevant_memories:
                self.stdout.write(
                    self.style.SUCCESS(f'🧠 Retrieved {len(relevant_memories)} relevant memories')
                )
                for memory in relevant_memories:
                    self.stdout.write(f'   - {memory["title"]}')
            
            # Simulate AI response (simplified for demo)
            if i == 0:
                ai_response = "I remember you're a full-stack developer with Python and React experience! What specific issues are you facing with your React project?"
            elif i == 1:
                ai_response = "Since you're working on API integration, I can help with that. Are you using fetch or axios for your HTTP requests?"
            else:
                ai_response = "CORS issues are common in React development. You might need to configure your backend to allow cross-origin requests. What's your backend setup?"
            
            # Create AI message
            ai_message = Message.objects.create(
                conversation=conversation,
                content=ai_response,
                is_from_user=False,
                in_reply_to=message
            )
            
            message_list.append({"role": "assistant", "content": ai_response})
            
            self.stdout.write(
                self.style.SUCCESS(f'Assistant: {ai_response}\n')
            )
            
            # Process the response for memory updates
            context_manager.process_ai_response(ai_response, msg_content)
        
        # Interactive portion
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'memories':
                    self.show_memories(memory_manager)
                    continue
                elif not user_input:
                    continue
                
                # Build context for AI
                ai_context = context_manager.build_context_for_ai(user_input)
                
                # Show relevant memories
                relevant_memories = ai_context.get('relevant_memories', [])
                if relevant_memories:
                    self.stdout.write(
                        self.style.SUCCESS(f'🧠 Using {len(relevant_memories)} relevant memories')
                    )
                
                # Create user message
                message = Message.objects.create(
                    conversation=conversation,
                    content=user_input,
                    is_from_user=True
                )
                
                message_list.append({"role": "user", "content": user_input})
                
                # Keep only recent messages for API call
                recent_messages = message_list[-10:] if len(message_list) > 10 else message_list
                
                # For demo, provide contextual responses
                self.stdout.write(
                    self.style.SUCCESS('Assistant: I understand your question and I\'m using our conversation history and your preferences to provide a personalized response. In a real scenario, this would be processed by the enhanced GPT system with full memory context.')
                )
                
                # Process for memory updates
                context_manager.process_ai_response("Demo response", user_input)
                
            except KeyboardInterrupt:
                break
            except EOFError:
                break
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Demo completed! Check the database to see stored memories.')
        )

    def show_memories(self, memory_manager):
        """Display current memories"""
        self.stdout.write(self.style.WARNING('\n📚 Current Memories:'))
        
        # Short-term memories
        short_term = memory_manager.get_short_term_memory()
        self.stdout.write(f'\n🔄 Short-term ({len(short_term)}):')
        for memory in short_term:
            self.stdout.write(f'   - {memory["title"]} (score: {memory["importance_score"]:.2f})')
        
        # Long-term memories
        long_term = memory_manager.get_long_term_memory()
        self.stdout.write(f'\n💾 Long-term ({len(long_term)}):')
        for memory in long_term:
            self.stdout.write(f'   - {memory["title"]} (score: {memory["importance_score"]:.2f})')
        
        # User personality
        personality = memory_manager.get_user_personality()
        self.stdout.write(f'\n👤 Personality:')
        self.stdout.write(f'   - Style: {personality["communication_style"]}')
        self.stdout.write(f'   - Interests: {", ".join(personality["interests"])}')
        
        self.stdout.write('')
