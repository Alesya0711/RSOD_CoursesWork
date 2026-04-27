"""
URL configuration for education_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('teachers/', views.teachers_list, name='teachers_list'),
    path('teacher/<int:teacher_id>/', views.teacher_detail, name='teacher_detail'),

    # Аутентификация
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),

    # Запись и отзывы
    path('course/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('course/<int:course_id>/feedback/', views.add_feedback, name='add_feedback'),

    path('reports/courses/', views.export_courses_report, name='export_courses_report'),
    path('reports/students/', views.export_students_report, name='export_students_report'),
    path('reports/enrollment/', views.export_enrollment_report, name='export_enrollment_report'),
    path('admin-panel/reports/export/teachers/', views.export_teachers_report, name='export_teachers_report'),

    path('reports/', views.reports_page, name='reports_page'),

    path('about/', views.about, name='about'),

    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # Админ-панель
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/courses/', views.admin_courses, name='admin_courses'),
    path('admin-panel/courses/add/', views.admin_add_course, name='admin_add_course'),
    path('admin-panel/courses/edit/<int:course_id>/', views.admin_edit_course, name='admin_edit_course'),
    path('admin-panel/teachers/', views.admin_teachers, name='admin_teachers'),
    path('admin-panel/teachers/add/', views.admin_add_teacher, name='admin_add_teacher'),
    path('admin-panel/records/', views.admin_records, name='admin_records'),
    path('admin-panel/records/<int:record_id>/status/', views.admin_update_record_status, name='admin_update_record_status'),
    path('admin-panel/schools/', views.admin_schools, name='admin_schools'),
    path('admin-panel/schools/add/', views.admin_add_school, name='admin_add_school'),
    path('admin-panel/students/', views.admin_students, name='admin_students'),
    path('admin-panel/teachers/edit/<int:teacher_id>/', views.admin_edit_teacher, name='admin_edit_teacher'),
    path('admin-panel/schools/edit/<int:school_id>/', views.admin_edit_school, name='admin_edit_school'),
    path('admin-panel/schools/delete/<int:school_id>/', views.admin_delete_school, name='admin_delete_school'),
    # Абитуриенты
    path('admin-panel/students/', views.admin_students, name='admin_students'),
    path('admin-panel/students/add/', views.admin_add_student, name='admin_add_student'),
    path('admin-panel/students/edit/<int:abitur_id>/', views.admin_edit_student, name='admin_edit_student'),
    path('admin-panel/edit-about/', views.admin_edit_about, name='admin_edit_about'),

    # Отзывы (админка)
    path('admin-panel/feedbacks/', views.admin_feedbacks, name='admin_feedbacks'),
    path('admin-panel/feedbacks/edit/<int:feedback_id>/', views.admin_edit_feedback, name='admin_edit_feedback'),
    path('admin-panel/feedbacks/delete/<int:feedback_id>/', views.admin_delete_feedback, name='admin_delete_feedback'),
    path('admin-panel/feedbacks/approve/<int:feedback_id>/', views.admin_approve_feedback, name='admin_approve_feedback'),
    path('admin-panel/feedbacks/reject/<int:feedback_id>/', views.admin_reject_feedback, name='admin_reject_feedback'),

    path('admin-panel/archive/', views.admin_archive, name='admin_archive'),
    path('admin-panel/archive/courses/', views.admin_archive_courses, name='admin_archive_courses'),
    path('admin-panel/archive/teachers/', views.admin_archive_teachers, name='admin_archive_teachers'),
    path('admin-panel/archive/students/', views.admin_archive_students, name='admin_archive_students'),

    path('admin-panel/archive/course/<int:course_id>/toggle/', views.admin_toggle_course_archive,
         name='admin_toggle_course_archive'),
    path('admin-panel/archive/teacher/<int:teacher_id>/toggle/', views.admin_toggle_teacher_archive,
         name='admin_toggle_teacher_archive'),
    path('admin-panel/archive/student/<int:abitur_id>/toggle/', views.admin_toggle_student_archive,
         name='admin_toggle_student_archive'),

    path('admin-panel/archive/course/<int:course_id>/restore/', views.admin_restore_course,
         name='admin_restore_course'),
    path('admin-panel/archive/teacher/<int:teacher_id>/restore/', views.admin_restore_teacher,
         name='admin_restore_teacher'),
    path('admin-panel/archive/student/<int:abitur_id>/restore/', views.admin_restore_student,
         name='admin_restore_student'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)