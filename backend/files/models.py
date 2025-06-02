from django.db import models
import uuid
import os
import hashlib

def file_upload_path(instance, filename):
    """Generate file path for new file upload"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

def calculate_file_hash(file_obj):
    """Calculate SHA-256 hash of file content"""
    hash_sha256 = hashlib.sha256()
    for chunk in file_obj.chunks():
        hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# Custom manager for optimized queries (SQLite compatible)
class FileReferenceManager(models.Manager):
    """Custom manager with optimized query methods for SQLite"""
    
    def search_by_filename(self, query):
        """SQLite-compatible filename search using LIKE and normalization"""
        if not query.strip():
            return self.none()
        
        # Normalize search query
        normalized_query = query.lower().strip()
        
        # Use multiple search strategies for better results
        return self.filter(
            models.Q(filename_normalized__icontains=normalized_query) |
            models.Q(original_filename__icontains=query)
        ).distinct().order_by('-uploaded_at')
    
    def filter_by_file_type(self, file_types):
        """Optimized file type filtering"""
        if not file_types:
            return self.all()
        return self.select_related('file').filter(file__file_type__in=file_types)
    
    def filter_by_size_range(self, min_size=None, max_size=None):
        """Optimized size range filtering"""
        queryset = self.select_related('file')
        if min_size is not None:
            queryset = queryset.filter(file__size__gte=min_size)
        if max_size is not None:
            queryset = queryset.filter(file__size__lte=max_size)
        return queryset
    
    def filter_by_date_range(self, from_date=None, to_date=None):
        """Optimized date range filtering"""
        queryset = self.all()
        if from_date:
            queryset = queryset.filter(uploaded_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(uploaded_at__lte=to_date)
        return queryset
    
    def duplicates_only(self):
        """Get only duplicate file references"""
        return self.filter(is_duplicate=True).select_related('file')
    
    def most_recent(self, limit=10):
        """Get most recent uploads with optimized query"""
        return self.select_related('file').order_by('-uploaded_at')[:limit]
    
    def advanced_search(self, query_params):
        """
        Advanced search combining multiple filters with optimized queries
        """
        queryset = self.select_related('file').all()
        
        # Search by filename
        search = query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                models.Q(filename_normalized__icontains=search.lower()) |
                models.Q(original_filename__icontains=search)
            )
        
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

class FileManager(models.Manager):
    """Custom manager for File model with optimized queries"""
    
    def most_referenced(self, limit=10):
        """Get files with most references"""
        return self.filter(reference_count__gt=1).order_by('-reference_count', '-created_at')[:limit]
    
    def by_file_type(self):
        """Get files grouped by file type with statistics"""
        from django.db.models import Count, Sum
        return self.values('file_type').annotate(
            count=Count('id'),
            total_size=Sum('size'),
            total_references=Sum('reference_count')
        ).order_by('-total_size')
    
    def orphaned(self):
        """Get files with no references (should not happen with proper reference counting)"""
        return self.filter(reference_count=0)
    
    def storage_efficient_query(self):
        """Optimized query for storage statistics"""
        from django.db.models import Sum, Count
        return self.aggregate(
            total_files=Count('id'),
            total_size=Sum('size'),
            total_references=Sum('reference_count')
        )

class File(models.Model):
    """
    Represents the actual physical file stored on disk.
    Multiple FileReference objects can point to the same File for deduplication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=file_upload_path)
    file_hash = models.CharField(max_length=64, unique=True, db_index=True)  # SHA-256 hash
    file_type = models.CharField(max_length=100, db_index=True)
    size = models.BigIntegerField(db_index=True)  # Add index for size-based queries
    reference_count = models.PositiveIntegerField(default=0, db_index=True)  # Index for duplicate queries
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    objects = FileManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Single field indexes for basic queries
            models.Index(fields=['file_hash'], name='files_file_hash_idx'),
            models.Index(fields=['file_type'], name='files_file_type_idx'),
            models.Index(fields=['size'], name='files_size_idx'),
            models.Index(fields=['created_at'], name='files_created_at_idx'),
            models.Index(fields=['reference_count'], name='files_ref_count_idx'),
            
            # Compound indexes for complex queries (SQLite compatible)
            models.Index(fields=['file_type', 'size'], name='files_type_size_idx'),
            models.Index(fields=['file_type', '-created_at'], name='files_type_date_idx'),
            models.Index(fields=['size', '-created_at'], name='files_size_date_idx'),
            models.Index(fields=['reference_count', '-created_at'], name='files_refs_date_idx'),
            
            # Performance indexes for common query patterns
            models.Index(fields=['-reference_count', '-created_at'], name='files_most_refs_idx'),
            models.Index(fields=['file_type', '-reference_count'], name='files_type_refs_idx'),
        ]
    
    def __str__(self):
        return f"File {self.file_hash[:8]} ({self.reference_count} refs)"

    def increment_reference(self):
        """Increment reference count when a new FileReference is created"""
        self.reference_count += 1
        self.save(update_fields=['reference_count'])

    def decrement_reference(self):
        """Decrement reference count when a FileReference is deleted"""
        self.reference_count = max(0, self.reference_count - 1)
        self.save(update_fields=['reference_count'])

class FileReference(models.Model):
    """
    Represents a user's reference/upload to a file.
    Multiple references can point to the same physical File for deduplication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='references')
    original_filename = models.CharField(max_length=255, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_duplicate = models.BooleanField(default=False, db_index=True)
    
    # Normalized filename for better search performance in SQLite
    filename_normalized = models.CharField(max_length=255, db_index=True, blank=True)
    
    objects = FileReferenceManager()
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            # Basic indexes
            models.Index(fields=['original_filename'], name='filerefs_filename_idx'),
            models.Index(fields=['uploaded_at'], name='filerefs_uploaded_idx'),
            models.Index(fields=['is_duplicate'], name='filerefs_duplicate_idx'),
            models.Index(fields=['filename_normalized'], name='filerefs_norm_name_idx'),
            
            # Compound indexes for filtering combinations
            models.Index(fields=['is_duplicate', '-uploaded_at'], name='filerefs_dup_date_idx'),
            models.Index(fields=['original_filename', '-uploaded_at'], name='filerefs_name_date_idx'),
            models.Index(fields=['filename_normalized', '-uploaded_at'], name='filerefs_norm_date_idx'),
            
            # Foreign key optimization
            models.Index(fields=['file', '-uploaded_at'], name='filerefs_file_date_idx'),
            models.Index(fields=['file', 'is_duplicate'], name='filerefs_file_dup_idx'),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to update normalized filename"""
        # Normalize filename for better search performance
        self.filename_normalized = self.original_filename.lower().strip()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.original_filename

class StorageStats(models.Model):
    """
    Tracks storage savings from deduplication
    """
    total_files_uploaded = models.PositiveIntegerField(default=0)
    unique_files_stored = models.PositiveIntegerField(default=0)
    total_size_uploaded = models.BigIntegerField(default=0)  # Total size of all uploads
    actual_size_stored = models.BigIntegerField(default=0)   # Actual storage used
    storage_saved = models.BigIntegerField(default=0)        # Bytes saved through deduplication
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Storage Statistics"
        verbose_name_plural = "Storage Statistics"
    
    def __str__(self):
        savings_mb = self.storage_saved / (1024 * 1024)
        return f"Storage saved: {savings_mb:.2f} MB"
    
    def calculate_savings_percentage(self):
        """Calculate percentage of storage saved"""
        if self.total_size_uploaded > 0:
            return (self.storage_saved / self.total_size_uploaded) * 100
        return 0
    
    @classmethod
    def get_stats(cls):
        """Get or create the singleton stats object"""
        stats, created = cls.objects.get_or_create(pk=1)
        return stats
