from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.conf import settings
from .models import Document
import os
import shutil

User = get_user_model()

# Unregister the default User admin and register our custom one
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'document_count', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    def document_count(self, obj):
        """Show number of documents uploaded by this user"""
        count = obj.documents.filter(is_active=True).count()
        if count > 0:
            url = reverse('admin:chatbot_document_changelist') + f'?user__id__exact={obj.id}'
            return format_html('<a href="{}">{} documents</a>', url, count)
        return '0 documents'
    document_count.short_description = 'Documents'

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'filename', 'file_size_human', 'file_type', 'upload_date', 'is_active', 'delete_from_chroma')
    list_filter = ('is_active', 'file_type', 'upload_date', 'user')
    search_fields = ('title', 'filename', 'user__username', 'user__email')
    ordering = ('-upload_date',)
    readonly_fields = ('upload_date', 'last_modified', 'file_size_human')
    list_per_page = 25
    
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'filename', 'is_active')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size', 'file_size_human', 'file_type')
        }),
        ('Chroma Integration', {
            'fields': ('chroma_collection_id',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('upload_date', 'last_modified'),
            'classes': ('collapse',)
        }),
    )
    
    def delete_from_chroma(self, obj):
        """Add a button to delete document from Chroma DB"""
        if obj.chroma_collection_id and obj.is_active:
            url = reverse('admin:delete_document_from_chroma', args=[obj.id])
            return format_html(
                '<a class="button" href="{}" onclick="return confirm(\'Are you sure you want to delete this document from Chroma DB?\')">Delete from Chroma</a>',
                url
            )
        return 'N/A'
    delete_from_chroma.short_description = 'Chroma Actions'
    delete_from_chroma.allow_tags = True
    
    def get_queryset(self, request):
        """Filter documents based on user permissions"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superusers can only see their own documents
        return qs.filter(user=request.user)
    
    def save_model(self, request, obj, form, change):
        """Ensure users can only modify their own documents"""
        if not change:  # Creating new document
            obj.user = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        """Add custom URLs for admin actions"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:document_id>/delete-from-chroma/',
                self.admin_site.admin_view(self.delete_from_chroma_view),
                name='delete_document_from_chroma',
            ),
        ]
        return custom_urls + urls
    
    def delete_from_chroma_view(self, request, document_id):
        """Custom view to delete document from Chroma DB"""
        document = get_object_or_404(Document, id=document_id)
        
        # Check permissions
        if not request.user.is_superuser and document.user != request.user:
            messages.error(request, 'You do not have permission to delete this document.')
            return redirect('admin:chatbot_document_changelist')
        
        try:
            # Delete from Chroma DB if collection ID exists
            if document.chroma_collection_id:
                self._delete_from_chroma_db(document.chroma_collection_id)
                messages.success(request, f'Document "{document.title}" deleted from Chroma DB successfully.')
            else:
                messages.warning(request, f'Document "{document.title}" was not found in Chroma DB.')
            
            # Delete the physical file
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)
                messages.success(request, f'Physical file "{document.filename}" deleted successfully.')
            
            # Mark document as inactive (soft delete)
            document.is_active = False
            document.save()
            
        except Exception as e:
            messages.error(request, f'Error deleting document: {str(e)}')
        
        return redirect('admin:chatbot_document_changelist')
    
    def _delete_from_chroma_db(self, collection_id):
        """Helper method to delete from Chroma DB"""
        try:
            from langchain_community.vectorstores import Chroma
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            # Initialize embeddings
            if settings.RAG_EMBEDDINGS_PROVIDER == 'openai':
                from langchain_openai import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings()
            else:
                embeddings = HuggingFaceEmbeddings(
                    model_name=settings.RAG_HF_MODEL_NAME
                )
            
            # Initialize Chroma
            persist_directory = settings.CHROMA_PERSIST_DIR
            vectorstore = Chroma(
                collection_name=collection_id,
                embedding_function=embeddings,
                persist_directory=persist_directory
            )
            
            # Delete the collection
            vectorstore.delete_collection()
            
        except Exception as e:
            raise Exception(f"Failed to delete from Chroma DB: {str(e)}")
