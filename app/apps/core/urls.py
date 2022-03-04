from core.views import (CreateDocument, CreateProject,  # DocumentDetail,
                        DeleteDocumentUserShare, DeleteProjectUserShare,
                        DocumentImages, DocumentModels,
                        DocumentPartsProcessAjax, DocumentsList,
                        DocumentsTasksList, EditPart, Home, MigrateDocument,
                        ModelCancelTraining, ModelDelete, ModelRightDelete,
                        ModelRights, ModelUpload, ProjectList, PublishDocument,
                        ShareDocument, ShareProject, UpdateDocument,
                        UserModels)
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('', Home.as_view(), name='home'),

    path('projects/create/', CreateProject.as_view(), name='project-create'),
    path('projects/', ProjectList.as_view(), name='projects-list'),
    # path('project/<str:slug>/', ProjectDetail.as_view(), name='project-detail'),
    path('project/<str:slug>/documents/', DocumentsList.as_view(), name='documents-list'),
    path('project/<str:slug>/document/create/', CreateDocument.as_view(), name='document-create'),
    path('project/<int:pk>/share/', ShareProject.as_view(), name='project-share'),
    path('project/delete_share/', DeleteProjectUserShare.as_view(), name='delete-project-share'),

    path('documents/tasks/', DocumentsTasksList.as_view(), name='documents-tasks-list'),
    # path('document/<int:pk>/', DocumentDetail.as_view(), name='document-detail'),
    path('document/<int:pk>/edit/', UpdateDocument.as_view(), name='document-update'),
    path('document/<int:pk>/parts/edit/', EditPart.as_view(), name='document-part-edit'),
    path('document/<int:pk>/part/<int:part_pk>/edit/', EditPart.as_view(),
         name='document-part-edit'),
    path('document/<int:pk>/images/', DocumentImages.as_view(), name='document-images'),
    path('models/', UserModels.as_view(), name='user-models'),
    path('models/new/', ModelUpload.as_view(), name='model-upload'),
    path('model/<int:pk>/delete/', ModelDelete.as_view(), name='model-delete'),
    path('model/<int:pk>/cancel_training/', ModelCancelTraining.as_view(),
         name='model-cancel-training'),
    path('model/<int:pk>/rights/', ModelRights.as_view(), name='model-rights'),
    path('model/<int:modelPk>/right/<int:pk>/delete/', ModelRightDelete.as_view(), name='model-right-delete'),
    path('document/<int:document_pk>/models/', DocumentModels.as_view(), name='document-models'),
    path('document/<int:pk>/publish/', PublishDocument.as_view(), name='document-publish'),
    path('document/<int:pk>/share/', ShareDocument.as_view(), name='document-share'),
    path('document/<int:pk>/migrate/', MigrateDocument.as_view(), name='document-migrate'),
    path('document/delete_share/', DeleteDocumentUserShare.as_view(), name='delete-document-share'),
    path('document/<int:pk>/process/', DocumentPartsProcessAjax.as_view(),
         name='document-parts-process'),

    path('test/', TemplateView.as_view(template_name='core/test.html')),
]
