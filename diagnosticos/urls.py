# diagnosticos/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_view, name='chatbot'),
    path('api/procesar_texto/', views.procesar_texto_api, name='procesar_texto'),
    path('protocolos/', views.protocolos_view, name='protocolos'),
    path('estadisticas/', views.estadisticas_view, name='estadisticas'),
    path('dashboard-predictivo/', views.dashboard_predictivo_view, name='dashboard_predictivo'),
    path('caso/<int:caso_id>/', views.caso_detail_view, name='caso_detail'),
]