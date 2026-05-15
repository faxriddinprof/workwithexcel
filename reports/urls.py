from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('templates/upload/', views.template_upload, name='template_upload'),
    path('assignments/create/', views.assignment_create, name='assignment_create'),
    path('assignments/<int:assignment_id>/', views.submission_editor, name='submission_editor'),
    path('assignments/<int:assignment_id>/save/', views.submission_save, name='submission_save'),
    path('assignments/<int:assignment_id>/export/', views.submission_export, name='submission_export'),
]