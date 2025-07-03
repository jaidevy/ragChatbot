"""
Django management command to clean up old memories
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from chatbot.models import ConversationMemory
from chatbot.memory_manager import MemoryManager
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Clean up old memories and promote important short-term memories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to keep short-term memories (default: 7)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        days = options.get('days', 7)
        
        self.stdout.write('Starting memory cleanup...')
        
        # Get expired memories
        cutoff_date = timezone.now() - timedelta(days=days)
        expired_memories = ConversationMemory.objects.filter(
            memory_type='short_term',
            created_at__lt=cutoff_date
        )
        
        # Separate important from unimportant
        important_expired = expired_memories.filter(importance_score__gte=0.7)
        unimportant_expired = expired_memories.filter(importance_score__lt=0.7)
        
        self.stdout.write(f'Found {expired_memories.count()} expired short-term memories')
        self.stdout.write(f'  - {important_expired.count()} important (will be promoted)')
        self.stdout.write(f'  - {unimportant_expired.count()} unimportant (will be deleted)')
        
        if not dry_run:
            # Promote important memories to long-term
            promoted_count = 0
            for memory in important_expired:
                memory.memory_type = 'long_term'
                memory.expires_at = None
                memory.save()
                promoted_count += 1
            
            # Delete unimportant memories
            deleted_count = unimportant_expired.count()
            unimportant_expired.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cleanup completed: promoted {promoted_count}, deleted {deleted_count} memories'
                )
            )
        else:
            self.stdout.write(self.style.WARNING('Dry run - no changes made'))
        
        # Clean up user-specific memories
        users_with_memories = ConversationMemory.objects.values_list('user', flat=True).distinct()
        
        for user_id in users_with_memories:
            try:
                user = User.objects.get(id=user_id)
                memory_manager = MemoryManager(user)
                
                if not dry_run:
                    memory_manager._cleanup_short_term_memory()
                
                self.stdout.write(f'Cleaned up memories for user: {user.username}')
                
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'User with ID {user_id} no longer exists')
                )
        
        self.stdout.write(self.style.SUCCESS('Memory cleanup completed successfully'))
