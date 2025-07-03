from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from celery.result import AsyncResult
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from .tasks import send_gpt_request, send_gpt_request_with_memory, generate_title_request, analyze_message_importance
from .memory_manager import MemoryManager, ContextManager

User = get_user_model()


class LastMessagesPagination(LimitOffsetPagination):
    """
    Pagination class for last messages.
    """
    default_limit = 10
    max_limit = 10


# List and create conversations
class ConversationListCreate(generics.ListCreateAPIView):
    """
    List and create conversations.
    """
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).order_by('created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# Retrieve, update, and delete a specific conversation
class ConversationDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete a specific conversation.
    """
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        conversation = self.get_object()
        if conversation.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().delete(request, *args, **kwargs)


# Archive a conversation
class ConversationArchive(APIView):
    """
    Archive a conversation.
    """

    def patch(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        if conversation.archive:
            conversation.archive = False
            conversation.save()
            return Response({"message": "remove from archive"}, status=status.HTTP_200_OK)
        else:
            conversation.archive = True
            conversation.save()
            return Response({"message": "add to archive"}, status=status.HTTP_200_OK)


class ConversationFavourite(APIView):
    """
    Favourite a conversation.
    """

    def patch(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        if conversation.favourite:
            conversation.favourite = False
            conversation.save()
            return Response({"message": "remove from favourite"}, status=status.HTTP_200_OK)
        else:
            conversation.favourite = True
            conversation.save()
            return Response({"message": "add to favourite"}, status=status.HTTP_200_OK)


# Delete a conversation
class ConversationDelete(APIView):
    """
    Delete a conversation.
    """

    def delete(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        conversation.delete()
        return Response({"message": "conversation deleted"}, status=status.HTTP_200_OK)


# List messages in a conversation
class MessageList(generics.ListAPIView):
    """
    List messages in a conversation.
    """
    serializer_class = MessageSerializer
    pagination_class = LastMessagesPagination

    def get_queryset(self):
        conversation = get_object_or_404(Conversation, id=self.kwargs['conversation_id'], user=self.request.user)
        return Message.objects.filter(conversation=conversation).select_related('conversation')


# Create a message in a conversation
class MessageCreate(generics.CreateAPIView):
    """
    Create a message in a conversation with enhanced memory and RAG integration.
    """
    serializer_class = MessageSerializer

    def perform_create(self, serializer):
        conversation = get_object_or_404(Conversation, id=self.kwargs['conversation_id'], user=self.request.user)
        message = serializer.save(conversation=conversation, is_from_user=True)

        # Initialize memory manager for this user
        memory_manager = MemoryManager(self.request.user)
        context_manager = ContextManager(conversation.id, self.request.user)

        # Analyze message importance asynchronously
        analyze_message_importance.delay(message.id)

        # Retrieve conversation context (last 10 messages)
        messages = Message.objects.filter(conversation=conversation).order_by('-created_at')[:10][::-1]

        # Build the message list for GPT
        message_list = []
        for msg in messages:
            if msg.is_from_user:
                message_list.append({"role": "user", "content": msg.content})
            else:
                message_list.append({"role": "assistant", "content": msg.content})

        name_space = User.objects.get(id=self.request.user.id).username

        from site_settings.models import SiteSetting
        # Get system prompt from site settings
        try:
            system_prompt_obj = SiteSetting.objects.first()
            base_prompt = system_prompt_obj.prompt
            # Enhance the base prompt for RAG + Memory integration
            system_prompt = f"{base_prompt}\n\nYou have access to both a knowledge base and the user's conversation history. Use both sources to provide accurate, personalized, and contextually relevant responses."
        except Exception as e:
            print(str(e))
            system_prompt = """You are a helpful AI assistant with access to a knowledge base and excellent memory capabilities. 
            You remember past conversations, user preferences, and important information to provide personalized and contextually aware responses.
            Always strive to provide accurate information from the knowledge base while maintaining a natural, conversational tone."""

        # Use the enhanced GPT request with memory and RAG
        task = send_gpt_request_with_memory.apply_async(
            args=(message_list, self.request.user.id, conversation.id, name_space, system_prompt)
        )
        
        response = task.get()
        
        return [response, conversation.id, message.id]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response_list = self.perform_create(serializer)
        assistant_response = response_list[0]
        conversation_id = response_list[1]
        last_user_message_id = response_list[2]

        try:
            # Store GPT response as a message
            ai_message = Message(
                conversation_id=conversation_id,
                content=assistant_response,
                is_from_user=False,
                in_reply_to_id=last_user_message_id
            )
            ai_message.save()
            
            # Analyze AI message importance
            analyze_message_importance.delay(ai_message.id)
            
            # Update conversation context
            conversation = Conversation.objects.get(id=conversation_id)
            conversation.updated_at = timezone.now()
            conversation.save()

        except ObjectDoesNotExist:
            error = f"Conversation with id {conversation_id} does not exist"
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_msg = str(e)
            error = f"Failed to save assistant response: {error_msg}"
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response({
            "response": assistant_response,
            "message_id": ai_message.id,
            "conversation_id": conversation_id
        }, status=status.HTTP_200_OK, headers=headers)


class ConversationRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    Retrieve View to update or get the title
    """
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    lookup_url_kwarg = 'conversation_id'

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()

        if conversation.title == "Empty":
            messages = Message.objects.filter(conversation=conversation)

            if messages.exists():
                message_list = []
                for msg in messages:
                    if msg.is_from_user:
                        message_list.append({"role": "user", "content": msg.content})
                    else:
                        message_list.append({"role": "assistant", "content": msg.content})

                task = generate_title_request.apply_async(args=(message_list,))
                my_title = task.get()
                # if length of title is greater than 55, truncate it
                my_title = my_title[:30]
                conversation.title = my_title
                conversation.save()
                serializer = self.get_serializer(conversation)
                return Response(serializer.data)
            else:
                return Response({"message": "No messages in conversation."}, status=status.HTTP_204_NO_CONTENT)
        else:
            serializer = self.get_serializer(conversation)
            return Response(serializer.data)


class GPT3TaskStatus(APIView):
    """
    Check the status of a GPT task and return the result if it's ready.
    """

    def get(self, request, task_id, *args, **kwargs):
        task = AsyncResult(task_id)

        if task.ready():
            response = task.result
            return Response({"status": "READY", "response": response})
        else:
            return Response({"status": "PENDING"})


class MemoryListView(APIView):
    """
    API view to list user memories
    """
    
    def get(self, request):
        memory_type = request.query_params.get('type', 'all')
        limit = int(request.query_params.get('limit', 20))
        
        memory_manager = MemoryManager(request.user)
        
        if memory_type == 'short_term':
            memories = memory_manager.get_short_term_memory(limit=limit)
        elif memory_type == 'long_term':
            memories = memory_manager.get_long_term_memory(limit=limit)
        else:
            short_term = memory_manager.get_short_term_memory(limit=limit//2)
            long_term = memory_manager.get_long_term_memory(limit=limit//2)
            memories = {
                'short_term': short_term,
                'long_term': long_term
            }
        
        return Response(memories, status=status.HTTP_200_OK)


class UserMemoryListView(generics.ListAPIView):
    """
    List user's memories with pagination and filtering
    """
    serializer_class = MessageSerializer  # We'll create a MemorySerializer later
    pagination_class = LastMessagesPagination

    def get_queryset(self):
        memory_manager = MemoryManager(self.request.user)
        memory_type = self.request.query_params.get('type', 'all')
        
        if memory_type == 'short_term':
            memories = memory_manager.get_short_term_memory(limit=50)
        elif memory_type == 'long_term':
            memories = memory_manager.get_long_term_memory(limit=50)
        else:
            # Return both types
            short_term = memory_manager.get_short_term_memory(limit=25)
            long_term = memory_manager.get_long_term_memory(limit=25)
            memories = short_term + long_term
        
        return memories

    def list(self, request, *args, **kwargs):
        memories = self.get_queryset()
        return Response({
            'memories': memories,
            'count': len(memories)
        })


class ConversationContextView(APIView):
    """
    API view to get conversation context and memory information
    """
    
    def get(self, request, conversation_id):
        try:
            # Verify user owns the conversation
            conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
            
            memory_manager = MemoryManager(request.user)
            context = memory_manager.get_conversation_context(conversation_id)
            
            return Response(context, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to get conversation context: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class UserPersonalityView(APIView):
    """
    API view to get and update user personality profile
    """
    
    def get(self, request):
        memory_manager = MemoryManager(request.user)
        personality = memory_manager.get_user_personality()
        return Response(personality, status=status.HTTP_200_OK)
    
    def patch(self, request):
        memory_manager = MemoryManager(request.user)
        
        # Update personality with provided data
        update_data = {}
        if 'communication_style' in request.data:
            update_data['communication_style'] = request.data['communication_style']
        if 'interests' in request.data:
            update_data['interests'] = request.data['interests']
        if 'preferences' in request.data:
            update_data['preferences'] = request.data['preferences']
        
        memory_manager.update_user_personality(**update_data)
        
        # Return updated personality
        personality = memory_manager.get_user_personality()
        return Response(personality)


class MemorySearchView(APIView):
    """
    API view to search memories
    """
    
    def post(self, request):
        query = request.data.get('query', '')
        memory_type = request.data.get('type', 'all')
        limit = request.data.get('limit', 10)
        
        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        memory_manager = MemoryManager(request.user)
        
        if memory_type == 'long_term':
            memories = memory_manager.get_long_term_memory(query=query, limit=limit)
        else:
            # Search both short and long term memories
            short_term = memory_manager.get_short_term_memory(limit=limit//2)
            long_term = memory_manager.get_long_term_memory(query=query, limit=limit//2)
            
            # Filter short term memories by query
            filtered_short_term = [
                m for m in short_term 
                if query.lower() in m['title'].lower() or query.lower() in m['content'].lower()
            ]
            
            memories = filtered_short_term + long_term
        
        return Response({
            'query': query,
            'memories': memories,
            'count': len(memories)
        })


class MemoryPromoteView(APIView):
    """
    Promote short-term memory to long-term
    """
    
    def post(self, request, memory_id):
        memory_manager = MemoryManager(request.user)
        success = memory_manager.promote_to_long_term(memory_id)
        
        if success:
            return Response({'message': 'Memory promoted to long-term storage'})
        else:
            return Response(
                {'error': 'Failed to promote memory. Check if memory exists and meets importance threshold.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
