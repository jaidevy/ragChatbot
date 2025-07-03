from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import get_object_or_404
import requests
import tempfile
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Document
from .chroma_helpers import build_or_update_chroma_index
from .pinecone_helpers import build_or_update_pinecone_index

User = get_user_model()


class TrainView(View):
    """
    View to train a vector index (Pinecone or ChromaDB)
    """

    def get(self, request, object_id):
        # Check if user is staff or superuser
        if not request.user.is_staff and not request.user.is_superuser:
            return HttpResponseForbidden("You don't have permission to access this page.")

        # Use get_object_or_404 for better error handling
        document = get_object_or_404(Document, pk=object_id)
        
        try:
            # Determine file path based on storage backend
            if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') and settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
                # Production: AWS S3 storage - need to download file
                file_url = document.file.url
                
                # Ensure URL is absolute
                if not file_url.startswith(('http://', 'https://')):
                    # Construct full URL for S3
                    if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN'):
                        file_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}{file_url}"
                    else:
                        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com{file_url}"
                
                # Download the file
                response = requests.get(file_url, timeout=30)
                response.raise_for_status()
                
                temp_dir = tempfile.mkdtemp()
                file_name = os.path.join(temp_dir, os.path.basename(document.file.name))

                with open(file_name, 'wb') as f:
                    f.write(response.content)

                file_path = file_name
                cleanup_needed = True
                
            else:
                # Local development: use direct file path
                file_path = document.file.path
                cleanup_needed = False

            # Load and process files
            if document.storage_type == 'CHROMA':
                # Use ChromaDB for training
                build_or_update_chroma_index(
                    file_path=file_path,
                    index_name=document.index_name
                )
                document.is_trained = True
                document.save()
            elif document.storage_type == 'PINECONE':
                # Use Pinecone for training
                build_or_update_pinecone_index(
                    file_path=file_path,
                    index_name=document.index_name,
                    name_space=settings.PINECONE_NAMESPACE_NAME
                )
                document.is_trained = True
                document.save()

            # Clean up the temporary directory if needed
            if cleanup_needed:
                os.remove(file_path)
                os.rmdir(temp_dir)

            # Redirect to Django admin with a success message
            messages.success(request, "Training complete.")
            admin_url = reverse('admin:training_model_document_change', args=[object_id])
            return HttpResponseRedirect(admin_url)
            
        except requests.RequestException as e:
            messages.error(request, f"Failed to download file: {e}")
            admin_url = reverse('admin:training_model_document_change', args=[object_id])
            return HttpResponseRedirect(admin_url)
        except Exception as e:
            messages.error(request, f"Training failed: {e}")
            admin_url = reverse('admin:training_model_document_change', args=[object_id])
            return HttpResponseRedirect(admin_url)
