from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileViewSet, FileReferenceViewSet

# Create separate routers for different viewsets
router = DefaultRouter()
router.register(r'files', FileReferenceViewSet, basename='filereference')
router.register(r'physical-files', FileViewSet, basename='file')

urlpatterns = [
    path('', include(router.urls)),
] 