from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.http import Http404
from django.db.models import Sum, Count, Q

from .models import File, FileReference, StorageStats
from .serializers import (
    FileSerializer, FileReferenceSerializer, FileUploadSerializer,
    FileUploadResponseSerializer, StorageStatsSerializer, FileSearchSerializer,
    BulkDeleteSerializer, BulkDeleteResponseSerializer, DetailedStatsSerializer,
    FileTypeStatsSerializer
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

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        Bulk delete multiple file references
        """
        try:
            # Validate the request data
            bulk_delete_serializer = BulkDeleteSerializer(data=request.data)
            bulk_delete_serializer.is_valid(raise_exception=True)
            
            reference_ids = bulk_delete_serializer.validated_data['reference_ids']
            references = FileReference.objects.filter(id__in=reference_ids)
            
            deletion_results = []
            total_storage_freed = 0
            
            for reference in references:
                deletion_info = DeduplicationService.handle_file_deletion(reference)
                deletion_results.append({
                    'reference_id': str(reference.id),
                    'original_filename': reference.original_filename,
                    'file_deleted': deletion_info['file_deleted'],
                    'storage_freed': deletion_info['storage_freed']
                })
                total_storage_freed += deletion_info['storage_freed']
            
            response_data = {
                'message': f'Successfully deleted {len(deletion_results)} file references',
                'total_storage_freed': total_storage_freed,
                'results': deletion_results
            }
            
            # Serialize the response
            response_serializer = BulkDeleteResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Bulk deletion failed: {str(e)}'}, 
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
    def detailed_stats(self, request):
        """
        Get detailed storage statistics with breakdown by file type
        """
        try:
            # Basic stats
            stats = StorageStats.get_stats()
            
            # File type breakdown
            file_type_stats = File.objects.values('file_type').annotate(
                count=Count('id'),
                total_size=Sum('size'),
                total_references=Sum('reference_count')
            ).order_by('-total_size')
            
            # Most duplicated files
            most_duplicated = File.objects.filter(reference_count__gt=1).order_by('-reference_count')[:10]
            
            # Recent activity
            recent_uploads = FileReference.objects.order_by('-uploaded_at')[:10]
            recent_duplicates = FileReference.objects.filter(is_duplicate=True).order_by('-uploaded_at')[:5]
            
            response_data = {
                'basic_stats': StorageStatsSerializer(stats, context={'request': request}).data,
                'file_type_breakdown': list(file_type_stats),
                'most_duplicated_files': FileSerializer(most_duplicated, many=True, context={'request': request}).data,
                'recent_uploads': FileReferenceSerializer(recent_uploads, many=True, context={'request': request}).data,
                'recent_duplicates': FileReferenceSerializer(recent_duplicates, many=True, context={'request': request}).data
            }
            
            return Response(response_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve detailed stats: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def file_types(self, request):
        """
        Get list of available file types for filtering
        """
        try:
            file_types = File.objects.values_list('file_type', flat=True).distinct().order_by('file_type')
            return Response(list(file_types))
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

    @action(detail=False, methods=['get'])
    def orphaned_files(self, request):
        """
        Get physical files that have no references (should not happen with proper reference counting)
        """
        try:
            orphaned = File.objects.filter(reference_count=0)
            serializer = FileSerializer(orphaned, many=True, context={'request': request})
            return Response({
                'count': orphaned.count(),
                'orphaned_files': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve orphaned files: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def duplicate_references(self, request, pk=None):
        """
        Get all references that point to the same physical file as this reference
        """
        try:
            file_reference = self.get_object()
            duplicate_references = FileReference.objects.filter(
                file=file_reference.file
            ).exclude(id=file_reference.id)
            
            serializer = self.get_serializer(duplicate_references, many=True)
            return Response({
                'total_references': file_reference.file.reference_count,
                'other_references': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve duplicate references: {str(e)}'}, 
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
        Get all references to a specific physical file
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

    @action(detail=False, methods=['get'])
    def most_referenced(self, request):
        """
        Get files with the most references (most duplicated)
        """
        try:
            most_referenced = File.objects.filter(reference_count__gt=1).order_by('-reference_count')
            
            # Apply pagination
            page = self.paginate_queryset(most_referenced)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(most_referenced, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve most referenced files: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
