from rest_framework import serializers
from .models import File, FileReference, StorageStats

class FileSerializer(serializers.ModelSerializer):
    """Serializer for the File model (physical files)"""
    
    class Meta:
        model = File
        fields = [
            'id', 'file', 'file_hash', 'file_type', 'size', 
            'reference_count', 'created_at'
        ]
        read_only_fields = ['id', 'file_hash', 'reference_count', 'created_at']

class FileReferenceSerializer(serializers.ModelSerializer):
    """Serializer for FileReference model (user file uploads/references)"""
    
    # Include file details
    file_url = serializers.SerializerMethodField()
    file_hash = serializers.CharField(source='file.file_hash', read_only=True)
    file_type = serializers.CharField(source='file.file_type', read_only=True)
    size = serializers.IntegerField(source='file.size', read_only=True)
    reference_count = serializers.IntegerField(source='file.reference_count', read_only=True)
    
    class Meta:
        model = FileReference
        fields = [
            'id', 'original_filename', 'uploaded_at', 'is_duplicate',
            'file_url', 'file_hash', 'file_type', 'size', 'reference_count'
        ]
        read_only_fields = [
            'id', 'uploaded_at', 'is_duplicate', 'file_url', 
            'file_hash', 'file_type', 'size', 'reference_count'
        ]
    
    def get_file_url(self, obj):
        """Get the file URL"""
        request = self.context.get('request')
        if obj.file.file and request:
            return request.build_absolute_uri(obj.file.file.url)
        return None

class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests"""
    
    file = serializers.FileField()
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (max 10MB as mentioned in README)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size {value.size} bytes exceeds maximum allowed size of {max_size} bytes"
            )
        
        return value

class FileUploadResponseSerializer(serializers.Serializer):
    """Serializer for file upload response"""
    
    file_reference = FileReferenceSerializer(read_only=True)
    is_duplicate = serializers.BooleanField(read_only=True)
    storage_saved = serializers.IntegerField(read_only=True)
    message = serializers.CharField(read_only=True)

class StorageStatsSerializer(serializers.ModelSerializer):
    """Serializer for storage statistics"""
    
    savings_percentage = serializers.SerializerMethodField()
    deduplication_ratio = serializers.SerializerMethodField()
    
    # Formatted size fields for better readability
    total_size_uploaded_mb = serializers.SerializerMethodField()
    actual_size_stored_mb = serializers.SerializerMethodField()
    storage_saved_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = StorageStats
        fields = [
            'total_files_uploaded', 'unique_files_stored',
            'total_size_uploaded', 'actual_size_stored', 'storage_saved',
            'total_size_uploaded_mb', 'actual_size_stored_mb', 'storage_saved_mb',
            'savings_percentage', 'deduplication_ratio', 'last_updated'
        ]
        read_only_fields = [
            'total_files_uploaded', 'unique_files_stored',
            'total_size_uploaded', 'actual_size_stored', 'storage_saved',
            'total_size_uploaded_mb', 'actual_size_stored_mb', 'storage_saved_mb',
            'savings_percentage', 'deduplication_ratio', 'last_updated'
        ]
    
    def get_savings_percentage(self, obj):
        """Calculate storage savings percentage"""
        return round(obj.calculate_savings_percentage(), 2)
    
    def get_deduplication_ratio(self, obj):
        """Calculate deduplication ratio"""
        if obj.unique_files_stored > 0:
            return round(obj.total_files_uploaded / obj.unique_files_stored, 2)
        return 0
    
    def get_total_size_uploaded_mb(self, obj):
        """Convert bytes to MB"""
        return round(obj.total_size_uploaded / (1024 * 1024), 2)
    
    def get_actual_size_stored_mb(self, obj):
        """Convert bytes to MB"""
        return round(obj.actual_size_stored / (1024 * 1024), 2)
    
    def get_storage_saved_mb(self, obj):
        """Convert bytes to MB"""
        return round(obj.storage_saved / (1024 * 1024), 2)

class FileSearchSerializer(serializers.Serializer):
    """Serializer for file search parameters"""
    
    search = serializers.CharField(required=False, allow_blank=True, max_length=255)
    file_type = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True
    )
    min_size = serializers.IntegerField(required=False, min_value=0)
    max_size = serializers.IntegerField(required=False, min_value=0)
    from_date = serializers.DateTimeField(required=False)
    to_date = serializers.DateTimeField(required=False)
    duplicates_only = serializers.BooleanField(required=False, default=False)
    sort_by = serializers.ChoiceField(
        choices=[
            ('uploaded_at', 'Upload Date (Oldest)'),
            ('-uploaded_at', 'Upload Date (Newest)'),
            ('original_filename', 'Filename (A-Z)'),
            ('-original_filename', 'Filename (Z-A)'),
            ('file__size', 'Size (Smallest)'),
            ('-file__size', 'Size (Largest)'),
            ('file__file_type', 'Type (A-Z)'),
            ('-file__file_type', 'Type (Z-A)'),
        ],
        required=False,
        default='-uploaded_at'
    )
    
    def validate(self, data):
        """Validate search parameters"""
        min_size = data.get('min_size')
        max_size = data.get('max_size')
        
        if min_size is not None and max_size is not None and min_size > max_size:
            raise serializers.ValidationError("min_size cannot be greater than max_size")
        
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError("from_date cannot be later than to_date")
        
        return data 