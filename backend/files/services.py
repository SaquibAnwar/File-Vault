import os
import hashlib
from django.core.files.base import ContentFile
from django.db import transaction
from .models import File, FileReference, StorageStats
from django.db.models import Count, Sum, Avg, Max, Q

class DeduplicationService:
    """
    Service class for handling file deduplication logic
    """
    
    @staticmethod
    def calculate_file_hash(file_obj):
        """
        Calculate SHA-256 hash of file content
        
        Args:
            file_obj: Django UploadedFile object
            
        Returns:
            str: SHA-256 hash as hexadecimal string
        """
        # Reset file pointer to beginning
        file_obj.seek(0)
        
        hash_sha256 = hashlib.sha256()
        
        # Read file in chunks to handle large files efficiently
        for chunk in file_obj.chunks(chunk_size=8192):
            hash_sha256.update(chunk)
        
        # Reset file pointer back to beginning for potential future use
        file_obj.seek(0)
        
        return hash_sha256.hexdigest()
    
    @staticmethod
    def find_existing_file(file_hash):
        """
        Check if a file with the given hash already exists
        
        Args:
            file_hash (str): SHA-256 hash of the file
            
        Returns:
            File: Existing File object if found, None otherwise
        """
        try:
            return File.objects.get(file_hash=file_hash)
        except File.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def handle_file_upload(uploaded_file, original_filename):
        """
        Handle file upload with deduplication logic
        
        Args:
            uploaded_file: Django UploadedFile object
            original_filename (str): Original filename from user
            
        Returns:
            tuple: (FileReference object, is_duplicate boolean, storage_saved)
        """
        # Calculate file hash
        file_hash = DeduplicationService.calculate_file_hash(uploaded_file)
        
        # Check if file already exists
        existing_file = DeduplicationService.find_existing_file(file_hash)
        
        is_duplicate = existing_file is not None
        storage_saved = 0
        
        if existing_file:
            # File is a duplicate - create reference to existing file
            file_obj = existing_file
            file_obj.increment_reference()
            storage_saved = uploaded_file.size  # We saved this much storage
        else:
            # New unique file - store it
            file_obj = File.objects.create(
                file=uploaded_file,
                file_hash=file_hash,
                file_type=uploaded_file.content_type or 'application/octet-stream',
                size=uploaded_file.size,
                reference_count=1  # First reference
            )
        
        # Create file reference
        file_reference = FileReference.objects.create(
            file=file_obj,
            original_filename=original_filename,
            is_duplicate=is_duplicate
        )
        
        # Update storage statistics
        DeduplicationService.update_storage_stats(
            uploaded_file.size, 
            0 if is_duplicate else uploaded_file.size, 
            storage_saved
        )
        
        return file_reference, is_duplicate, storage_saved
    
    @staticmethod
    @transaction.atomic
    def handle_file_deletion(file_reference):
        """
        Handle file deletion with reference counting
        
        Args:
            file_reference: FileReference object to delete
            
        Returns:
            dict: Information about the deletion (file_deleted, storage_freed)
        """
        file_obj = file_reference.file
        file_size = file_obj.size
        was_last_reference = file_obj.reference_count <= 1
        
        # Delete the file reference
        file_reference.delete()
        
        # Decrement reference count
        file_obj.decrement_reference()
        
        # If no more references, delete the physical file
        if file_obj.reference_count == 0:
            # Delete the physical file
            if file_obj.file:
                try:
                    if os.path.exists(file_obj.file.path):
                        os.remove(file_obj.file.path)
                except (ValueError, OSError):
                    pass  # File might not exist or be accessible
            
            # Delete the File record
            file_obj.delete()
            storage_freed = file_size
        else:
            storage_freed = 0
        
        # Update storage statistics
        stats = StorageStats.get_stats()
        stats.total_files_uploaded = max(0, stats.total_files_uploaded - 1)
        stats.total_size_uploaded = max(0, stats.total_size_uploaded - file_size)
        
        if was_last_reference:
            stats.unique_files_stored = max(0, stats.unique_files_stored - 1)
            stats.actual_size_stored = max(0, stats.actual_size_stored - file_size)
        else:
            # If not the last reference, we're freeing up "saved" storage
            stats.storage_saved = max(0, stats.storage_saved - file_size)
        
        stats.save()
        
        return {
            'file_deleted': was_last_reference,
            'storage_freed': storage_freed,
            'references_remaining': file_obj.reference_count if not was_last_reference else 0
        }
    
    @staticmethod
    def update_storage_stats(uploaded_size, stored_size, saved_size):
        """
        Update storage statistics
        
        Args:
            uploaded_size (int): Size of the uploaded file
            stored_size (int): Actual size stored (0 if duplicate)
            saved_size (int): Size saved through deduplication
        """
        stats = StorageStats.get_stats()
        
        stats.total_files_uploaded += 1
        stats.total_size_uploaded += uploaded_size
        stats.storage_saved += saved_size
        
        if stored_size > 0:  # New unique file
            stats.unique_files_stored += 1
            stats.actual_size_stored += stored_size
        
        stats.save()
    
    @staticmethod
    def get_storage_savings_info():
        """
        Get current storage savings information
        
        Returns:
            dict: Storage statistics and savings information
        """
        stats = StorageStats.get_stats()
        
        savings_percentage = stats.calculate_savings_percentage()
        
        return {
            'total_files_uploaded': stats.total_files_uploaded,
            'unique_files_stored': stats.unique_files_stored,
            'total_size_uploaded': stats.total_size_uploaded,
            'actual_size_stored': stats.actual_size_stored,
            'storage_saved': stats.storage_saved,
            'savings_percentage': round(savings_percentage, 2),
            'deduplication_ratio': round(stats.total_files_uploaded / max(stats.unique_files_stored, 1), 2),
            'last_updated': stats.last_updated
        }

class FileSearchService:
    """
    Service class for file search and filtering functionality with optimized performance
    """
    
    @staticmethod
    def search_files(query_params):
        """
        Optimized search and filter files based on query parameters using custom manager
        
        Args:
            query_params (dict): Search and filter parameters
            
        Returns:
            QuerySet: Filtered FileReference queryset with optimized queries
        """
        # Use the optimized advanced_search method from our custom manager
        return FileReference.objects.advanced_search(query_params)
    
    @staticmethod
    def search_by_filename_only(query):
        """
        Optimized filename-only search
        
        Args:
            query (str): Search query for filename
            
        Returns:
            QuerySet: Filtered results optimized for filename search
        """
        return FileReference.objects.search_by_filename(query)
    
    @staticmethod
    def get_file_type_statistics():
        """
        Get comprehensive file type statistics with optimized queries
        
        Returns:
            dict: File type statistics and performance metrics
        """
        # Use optimized manager method
        type_stats = File.objects.by_file_type()
        
        # Additional statistics
        total_stats = File.objects.storage_efficient_query()
        
        # Most duplicated file types
        duplicated_types = File.objects.filter(reference_count__gt=1).values('file_type').annotate(
            avg_duplicates=Avg('reference_count'),
            max_duplicates=Max('reference_count'),
            duplicated_files=Count('id')
        ).order_by('-avg_duplicates')
        
        return {
            'type_breakdown': list(type_stats),
            'total_statistics': total_stats,
            'most_duplicated_types': list(duplicated_types),
        }
    
    @staticmethod
    def get_search_suggestions(partial_query, limit=10):
        """
        Get search suggestions based on partial filename query
        
        Args:
            partial_query (str): Partial search query
            limit (int): Maximum number of suggestions
            
        Returns:
            list: List of suggested filenames
        """
        if not partial_query or len(partial_query) < 2:
            return []
        
        # Use normalized search for better performance
        suggestions = FileReference.objects.filter(
            filename_normalized__startswith=partial_query.lower()
        ).values_list('original_filename', flat=True).distinct()[:limit]
        
        return list(suggestions)
    
    @staticmethod
    def get_popular_file_types(limit=10):
        """
        Get most popular file types by upload count
        
        Args:
            limit (int): Maximum number of file types to return
            
        Returns:
            list: Popular file types with statistics
        """
        return File.objects.by_file_type()[:limit]
    
    @staticmethod
    def search_performance_analytics():
        """
        Get analytics about search performance and usage patterns
        
        Returns:
            dict: Performance analytics and insights
        """
        # File type distribution
        type_distribution = File.objects.values('file_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Size distribution (categorized)
        size_categories = [
            ('Small (< 1MB)', 0, 1024*1024),
            ('Medium (1-10MB)', 1024*1024, 10*1024*1024),
            ('Large (> 10MB)', 10*1024*1024, float('inf'))
        ]
        
        size_stats = []
        for label, min_size, max_size in size_categories:
            if max_size == float('inf'):
                count = File.objects.filter(size__gte=min_size).count()
            else:
                count = File.objects.filter(size__gte=min_size, size__lt=max_size).count()
            size_stats.append({'category': label, 'count': count})
        
        # Duplicate patterns
        duplicate_stats = {
            'total_references': FileReference.objects.count(),
            'unique_files': File.objects.count(),
            'duplicate_references': FileReference.objects.filter(is_duplicate=True).count(),
            'files_with_duplicates': File.objects.filter(reference_count__gt=1).count(),
        }
        
        # Recent activity
        from datetime import datetime, timedelta
        recent_date = datetime.now() - timedelta(days=7)
        recent_activity = {
            'uploads_last_7_days': FileReference.objects.filter(uploaded_at__gte=recent_date).count(),
            'duplicates_last_7_days': FileReference.objects.filter(
                uploaded_at__gte=recent_date, 
                is_duplicate=True
            ).count(),
        }
        
        return {
            'file_type_distribution': list(type_distribution),
            'size_distribution': size_stats,
            'duplicate_analytics': duplicate_stats,
            'recent_activity': recent_activity,
        } 