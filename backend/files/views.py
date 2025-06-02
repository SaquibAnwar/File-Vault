from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.http import Http404

from .models import File, FileReference, StorageStats
from .serializers import (
    FileSerializer, FileReferenceSerializer, FileUploadSerializer,
    FileUploadResponseSerializer, StorageStatsSerializer, FileSearchSerializer
)
from .services import DeduplicationService, FileSearchService

# Create your views here.

class FilePagination(PageNumberPagination):
    """Custom pagination for file listings"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class FileReferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing file references (user uploads)
    """
    queryset = FileReference.objects.select_related('file').all()
    serializer_class = FileReferenceSerializer
    pagination_class = FilePagination
    
    def get_queryset(self):
        """Get queryset with optional search/filtering"""
        queryset = super().get_queryset()
        
        # Apply search and filters if any query parameters are present
        if self.request.query_params:
            queryset = FileSearchService.search_files(self.request.query_params)
        
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Upload a new file with deduplication logic
        """
        # Validate the upload request
        upload_serializer = FileUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        
        uploaded_file = upload_serializer.validated_data['file']
        original_filename = uploaded_file.name
        
        try:
            # Handle file upload with deduplication
            file_reference, is_duplicate, storage_saved = DeduplicationService.handle_file_upload(
                uploaded_file, original_filename
            )
            
            # Prepare response
            response_data = {
                'file_reference': file_reference,
                'is_duplicate': is_duplicate,
                'storage_saved': storage_saved,
                'message': 'File uploaded successfully'
            }
            
            if is_duplicate:
                response_data['message'] = f'Duplicate file detected. Storage saved: {storage_saved} bytes'
            
            # Serialize the response
            response_serializer = FileUploadResponseSerializer(
                response_data, 
                context={'request': request}
            )
            
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'File upload failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a file reference with reference counting
        """
        try:
            file_reference = self.get_object()
            deletion_info = DeduplicationService.handle_file_deletion(file_reference)
            
            return Response({
                'message': 'File reference deleted successfully',
                'file_deleted': deletion_info['file_deleted'],
                'storage_freed': deletion_info['storage_freed'],
                'references_remaining': deletion_info['references_remaining']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'File deletion failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Advanced search and filtering endpoint
        """
        # Validate search parameters
        search_serializer = FileSearchSerializer(data=request.query_params)
        search_serializer.is_valid(raise_exception=True)
        
        # Get filtered results
        queryset = FileSearchService.search_files(request.query_params)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get storage statistics and deduplication savings
        """
        try:
            stats = StorageStats.get_stats()
            serializer = StorageStatsSerializer(stats, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve stats: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def file_types(self, request):
        """
        Get list of available file types for filtering
        """
        try:
            file_types = File.objects.values_list('file_type', flat=True).distinct().order_by('file_type')
            return Response({'file_types': list(file_types)})
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve file types: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def duplicates(self, request):
        """
        Get all duplicate file references
        """
        try:
            duplicates = FileReference.objects.filter(is_duplicate=True).select_related('file')
            
            # Apply pagination
            page = self.paginate_queryset(duplicates)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(duplicates, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve duplicates: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing physical file information (read-only)
    """
    queryset = File.objects.all()
    serializer_class = FileSerializer
    pagination_class = FilePagination

    @action(detail=True, methods=['get'])
    def references(self, request, pk=None):
        """
        Get all references to a specific file
        """
        try:
            file_obj = self.get_object()
            references = file_obj.references.all()
            
            # Apply pagination
            page = self.paginate_queryset(references)
            if page is not None:
                serializer = FileReferenceSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = FileReferenceSerializer(references, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve file references: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Maintain backward compatibility with the original API
# Map 'files' endpoint to FileReference operations
FileViewSet = FileReferenceViewSet
