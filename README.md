# Dynamic AI Chatbot with Custom Training Sources
## Customizable-gpt-chatbot
This project is a dynamic AI chatbot that can be trained from various sources, such as PDFs, documents, websites, and YouTube videos. It uses a user system with social authentication through Google, and the Django REST framework for its backend. The chatbot leverages OpenAI's GPT-3.5 language model to conduct conversations and is designed for scalability and ease of use.

## Core Features

### Knowledge Base Management
- Train chatbot from multiple document sources including PDFs, Word documents, and CSV files
- Support for both Pinecone and ChromaDB vector databases for flexible storage options
- Dynamic document indexing with real-time updates to the knowledge base
- Automatic text processing and embedding generation using OpenAI's text-embedding models
- File upload management with organized storage by vector database type

### Intelligent Conversation System
- Advanced conversational AI powered by OpenAI GPT-3.5 language model
- Context-aware responses that maintain conversation flow and coherence
- Multi-turn conversation support with persistent chat history
- Automatic conversation title generation based on content
- Real-time message processing with background task queuing

### Memory and Personalization
- Advanced memory system with short-term and long-term memory storage
- User personality profiling that learns communication styles and preferences
- Conversation context tracking that remembers important topics and details
- Automatic importance scoring for messages and conversations
- Memory-enhanced responses that reference previous conversations naturally
- Episodic and semantic memory types for different kinds of information retention

### User Management and Authentication
- Comprehensive user system with profile management
- Social authentication integration with Google OAuth
- Secure user sessions with proper authentication backends
- User-specific conversation history and memory isolation
- Personalized chatbot experiences based on user preferences

### Conversation Management
- Persistent conversation storage with unique conversation identifiers
- Conversation archiving and favoriting capabilities
- Advanced conversation search and filtering options
- Conversation summaries generated automatically by AI
- Sentiment analysis tracking for each conversation
- Key topic extraction and categorization

### Advanced AI Integration
- Retrieval-Augmented Generation combining knowledge base with conversational AI
- Smart document similarity search for relevant information retrieval
- Named entity recognition and extraction from user messages
- Intent detection to understand user goals and needs
- Emotion detection in conversations for better response tailoring
- Automatic memory promotion from short-term to long-term based on importance

### API and Integration
- RESTful API with comprehensive documentation using Swagger
- OAuth2 provider integration for secure API access
- Rate limiting and throttling for API protection
- Cross-origin resource sharing support for web applications
- Comprehensive API endpoints for all major functionality

### Background Processing
- Asynchronous task processing using Celery for performance
- Background memory maintenance and cleanup operations
- Scheduled tasks for periodic system optimization
- Message importance analysis performed asynchronously
- Conversation summarization handled in background

### Administrative Features
- Django admin interface for system management
- Document training status tracking and management
- User activity monitoring and analytics
- Memory system statistics and health monitoring
- Conversation analytics and reporting capabilities

### Technical Infrastructure
- Scalable architecture supporting local, staging, and production environments
- PostgreSQL database support for robust data storage
- Redis integration for caching and session management
- AWS S3 integration for scalable file storage
- Comprehensive logging and error tracking
- Security features including CSRF protection and secure headers

### Customization and Configuration
- Dynamic site settings that can be updated without code changes
- Configurable memory settings for different use cases
- Flexible vector database selection per document or conversation
- Customizable personality traits and communication styles
- Adjustable importance thresholds and memory retention policies

### Performance and Scalability
- Efficient vector similarity search for fast information retrieval
- Database indexing for optimized query performance
- Lazy loading and pagination for large datasets
- Caching strategies for frequently accessed information
- Background processing to maintain responsive user experience

## Technologies
- Language: Python
- Framework: Django REST Framework
- Database: PostgreSQL

### Major Libraries:
- Celery
- Langchain 
- OpenAI
- Pinecone
- ChromaDB

## Requirements
- Python 3.8 or above
- Django 4.1 or above
- Pinecone API Key (optional, for Pinecone storage)
- API key from OpenAI
- Redis or AWS SQS
- PostgreSQL database

## Future Scope
- Integration with more third-party services for authentication
- Support for additional file formats and media types for chatbot training
- Improved context-awareness in conversations
- Enhanced multilingual support with automatic language detection
- Integration with popular messaging platforms and chat applications

## How to run
- Clone the repository. `git clone https://github.com/libraiger/ragChatbot`
- Install the required packages by running `pip install -r requirements.txt`
- Run celery `celery -A config worker --loglevel=info`
- Run the command `python manage.py runserver`
- Open `http://127.0.0.1:8000/` in your browser

In linux and mac need to install 'sudo apt install python3-dev -y`
1. Make sure that you have the development libraries for libcurl installed on your system. You can install them by running the following command: `sudo apt-get install libcurl4-openssl-dev gcc libssl-dev -y`
2. Make sure that you have the latest version of pip and setuptools installed by running the following command: `pip install --upgrade pip setuptools`
3. `pip install pycurl`
