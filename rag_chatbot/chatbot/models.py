from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Document(models.Model):
    """Model to track user-uploaded documents and their metadata"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)  # Path to the uploaded file
    file_size = models.BigIntegerField()  # File size in bytes
    file_type = models.CharField(max_length=100)  # MIME type or file extension
    chroma_collection_id = models.CharField(max_length=255, blank=True, null=True)  # Chroma collection identifier
    upload_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)  # Soft delete flag
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
    
    def __str__(self):
        return f"{self.title} ({self.user.username})"
    
    @property
    def file_size_human(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
