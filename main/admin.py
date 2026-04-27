from django.contrib import admin
from .models import Users, School, Parent, Teacher, Abiturient, Course, RecordCourse, Feedback, AboutPage

@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ['login', 'role', 'is_activ']
    list_filter = ['role', 'is_activ']

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'director_full_name', 'address']
    search_fields = ['name', 'address', 'director_last_name', 'director_first_name']
    list_filter = ['name']

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'phone']

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email']

@admin.register(Abiturient)
class AbiturientAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email', 'phone']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher', 'level', 'price', 'start_date']
    list_filter = ['level', 'is_activ']

@admin.register(RecordCourse)
class RecordCourseAdmin(admin.ModelAdmin):
    list_display = ['abiturient', 'course', 'status']
    list_filter = ['status']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['abiturient', 'course', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ['__str__']

    fieldsets = (
        ('Основная информация', {
            'fields': ('page_title', 'main_heading')
        }),
        ('Карточки (верхний блок)', {
            'fields': (
                ('address_title', 'address_content'),
                ('director_title', 'director_content'),
                ('teachers_title', 'teachers_content'),
            )
        }),
        ('О деятельности', {
            'fields': ('about_heading', 'about_paragraph1', 'about_paragraph2')
        }),
        ('Преимущества (JSON)', {
            'fields': ('advantages_heading', 'advantages'),
            'description': 'Формат: [{"title": "🎯 Заголовок", "desc": "Описание"}]'
        }),
        ('Контакты', {
            'fields': (
                'contacts_heading',
                'contact_address',
                'contact_director',
                'contact_phone',
                'contact_email',
                'contact_schedule',
            )
        }),
    )

    def has_add_permission(self, request):
        return not AboutPage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False