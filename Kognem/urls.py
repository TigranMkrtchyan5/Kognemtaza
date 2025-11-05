
from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from .views import *


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
    path('admin/users/all/', views.all_users, name='all_users'),
    path('admin/users/active/', views.active_users, name='active_users'),
    path('admin/users/banned/', views.banned_users, name='banned_users'),
    path('ban-user/<int:user_id>/', views.ban_user, name='ban_user'),
    path('unban-user/<int:user_id>/', views.unban_user, name='unban_user'),
    path('check-ban-status/<int:user_id>/', views.check_ban_status, name='check_ban_status'),
    path('admin/posts/approve/<int:post_id>/', views.approve_post, name='approve_post'),
    path('admin/posts/reject/<int:post_id>/', views.reject_post, name='reject_post'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('user/<int:user_id>/', views.user_detail, name='user_detail'),
    path('create-post/', views.create_post, name='create_post'),
    path('admin/post_management/', views.post_management, name='post_management'),
    path('admin/posts/approved/', views.approved_posts_view, name='approved_posts'),
    path('admin/posts/rejected/', views.rejected_posts_view, name='rejected_posts'),
    path('admin/posts/pending/', views.pending_posts_view, name='pending_posts'),
    path('admin/posts/delete/<int:post_id>/', views.delete_post, name='delete_post'),
    path('Account/myinfo/', views.myinfo, name='myinfo'),
    path('Account/myposts/', views.myposts, name='myposts'),
    path('get_provinces/<int:state_id>/', views.get_provinces, name='get_provinces'),
    path('Account/notifications/', views.notifications, name='notifications'),
    path('Account/view_post/<int:post_id>/', views.view_post, name='view_post'),
    path('chat/<int:user_id>/', views.chat_room, name='chat_room'),
    path('messages/', views.messages_list, name='messages_list'),
    path('chat/create/<str:username>/', views.create_room, name='create_room'),
    path('chat/<int:user_id>/', views.chat_room, name='chat_room'),
    path('chat/<int:user_id>/send/', views.send_message, name='send_message'),
    path('chat/<int:user_id>/messages/', views.get_messages_by_id, name='get_messages_by_id'),
    path('chat/<str:username>/messages/', views.get_messages, name='get_messages'),
    path('calculate_distance/', views.calculate_distance, name='calculate_distance'),
    path('task/<int:post_id>/', views.task_detail, name='task_detail'),


    path('task/<int:post_id>/apply/', views.apply_for_task, name='apply_for_task'),
    path('task/<int:post_id>/applications/', views.task_applications, name='task_applications'),
    path('task/<int:post_id>/assign/<int:applicant_id>/', views.assign_task, name='assign_task'),
    path('task/<int:post_id>/complete/', views.complete_task, name='complete_task'),
    path('task/<int:post_id>/incomplete/', views.mark_incomplete, name='mark_incomplete'),
    path('task/<int:post_id>/cancel/', views.cancel_task, name='cancel_task'),
    path('tasks/my-applications/', views.my_applications, name='my_applications'),


    
    path('task/<int:post_id>/worker/incomplete/', views.worker_mark_incomplete, name='worker_mark_incomplete'),
    path('task/<int:post_id>/worker/cancel/', views.worker_cancel_task, name='worker_cancel_task'),
    path('task/<int:post_id>/start/', views.start_task, name='start_task'),
    path('task/<int:post_id>/resubmit/', views.resubmit_task, name='resubmit_task'),




    path('my-tasks/', views.worker_tasks, name='worker_tasks'),
    path('task/<int:post_id>/worker/complete/', views.worker_complete_task, name='worker_complete_task'),
    path('task/<int:post_id>/approve-completion/', views.owner_approve_completion, name='owner_approve_completion'),
    path('task/<int:post_id>/reject-completion/', views.owner_reject_completion, name='owner_reject_completion'),




    # Add these URLs
    path('task/<int:post_id>/dispute/', views.dispute_task, name='dispute_task'),
    path('task/<int:post_id>/owner-dispute/', views.owner_dispute_task, name='owner_dispute_task'),


    path('debug-tracking/', views.debug_tracking, name='debug_tracking'),


    path('task/<int:post_id>/track-view/', views.track_task_view, name='track_task_view'),

    # Добавьте в urlpatterns
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:post_id>/send-moderation/', views.send_for_moderation, name='send_for_moderation'),


    path('password-reset/', password_reset_request, name='password_reset_request'),
    path('password-reset/done/', password_reset_done, name='password_reset_done'),
    path('password-reset-confirm/<int:user_id>/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
    path('password-reset-complete/', password_reset_complete, name='password_reset_complete'),

    path('admin/reviews/', views.admin_review_list, name='admin_review_list'),
    path('admin/user-ratings/', views.user_ratings_report, name='user_ratings_report'),
    path('task/<int:post_id>/complete/', views.owner_complete_task, name='owner_complete_task'),
    
    
    
    # Review URLs
    path('submit-review/', views.submit_review, name='submit_review'),
    path('pending-reviews/', views.get_pending_reviews, name='get_pending_reviews'),
    path('check-review-status/<int:post_id>/', views.check_review_status, name='check_review_status'),



    
    
    path('dispute/<int:dispute_id>/submit-evidence/', views.submit_dispute_evidence, name='submit_dispute_evidence'),
    
    # Update the mark_incomplete URL to use the new view
    path('task/<int:post_id>/incomplete/', views.mark_incomplete, name='mark_incomplete'),
    

    path('task/<int:post_id>/worker-dispute/', views.worker_dispute_incomplete, name='worker_dispute_incomplete'),
    path('task/<int:post_id>/contact-admin/', views.contact_admin, name='contact_admin'),
    path('dispute/<int:dispute_id>/send-message/', views.send_dispute_message, name='send_dispute_message'),
    path('dispute/<int:dispute_id>/get-messages/', views.get_dispute_messages, name='get_dispute_messages'),
    
    # Admin dispute URLs
    path('admin/disputes/', views.admin_disputes, name='admin_disputes'),
    path('admin/disputes/<int:dispute_id>/', views.dispute_detail, name='dispute_detail'),

    path('disputes/<int:dispute_id>/reopen/', views.reopen_dispute, name='reopen_dispute'),

    
]

