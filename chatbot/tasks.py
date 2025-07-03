import pickle
import os
import openai
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# from langchain.vectorstores import FAISS as BaseFAISS
from training_model.pinecone_helpers import (
    PineconeManager,
    PineconeIndexManager,
    embeddings,
)
from langchain_community.vectorstores import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth import get_user_model
from .memory_manager import MemoryManager, ContextManager

logger = get_task_logger(__name__)
User = get_user_model()

PINECONE_API_KEY = settings.PINECONE_API_KEY
PINECONE_ENVIRONMENT = settings.PINECONE_ENVIRONMENT
PINECONE_INDEX_NAME = settings.PINECONE_INDEX_NAME
OPENAI_API_KEY = settings.OPENAI_API_KEY

chat = ChatOpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)


#
# class FAISS(BaseFAISS):
#     """
#     FAISS is a vector store that uses the FAISS library to store and search vectors.
#     """
#
#     def save(self, file_path):
#         with open(file_path, "wb") as f:
#             pickle.dump(self, f)
#
#     @staticmethod
#     def load(file_path):
#         with open(file_path, "rb") as f:
#             return pickle.load(f)

#
# def get_faiss_index(index_name):
#     faiss_obj_path = os.path.join(settings.BASE_DIR, "models", "{}.pickle".format(index_name))
#
#     if os.path.exists(faiss_obj_path):
#         # Load the FAISS object from disk
#         try:
#             faiss_index = FAISS.load(faiss_obj_path)
#             return faiss_index
#         except Exception as e:
#             logger.error(f"Failed to load FAISS index: {e}")
#             return None

def get_pinecone_index(index_name, name_space):
    pinecone_manager = PineconeManager(PINECONE_API_KEY, PINECONE_ENVIRONMENT)
    pinecone_index_manager = PineconeIndexManager(pinecone_manager, index_name)

    try:
        pinecone_index = Pinecone.from_existing_index(index_name=pinecone_index_manager.index_name,
                                                      embedding=embeddings, namespace=settings.PINECONE_NAMESPACE_NAME)
        # pinecone_index = Pinecone.from_existing_index(index_name=pinecone_index_manager.index_name,
        #                                               namespace=name_space, embedding=embeddings)
        return pinecone_index

    except Exception as e:
        logger.error(f"Failed to load Pinecone index: {e}")
        return None


@shared_task
def send_gpt_request_with_memory(message_list, user_id, conversation_id, name_space, system_prompt):
    """
    Enhanced GPT request with seamless RAG and memory integration
    """
    try:
        user = User.objects.get(id=user_id)
        memory_manager = MemoryManager(user)
        context_manager = ContextManager(conversation_id, user)
        
        # Get the current user message
        current_message = message_list[-1]["content"] if message_list else ""
        
        # Load the Pinecone index for RAG retrieval
        base_index = get_pinecone_index(PINECONE_INDEX_NAME, name_space)
        
        rag_docs = []
        if base_index:
            try:
                # Perform similarity search on the knowledge base
                rag_docs = base_index.similarity_search(query=current_message, k=3)
            except Exception as e:
                logger.error(f"Failed to get similar documents: {e}")
        
        # Get memory-enhanced context
        relevant_memories = memory_manager.get_rag_enhanced_memories(current_message, limit=5)
        
        # Build comprehensive context with both RAG and memory
        ai_context = context_manager.build_rag_aware_context(current_message, rag_docs)
        
        # Merge RAG documents and memories into a unified context
        merged_context = memory_manager.merge_rag_and_memory_context(rag_docs, relevant_memories)
        
        # Create the enhanced user message with both RAG and memory context
        if merged_context:
            enhanced_message = f"{merged_context}\n\nUser question: {current_message}"
            message_list[-1] = {"role": "user", "content": enhanced_message}
        
        # Build enhanced system prompt
        enhanced_system_prompt = build_enhanced_system_prompt(system_prompt, ai_context)
        
        # Add conversational context
        memory_context = build_memory_context_messages(ai_context)
        
        # Prepare messages for GPT
        gpt_messages = [
            {"role": "system", "content": enhanced_system_prompt}
        ] + memory_context + message_list
        
        openai.api_key = settings.OPENAI_API_KEY
        
        # Send request to GPT with enhanced context
        gpt3_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=gpt_messages,
            temperature=0.7,
            max_tokens=2000
        )

        assistant_response = gpt3_response["choices"][0]["message"]["content"].strip()
        
        # Process the AI response and update memories
        context_manager.process_ai_response(assistant_response, current_message)
        
        # Store conversation summary if needed
        update_conversation_summary.delay(conversation_id, message_list, assistant_response)
        
        # If RAG documents were used, store their topics as potential memories
        if rag_docs and ai_context.get('rag_topics'):
            for topic in ai_context['rag_topics'][:3]:
                memory_manager.store_short_term_memory(
                    title=f"Discussed topic: {topic}",
                    content=f"User asked about {topic} in context of: {current_message[:100]}",
                    context={
                        'conversation_id': conversation_id,
                        'source': 'rag_retrieval'
                    },
                    importance=0.5
                )
        
        return assistant_response

    except Exception as e:
        logger.error(f"Failed to send request to GPT-3.5 with memory: {e}")
        return "Sorry, I'm having trouble understanding you. Could you please rephrase your question?"


def build_enhanced_system_prompt(base_prompt: str, ai_context: Dict[str, Any]) -> str:
    """
    Build enhanced system prompt with memory and personality context
    """
    personality = ai_context.get('user_personality', {})
    relevant_memories = ai_context.get('relevant_memories', [])
    rag_documents = ai_context.get('rag_documents', [])
    
    enhanced_prompt = base_prompt + "\n\n"
    
    # Add personality context
    if personality:
        enhanced_prompt += f"User Communication Style: {personality.get('communication_style', 'casual')}\n"
        if personality.get('interests'):
            enhanced_prompt += f"User Interests: {', '.join(personality['interests'])}\n"
        if personality.get('preferences'):
            enhanced_prompt += f"User Preferences: {json.dumps(personality['preferences'])}\n"
    
    # Add memory context
    if relevant_memories:
        enhanced_prompt += "\nRelevant information from past conversations:\n"
        for memory in relevant_memories[:3]:
            enhanced_prompt += f"- {memory['title']}: {memory['content'][:200]}...\n"
    
    enhanced_prompt += "\nInstructions:\n"
    enhanced_prompt += "- Use both the knowledge base information and personal conversation history to provide accurate, personalized responses\n"
    enhanced_prompt += "- Reference previous conversations naturally when relevant\n"
    enhanced_prompt += "- Maintain consistency with past interactions and user preferences\n"
    enhanced_prompt += "- If the knowledge base and personal memory conflict, clarify the discrepancy\n"
    enhanced_prompt += "- Be conversational and natural, not robotic\n"
    
    return enhanced_prompt


def build_memory_context_messages(ai_context: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build memory context messages for the conversation
    """
    context_messages = []
    
    # Add short-term memory context
    short_term_memories = ai_context.get('short_term_memory', [])
    if short_term_memories:
        memory_content = "Recent conversation context:\n"
        for memory in short_term_memories[:5]:  # Limit to 5 recent memories
            memory_content += f"- {memory['title']}: {memory['content'][:100]}...\n"
        
        context_messages.append({
            "role": "system",
            "content": memory_content
        })
    
    return context_messages


@shared_task
def generate_title_request(message_list):
    try:
        openai.api_key = settings.OPENAI_API_KEY
        # Send request to GPT-3 (replace with actual GPT-3 API call)
        gpt3_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                         {"role": "system",
                          "content": "Summarize and make a very short meaningful title under 24 characters"},
                     ] + message_list
        )
        response = gpt3_response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Failed to send request to GPT-3.5: {e}")
        return "Problematic title with error."
    return response


@shared_task
def update_conversation_summary(conversation_id, message_list, latest_response):
    """
    Update conversation summary and extract key information
    """
    try:
        from .models import Conversation, Message
        
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Build conversation text for analysis
        conversation_text = ""
        for msg in message_list[-10:]:  # Analyze last 10 messages
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"
        
        conversation_text += f"Assistant: {latest_response}\n"
        
        # Use GPT to extract key topics and generate summary
        openai.api_key = settings.OPENAI_API_KEY
        
        analysis_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """Analyze this conversation and extract:
                    1. Key topics discussed (max 5, return as comma-separated list)
                    2. Overall sentiment (positive/negative/neutral)
                    3. Important information that should be remembered
                    4. Brief summary (max 2 sentences)
                    
                    Return your response in JSON format:
                    {
                        "key_topics": ["topic1", "topic2"],
                        "sentiment": "positive",
                        "important_info": "key information to remember",
                        "summary": "brief summary"
                    }"""
                },
                {
                    "role": "user",
                    "content": conversation_text
                }
            ],
            temperature=0.3
        )
        
        analysis_result = analysis_response["choices"][0]["message"]["content"].strip()
        
        try:
            analysis_data = json.loads(analysis_result)
            
            # Update conversation with extracted information
            conversation.key_topics = analysis_data.get("key_topics", [])
            conversation.sentiment_analysis = {
                "overall_sentiment": analysis_data.get("sentiment", "neutral"),
                "last_updated": datetime.now().isoformat()
            }
            conversation.conversation_summary = analysis_data.get("summary", "")
            conversation.save()
            
            # Store important information as long-term memory if significant
            important_info = analysis_data.get("important_info", "")
            if important_info and len(important_info) > 20:
                user = conversation.user
                memory_manager = MemoryManager(user)
                memory_manager.store_long_term_memory(
                    title=f"Important info from {conversation.title}",
                    content=important_info,
                    context={"conversation_id": conversation_id},
                    importance=0.8
                )
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis result for conversation {conversation_id}")
            
    except Exception as e:
        logger.error(f"Failed to update conversation summary: {e}")


@shared_task
def analyze_message_importance(message_id):
    """
    Analyze message importance and update importance score
    """
    try:
        from .models import Message
        
        message = Message.objects.get(id=message_id)
        user = message.conversation.user
        memory_manager = MemoryManager(user)
        
        # Extract importance information
        message_info = memory_manager.extract_important_information(
            message.content, 
            message.is_from_user
        )
        
        # Update message with extracted information
        message.importance_score = message_info['importance_score']
        message.save()
        
        # If importance is high, store as memory
        if message_info['importance_score'] > 0.6:
            memory_manager.store_short_term_memory(
                title=f"Important message: {message.content[:50]}...",
                content=message.content,
                context={
                    "conversation_id": message.conversation.id,
                    "message_id": message.id,
                    "is_from_user": message.is_from_user
                },
                importance=message_info['importance_score']
            )
        
    except Exception as e:
        logger.error(f"Failed to analyze message importance: {e}")


@shared_task
def cleanup_old_memories():
    """
    Periodic task to clean up old memories and promote important ones
    """
    try:
        from .models import ConversationMemory
        from django.utils import timezone
        
        # Get all users with memories
        users_with_memories = ConversationMemory.objects.values_list('user', flat=True).distinct()
        
        for user_id in users_with_memories:
            user = User.objects.get(id=user_id)
            memory_manager = MemoryManager(user)
            
            # Promote important short-term memories to long-term
            important_short_term = ConversationMemory.objects.filter(
                user=user,
                memory_type='short_term',
                importance_score__gte=0.7,
                created_at__lt=timezone.now() - timedelta(hours=12)
            )
            
            for memory in important_short_term:
                memory_manager.promote_to_long_term(memory.id)
        
        logger.info("Completed memory cleanup and promotion")
        
    except Exception as e:
        logger.error(f"Failed to cleanup memories: {e}")


@shared_task
def periodic_memory_maintenance():
    """
    Periodic task to maintain memory system health
    Run this daily via Celery beat
    """
    try:
        from .models import ConversationMemory
        from django.utils import timezone
        
        # Get all users with memories
        users_with_memories = ConversationMemory.objects.values_list('user', flat=True).distinct()
        
        maintenance_stats = {
            'users_processed': 0,
            'memories_promoted': 0,
            'memories_cleaned': 0,
            'contexts_updated': 0
        }
        
        for user_id in users_with_memories:
            try:
                user = User.objects.get(id=user_id)
                memory_manager = MemoryManager(user)
                
                # Promote important short-term memories
                important_short_term = ConversationMemory.objects.filter(
                    user=user,
                    memory_type='short_term',
                    importance_score__gte=0.7,
                    created_at__lt=timezone.now() - timedelta(hours=12)
                )
                
                promoted_count = 0
                for memory in important_short_term:
                    if memory_manager.promote_to_long_term(memory.id):
                        promoted_count += 1
                
                # Clean up old memories
                memory_manager._cleanup_short_term_memory()
                
                # Update conversation contexts
                active_conversations = user.conversation_set.filter(
                    updated_at__gte=timezone.now() - timedelta(days=7)
                )
                
                for conversation in active_conversations:
                    context_manager = ContextManager(conversation.id, user)
                    # Update context based on recent activity
                    
                maintenance_stats['users_processed'] += 1
                maintenance_stats['memories_promoted'] += promoted_count
                
            except User.DoesNotExist:
                logger.warning(f"User {user_id} no longer exists during memory maintenance")
                continue
        
        logger.info(f"Memory maintenance completed: {maintenance_stats}")
        return maintenance_stats
        
    except Exception as e:
        logger.error(f"Failed to run memory maintenance: {e}")
        return None


@shared_task
def extract_and_store_conversation_memories(conversation_id):
    """
    Extract important information from a conversation and store as memories
    """
    try:
        from .models import Conversation
        
        conversation = Conversation.objects.get(id=conversation_id)
        user = conversation.user
        memory_manager = MemoryManager(user)
        
        # Get all messages from the conversation
        messages = conversation.message_set.all().order_by('created_at')
        
        # Build conversation text
        conversation_text = ""
        for message in messages:
            role = "User" if message.is_from_user else "Assistant"
            conversation_text += f"{role}: {message.content}\n"
        
        # Use GPT to extract key information
        openai.api_key = settings.OPENAI_API_KEY
        
        extraction_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """Analyze this conversation and extract important information that should be remembered about the user. Focus on:
                    1. Personal preferences and interests
                    2. Important life events or information
                    3. Goals, dreams, or aspirations
                    4. Likes, dislikes, and opinions
                    5. Any other memorable details
                    
                    Return a JSON array of memory objects with this format:
                    [
                        {
                            "title": "brief title for the memory",
                            "content": "detailed content to remember",
                            "importance": 0.8,
                            "category": "preference|personal|goal|opinion|other"
                        }
                    ]"""
                },
                {
                    "role": "user",
                    "content": conversation_text[:4000]  # Limit to avoid token limits
                }
            ],
            temperature=0.3
        )
        
        extraction_result = extraction_response["choices"][0]["message"]["content"].strip()
        
        try:
            memories_to_store = json.loads(extraction_result)
            
            stored_count = 0
            for memory_data in memories_to_store:
                memory_manager.store_long_term_memory(
                    title=memory_data.get('title', 'Extracted memory'),
                    content=memory_data.get('content', ''),
                    context={
                        'conversation_id': conversation_id,
                        'category': memory_data.get('category', 'other'),
                        'extracted_at': datetime.now().isoformat()
                    },
                    importance=memory_data.get('importance', 0.7)
                )
                stored_count += 1
            
            logger.info(f"Stored {stored_count} memories from conversation {conversation_id}")
            return stored_count
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse memory extraction result for conversation {conversation_id}")
            return 0
            
    except Exception as e:
        logger.error(f"Failed to extract memories from conversation {conversation_id}: {e}")
        return 0


# Keep the original function for backward compatibility
@shared_task
def send_gpt_request(message_list, name_space, system_prompt):
    """
    Original GPT request function (kept for backward compatibility)
    """
    try:
        # Load the Pinecone index
        base_index = get_pinecone_index(PINECONE_INDEX_NAME, name_space)

        if base_index:
            # Add extra text to the content of the last message
            last_message = message_list[-1]
            query_text = last_message["content"]

            # Get the most similar documents to the last message
            try:
                docs = base_index.similarity_search(query=last_message["content"], k=2)

                updated_content = '"""'
                for doc in docs:
                    updated_content += doc.page_content + "\n\n"
                updated_content += '"""\nQuestion:' + query_text
            except Exception as e:
                logger.error(f"Failed to get similar documents: {e}")
                updated_content = query_text

            updated_message = {"role": "user", "content": updated_content}
            message_list[-1] = updated_message

        openai.api_key = settings.OPENAI_API_KEY
        gpt3_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
            ] + message_list
        )

        assistant_response = gpt3_response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Failed to send request to GPT-3.5: {e}")
        return "Sorry, I'm having trouble understanding you."
    return assistant_response


@shared_task
def analyze_rag_response_importance(message_id, rag_docs_used):
    """
    Analyze importance of messages that used RAG documents
    """
    try:
        from .models import Message
        
        message = Message.objects.get(id=message_id)
        
        # If RAG documents were used, increase importance
        base_importance = message.importance_score
        if rag_docs_used and len(rag_docs_used) > 0:
            # Increase importance based on number of relevant docs found
            importance_boost = min(0.2 * len(rag_docs_used), 0.5)
            message.importance_score = min(base_importance + importance_boost, 1.0)
            message.save()
            
            # Store metadata about RAG usage
            if not message.entities:
                message.entities = []
            message.entities.append({
                'type': 'rag_retrieval',
                'doc_count': len(rag_docs_used),
                'timestamp': datetime.now().isoformat()
            })
            message.save()
            
    except Exception as e:
        logger.error(f"Failed to analyze RAG response importance: {e}")
