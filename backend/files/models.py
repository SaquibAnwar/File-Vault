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

class File(models.Model):
    """
    Represents the actual physical file stored on disk.
    Multiple FileReference objects can point to the same File for deduplication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=file_upload_path)
    file_hash = models.CharField(max_length=64, unique=True, db_index=True)  # SHA-256 hash
    file_type = models.CharField(max_length=100, db_index=True)
    size = models.BigIntegerField()
    reference_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['file_hash']),
            models.Index(fields=['file_type']),
            models.Index(fields=['size']),
            models.Index(fields=['created_at']),
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
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_duplicate = models.BooleanField(default=False)  # True if this was a duplicate upload
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['original_filename']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['is_duplicate']),
        ]
    
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
