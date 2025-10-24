from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('', views.start, name='start'),                     # Landing/start page
    path('home/', views.home, name='home'),            # Home page (login/register forms)
    path('register/', views.register_view, name='register'),# Registration page
    path('login/', views.login_view, name='login'),         # Login page (custom view)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('ashxatanq/', views.ashxatanq, name='ashxatanq'),
    path('Account/', views.Account, name='Account'),
    path('logout/', views.logout_view, name='logout'),
    path("check-username/", views.check_username, name="check_username"),
    path("check-email/", views.check_email, name="check_email"),
    path("check-phone/", views.check_phone, name="check_phone"),
    path("check-id/", views.check_id, name="check_id"),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('ban-user/<int:user_id>/', views.ban_user, name='ban_user'),
    path('unban-user/<int:user_id>/', views.unban_user, name='unban_user'),
    path('admin/posts/approve/<int:post_id>/', views.approve_post, name='approve_post'),
    path('admin/posts/reject/<int:post_id>/', views.reject_post, name='reject_post'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('admin-dashboard/login/', views.admin_dashboard_login, name='admin_dashboard_login'),
    path('admin/banned-users/', views.banned_users, name='banned_users')
    


]
   