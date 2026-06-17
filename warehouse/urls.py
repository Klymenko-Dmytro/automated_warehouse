from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/data/', views.api_warehouse_data, name='api_data'),
    path('api/manual-add/', views.api_manual_add, name='api_manual_add'),
    path('api/manual-remove/', views.api_manual_remove, name='api_manual_remove'),
]
