from django.urls import path
from . import views

urlpatterns = [
    # Auth endpoints
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.current_user_view, name='current-user'),
    path('change-password/', views.change_password_view, name='change-password'),
    
    # User management
    path('', views.UserListCreateView.as_view(), name='user-list-create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # Partner management (Super Admin only)
    path('partners/', views.PartnerListCreateView.as_view(), name='partner-list-create'),
    path('partners/<int:pk>/', views.PartnerDetailView.as_view(), name='partner-detail'),
    
    # Partner impersonation endpoints (Super Admin)
    path('impersonate/<int:partner_id>/', views.impersonate_partner, name='impersonate-partner'),
    path('exit-impersonation/', views.exit_impersonation, name='exit-impersonation'),
    path('impersonation-status/', views.get_impersonation_status, name='impersonation-status'),
    
    # Store impersonation endpoints (Partner Admin / Super Admin)
    path('impersonate/<int:partner_id>/store/<int:store_id>/', views.impersonate_store, name='impersonate-store'),
    path('exit-store-impersonation/', views.exit_store_impersonation, name='exit-store-impersonation'),
]
