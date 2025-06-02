import hashlib
import os
from django.core.files.base import ContentFile
from django.db import transaction
from .models import File, FileReference, StorageStats

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
    Service class for file search and filtering functionality
    """
    
    @staticmethod
    def search_files(query_params):
        """
        Search and filter files based on query parameters
        
        Args:
            query_params (dict): Search and filter parameters
            
        Returns:
            QuerySet: Filtered FileReference queryset
        """
        queryset = FileReference.objects.select_related('file').all()
        
        # Search by filename
        search = query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(original_filename__icontains=search)
        
        # Filter by file type
        file_types = query_params.getlist('file_type')
        if file_types:
            queryset = queryset.filter(file__file_type__in=file_types)
        
        # Filter by size range
        min_size = query_params.get('min_size')
        max_size = query_params.get('max_size')
        if min_size:
            try:
                queryset = queryset.filter(file__size__gte=int(min_size))
            except ValueError:
                pass
        if max_size:
            try:
                queryset = queryset.filter(file__size__lte=int(max_size))
            except ValueError:
                pass
        
        # Filter by date range
        from_date = query_params.get('from_date')
        to_date = query_params.get('to_date')
        if from_date:
            try:
                from datetime import datetime
                from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
                queryset = queryset.filter(uploaded_at__gte=from_date)
            except ValueError:
                pass
        if to_date:
            try:
                from datetime import datetime
                to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
                queryset = queryset.filter(uploaded_at__lte=to_date)
            except ValueError:
                pass
        
        # Filter duplicates only
        duplicates_only = query_params.get('duplicates_only', '').lower() == 'true'
        if duplicates_only:
            queryset = queryset.filter(is_duplicate=True)
        
        # Sort options
        sort_by = query_params.get('sort_by', '-uploaded_at')
        valid_sort_fields = [
            'uploaded_at', '-uploaded_at',
            'original_filename', '-original_filename', 
            'file__size', '-file__size',
            'file__file_type', '-file__file_type'
        ]
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        
        return queryset 