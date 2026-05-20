from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Course, Teacher, Abiturient, Feedback, RecordCourse, School, Parent, Users, AboutPage
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from .forms import RegisterForm, LoginForm, RecordCourseForm, FeedbackForm, ProfileForm, AbiturientForm
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .reports import generate_courses_report, generate_students_report, generate_enrollment_report, \
    generate_teachers_report
from .emails import send_welcome_email, send_enrollment_notification
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from django.db.models import Q, Avg
from django.utils import timezone
from datetime import date


# Главная страница со списком курсов
def index(request):
    courses = Course.objects.filter(is_activ=True).select_related('teacher')

    # Получаем параметры фильтрации
    level_filter = request.GET.get('level', '')
    price_sort = request.GET.get('price_sort', '')
    rating_sort = request.GET.get('rating_sort', '')
    search_query = request.GET.get('search', '')

    # Фильтр по уровню (ОГЭ, ЕГЭ)
    if level_filter:
        courses = courses.filter(level__icontains=level_filter)

    # Поиск по названию
    if search_query:
        courses = courses.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    courses = courses.annotate(
        avg_rating=Avg('feedbacks__rating')
    )

    # Сортировка по цене
    if price_sort == 'low_to_high':
        courses = courses.order_by('price')
    elif price_sort == 'high_to_low':
        courses = courses.order_by('-price')

    # Сортировка по рейтингу
    if rating_sort == 'high_to_low':
        courses = courses.order_by('-avg_rating')
    elif rating_sort == 'low_to_high':
        courses = courses.order_by('avg_rating')

    levels = Course.objects.filter(is_activ=True).values_list('level', flat=True).distinct()

    context = {
        'courses': courses,
        'levels': levels,
        'current_level': level_filter,
        'current_price_sort': price_sort,
        'current_rating_sort': rating_sort,
        'search_query': search_query,
    }
    return render(request, 'main/index.html', context)

# Страница деталей курса
def course_detail(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    feedbacks = Feedback.objects.filter(course=course, status='approved').select_related('abiturient')
    avg_rating = feedbacks.aggregate(Avg('rating'))['rating__avg']

    user_enrollment = None
    if request.user.is_authenticated:
        abiturient = Abiturient.objects.filter(user_id=request.user.id).first()
        if abiturient:
            user_enrollment = RecordCourse.objects.filter(
                abiturient=abiturient,
                course=course
            ).first()

    enrolled_count = course.get_enrolled_count()
    is_full = course.is_full()
    available_spots = course.get_available_spots()

    course_started = course.start_date < date.today()
    course_ended = course.end_date < date.today()
    enrollment_closed = course_started or course_ended

    context = {
        'course': course,
        'feedbacks': feedbacks,
        'avg_rating': avg_rating or 0,
        'user_enrollment': user_enrollment,
        'enrolled_count': enrolled_count,
        'is_full': is_full,
        'available_spots': available_spots,
        'max_students': course.max_students,
        'now': date.today(),
        'course_started': course_started,
        'course_ended': course_ended,
        'enrollment_closed': enrollment_closed,
    }
    return render(request, 'main/course_detail.html', context)

# Страница списка преподавателей
def teachers_list(request):
    teachers = Teacher.objects.all()
    return render(request, 'main/teachers_list.html', {'teachers': teachers})

# Страница преподавателя
def teacher_detail(request, teacher_id):
    teacher = get_object_or_404(Teacher, teacher_id=teacher_id)
    courses = Course.objects.filter(teacher=teacher, is_activ=True)
    return render(request, 'main/teacher_detail.html', {
        'teacher': teacher,
        'courses': courses,
    })


# Регистрация
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                # 1. Создаем пользователя
                user = form.save(commit=False)
                user.save()

                # 2. Получаем данные о родителе из формы (уже нормализованные)
                parent_pasport = form.cleaned_data.get('parent_pasport')  # Только цифры
                parent_inn = form.cleaned_data.get('parent_inn')  # Только цифры (12)

                # 3. Ищем существующего родителя по паспорту и ИНН
                parent = Parent.objects.filter(
                    pasport=parent_pasport,
                    inn=parent_inn
                ).first()

                # 4. Если родителя нет - создаем нового
                if not parent:
                    parent = Parent.objects.create(
                        first_name=form.cleaned_data.get('parent_first_name'),
                        last_name=form.cleaned_data.get('parent_last_name'),
                        phone=form.cleaned_data.get('parent_phone'),  # Только цифры
                        pasport=parent_pasport,
                        inn=parent_inn,
                        addres=form.cleaned_data.get('parent_address'),
                    )

                # 5. Обрабатываем школу
                school_id = None
                add_new_school = form.cleaned_data.get('add_new_school')

                if add_new_school:
                    # Создаем новую школу
                    new_school_name = form.cleaned_data.get('new_school_name')
                    new_school_address = form.cleaned_data.get('new_school_address')

                    # 🔍 НОВЫЕ ПОЛЯ: директор разбит на 3 части
                    new_school_director_last_name = form.cleaned_data.get('new_school_director_last_name')
                    new_school_director_first_name = form.cleaned_data.get('new_school_director_first_name')
                    new_school_director_middle_name = form.cleaned_data.get('new_school_director_middle_name', '')

                    # Формируем полное ФИО для отображения (опционально)
                    new_school_director_full = f"{new_school_director_last_name} {new_school_director_first_name}"
                    if new_school_director_middle_name:
                        new_school_director_full += f" {new_school_director_middle_name}"

                    # Проверяем, нет ли уже такой школы
                    existing_school = School.objects.filter(
                        name=new_school_name,
                        address=new_school_address
                    ).first()

                    if existing_school:
                        school_id = existing_school.school_id
                        messages.info(request, 'Такая школа уже существует в базе, используем её')
                    else:
                        # Создаем новую школу с разбитыми полями директора
                        new_school = School.objects.create(
                            name=new_school_name,
                            address=new_school_address,
                            director_last_name=new_school_director_last_name,
                            director_first_name=new_school_director_first_name,
                            director_middle_name=new_school_director_middle_name,
                        )
                        school_id = new_school.school_id
                else:
                    # Используем выбранную школу из списка
                    school_choice = form.cleaned_data.get('school_choice')
                    if school_choice:
                        school_id = int(school_choice)

                # 6. Создаем абитуриента
                Abiturient.objects.create(
                    user_id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    email=user.email,
                    phone=form.cleaned_data.get('phone'),  # Только цифры
                    class_name=form.cleaned_data.get('class_name'),
                    school_id=school_id,
                    parent_id=parent.parent_id,
                )

                # Отправка приветственного письма
                send_welcome_email(user)

                login(request, user)
                messages.success(request, 'Регистрация успешна!')
                return redirect('index')

            except IntegrityError as e:
                messages.error(request, f'Ошибка при сохранении данных: {str(e)}')
                return redirect('register')
            except Exception as e:
                messages.error(request, f'Произошла ошибка при регистрации: {str(e)}')
                return redirect('register')
    else:
        form = RegisterForm()
    return render(request, 'main/register.html', {'form': form})

# Вход
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Вход выполнен!')
            return redirect('index')
    else:
        form = LoginForm()
    return render(request, 'main/login.html', {'form': form})


# Выход
def user_logout(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('index')


# Личный кабинет
@login_required
def profile(request):
    user = request.user
    abiturient = Abiturient.objects.filter(user_id=user.id).first()

    if abiturient:
        records = RecordCourse.objects.filter(abiturient=abiturient).select_related('course')
        feedbacks = Feedback.objects.filter(abiturient=abiturient).select_related('course')
        parent = abiturient.parent
        school = abiturient.school
    else:
        abiturient = None
        records = []
        feedbacks = []
        parent = None
        school = None

    context = {
        'user': user,
        'abiturient': abiturient,
        'records': records,
        'feedbacks': feedbacks,
        'parent': parent,
        'school': school,
    }
    return render(request, 'main/profile.html', context)


# Запись на курс
@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    abiturient = Abiturient.objects.filter(user_id=request.user.id).first()

    if not abiturient:
        messages.error(request, 'Сначала заполните профиль абитуриента')
        return redirect('profile')

    # Проверяем, активен ли курс
    if not course.is_activ:
        messages.error(request, 'Этот курс больше не активен')
        return redirect('course_detail', course_id=course_id)

    # Если курс уже начался
    if course.start_date < date.today():
        messages.error(request, f'Курс "{course.name}" уже начался ({course.start_date}). Запись закрыта.')
        return redirect('course_detail', course_id=course_id)

    # Если курс уже закончился
    if course.end_date < date.today():
        messages.error(request, f'Курс "{course.name}" уже завершился ({course.end_date}). Запись закрыта.')
        return redirect('course_detail', course_id=course_id)

    # Если набран курс
    if course.is_full():
        messages.error(request, f'Курс "{course.name}" уже набран. Свободных мест нет.')
        return redirect('course_detail', course_id=course_id)

    # Проверяем, не записан ли уже пользователь на этот курс
    existing_record = RecordCourse.objects.filter(
        abiturient=abiturient,
        course=course
    ).first()

    if existing_record:
        messages.warning(request, f'Вы уже записаны на курс "{course.name}" (статус: {existing_record.status})')
        return redirect('profile')

    if request.method == 'POST':
        try:
            # Ещё раз проверяем все условия
            if course.start_date < date.today():
                messages.error(request, 'Курс уже начался. Запись закрыта.')
                return redirect('course_detail', course_id=course_id)

            if course.end_date < date.today():
                messages.error(request, 'Курс уже завершился. Запись закрыта.')
                return redirect('course_detail', course_id=course_id)

            if course.is_full():
                messages.error(request, 'Курс уже набран. Свободных мест нет.')
                return redirect('course_detail', course_id=course_id)

            record = RecordCourse.objects.create(
                abiturient=abiturient,
                course=course,
                status='В обработке',
            )

            try:
                send_enrollment_notification(abiturient, course)
            except Exception as email_error:
                # Логируем ошибку, но не прерываем запись
                print(f"Ошибка при отправке email: {email_error}")
                messages.warning(
                    request,
                    'Вы успешно записались на курс.'
                )

            messages.success(request, f'Вы записались на курс "{course.name}"!')
            return redirect('profile')

        except IntegrityError:
            messages.error(request, 'Ошибка при записи на курс. Попробуйте позже.')
            return redirect('course_detail', course_id=course_id)

        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('course_detail', course_id=course_id)

    return render(request, 'main/enroll_course.html', {
        'course': course,
        'enrolled_count': course.get_enrolled_count(),
        'is_full': course.is_full(),
        'available_spots': course.get_available_spots(),
    })

# Оставить отзыв
@login_required
def add_feedback(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    abiturient = Abiturient.objects.filter(user_id=request.user.id).first()

    if not abiturient:
        messages.error(request, 'Сначала заполните профиль абитуриента')
        return redirect('profile')

    # Проверяем существующий отзыв
    existing_feedback = Feedback.objects.filter(
        abiturient=abiturient,
        course=course
    ).first()

    if existing_feedback:
        messages.warning(request, 'Вы уже оставляли отзыв на этот курс')
        return redirect('course_detail', course_id=course_id)

    # Проверяем запись на курс
    is_enrolled = RecordCourse.objects.filter(
        abiturient=abiturient,
        course=course
    ).exists()

    if not is_enrolled:
        messages.warning(request, 'Вы можете оставить отзыв только после записи на курс')
        return redirect('course_detail', course_id=course_id)

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        is_valid = form.is_valid()

        if form.is_valid():
            try:
                feedback = form.save(commit=False)
                feedback.abiturient = abiturient
                feedback.course = course
                feedback.status = 'pending'
                feedback.save()

                messages.success(request, 'Спасибо за ваш отзыв! Он появится после модерации.')
                return redirect('course_detail', course_id=course_id)

            except IntegrityError as e:
                messages.error(request, 'Ошибка при сохранении отзыва (дубликат)')
                return redirect('course_detail', course_id=course_id)
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'Ошибка: {str(e)}')
                return redirect('course_detail', course_id=course_id)
    else:
        print("\nGET запрос - показываем форму")

    form = FeedbackForm()

    return render(request, 'main/add_feedback.html', {
        'form': form,
        'course': course,
    })

# Отчеты
@staff_member_required
def export_courses_report(request):
    return generate_courses_report()

@staff_member_required
def export_students_report(request):
    return generate_students_report()

@staff_member_required
def export_teachers_report(request):
    return generate_teachers_report()

@staff_member_required
def export_enrollment_report(request):
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    start_date = None
    end_date = None

    if start_date_str:
        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            from django.contrib import messages
            messages.error(request, 'Неверный формат даты начала')
            return redirect('reports_enrollment')

    if end_date_str:
        try:
            from datetime import datetime
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            from django.contrib import messages
            messages.error(request, 'Неверный формат даты окончания')
            return redirect('reports_enrollment')

    # Проверка: дата начала не должна быть позже даты окончания
    if start_date and end_date:
        if start_date > end_date:
            from django.contrib import messages
            messages.error(request, 'Дата начала не может быть позже даты окончания')
            return redirect('reports_enrollment')

    return generate_enrollment_report(start_date=start_date, end_date=end_date)

@staff_member_required
def reports_page(request):
    return render(request, 'admin/reports.html')

# О нас
def about(request):
    about_content = AboutPage.get_content()

    import json
    try:
        advantages = json.loads(about_content.advantages) if isinstance(about_content.advantages, str) else about_content.advantages
    except:
        advantages = []

    context = {
        'about': about_content,
        'advantages': advantages,
    }
    return render(request, 'main/about.html', context)

# Редактирование профиля
@login_required
def edit_profile(request):
    user = request.user
    abiturient = Abiturient.objects.filter(user_id=user.id).first()

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        class_name = request.POST.get('class_name', '').strip()

        # Имя (только буквы)
        if not first_name:
            messages.error(request, 'Имя обязательно')
            return redirect('edit_profile')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', first_name):
            messages.error(request, 'Имя должно содержать только буквы, пробелы и дефис')
            return redirect('edit_profile')

        # Фамилия (только буквы)
        if not last_name:
            messages.error(request, 'Фамилия обязательна')
            return redirect('edit_profile')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', last_name):
            messages.error(request, 'Фамилия должна содержать только буквы, пробелы и дефис')
            return redirect('edit_profile')

        # Email
        if not email:
            messages.error(request, 'Email обязателен')
            return redirect('edit_profile')
        if '@' not in email:
            messages.error(request, 'Email должен содержать символ @')
            return redirect('edit_profile')
        domain_part = email.split('@')[-1]
        if '.' not in domain_part:
            messages.error(request, 'Email должен содержать точку и домен')
            return redirect('edit_profile')
        if len(domain_part.split('.')[-1]) < 2:
            messages.error(request, 'Некорректный домен email')
            return redirect('edit_profile')

        # Проверка уникальности email (исключая текущего пользователя)
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return redirect('edit_profile')

        # Телефон (11 цифр)
        if not phone:
            messages.error(request, 'Телефон обязателен')
            return redirect('edit_profile')
        phone_digits = re.sub(r'\D', '', phone)
        if len(phone_digits) != 11:
            messages.error(request, f'Телефон должен содержать 11 цифр (сейчас: {len(phone_digits)})')
            return redirect('edit_profile')
        if not phone_digits.startswith(('7', '8')):
            messages.error(request, 'Телефон должен начинаться с 7 или 8')
            return redirect('edit_profile')

        # Класс (1-11)
        if not class_name:
            messages.error(request, 'Класс обязателен')
            return redirect('edit_profile')
        class_match = re.match(r'^([1-9]|10|11)([а-яА-Я]?)$', class_name.strip())
        if not class_match:
            messages.error(request, 'Класс в формате 9а, 10б, 11в')
            return redirect('edit_profile')
        grade = int(class_match.group(1))
        if grade > 11:
            messages.error(request, 'Класс должен быть не больше 11')
            return redirect('edit_profile')

        try:
            # Обновляем данные пользователя (User)
            user.first_name = first_name.strip().title()
            user.last_name = last_name.strip().title()
            user.email = email.lower().strip()
            user.save()

            # Обновляем данные абитуриента (Abiturient)
            if abiturient:
                abiturient.first_name = first_name.strip().title()
                abiturient.last_name = last_name.strip().title()
                abiturient.email = email.lower().strip()
                abiturient.phone = phone_digits
                abiturient.class_name = class_name.strip()

                # Обработка фото
                if request.FILES.get('photo'):
                    abiturient.photo = request.FILES['photo']

                # Удаление фото
                if request.POST.get('photo-clear') == 'on':
                    abiturient.photo.delete(save=False)
                    abiturient.photo = None

                abiturient.save()
            else:
                # Если записи нет - создаём новую
                abiturient = Abiturient.objects.create(
                    user_id=user.id,
                    first_name=first_name.strip().title(),
                    last_name=last_name.strip().title(),
                    email=email.lower().strip(),
                    phone=phone_digits,
                    class_name=class_name.strip(),
                    photo=request.FILES.get('photo'),
                )

            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')

        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении данных')
            return redirect('edit_profile')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('edit_profile')

    return render(request, 'main/edit_profile.html', {
        'user': user,
        'abiturient': abiturient,
    })


# Админ-панель
@staff_member_required
def admin_dashboard(request):
    courses_count = Course.objects.count()
    teachers_count = Teacher.objects.count()
    students_count = Abiturient.objects.count()
    schools_count = School.objects.count()
    records_count = RecordCourse.objects.count()

    recent_records = RecordCourse.objects.select_related('abiturient', 'course')[:5]

    context = {
        'courses_count': courses_count,
        'teachers_count': teachers_count,
        'students_count': students_count,
        'schools_count': schools_count,
        'records_count': records_count,
        'recent_records': recent_records,
    }
    return render(request, 'admin/dashboard.html', context)

# Управление курсами
@staff_member_required
def admin_courses(request):
    courses = Course.objects.select_related('teacher').filter(is_activ=True).all()
    return render(request, 'admin/courses.html', {'courses': courses})

@staff_member_required
def admin_add_course(request):
    teachers = Teacher.objects.filter(is_activ=True)

    if request.method == 'POST':
        # Валидация данных
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        teacher_id = request.POST.get('teacher_id')
        level = request.POST.get('level', '').strip()
        price = request.POST.get('price')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        raspisanie = request.POST.get('raspisanie', '').strip()
        photo_url = request.POST.get('photo_url', '').strip()

        # Проверка обязательных полей
        if not name:
            messages.error(request, 'Название курса обязательно')
            return redirect('admin_add_course')

        if not teacher_id:
            messages.error(request, 'Выберите преподавателя')
            return redirect('admin_add_course')

        # Валидация цены
        if not price:
            messages.error(request, 'Укажите цену курса')
            return redirect('admin_add_course')

        try:
            price_value = float(price)
            if price_value <= 0:
                messages.error(request, 'Цена должна быть положительным числом')
                return redirect('admin_add_course')
        except (ValueError, TypeError):
            messages.error(request, 'Неверный формат цены')
            return redirect('admin_add_course')

        # Валидация дат
        if start_date and end_date:
            from datetime import datetime
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()

                if start > end:
                    messages.error(request, 'Дата начала не может быть позже даты окончания')
                    return redirect('admin_add_course')

                if start < timezone.now().date():
                    messages.warning(request, 'Дата начала курса в прошлом')
            except ValueError:
                messages.error(request, 'Неверный формат даты')
                return redirect('admin_add_course')

        try:
            course = Course(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                teacher_id=request.POST.get('teacher_id'),
                level=request.POST.get('level'),
                price=request.POST.get('price'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                raspisanie=request.POST.get('raspisanie'),
                photo_url=request.POST.get('photo_url', ''),
                is_activ=request.POST.get('is_activ') == 'on',
                max_students=request.POST.get('max_students', 15),
            )

            # Обработка фото
            if request.FILES.get('photo'):
                course.photo = request.FILES['photo']

            course.save()
            messages.success(request, 'Курс успешно добавлен!')
            return redirect('admin_courses')

        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении курса')
            return redirect('admin_add_course')

        except Exception as e:
            messages.error(request, f'Произошла ошибка: {str(e)}')
            return redirect('admin_add_course')

    return render(request, 'admin/add_course.html', {'teachers': teachers})

@staff_member_required
def admin_edit_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)
    teachers = Teacher.objects.filter(is_activ=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        teacher_id = request.POST.get('teacher_id')
        level = request.POST.get('level', '').strip()
        price = request.POST.get('price')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        raspisanie = request.POST.get('raspisanie', '').strip()
        photo_url = request.POST.get('photo_url', '').strip()
        course.max_students = request.POST.get('max_students', course.max_students)

        # Валидация
        if not name:
            messages.error(request, 'Название курса обязательно')
            return redirect('admin_edit_course', course_id=course_id)

        if not teacher_id:
            messages.error(request, 'Выберите преподавателя')
            return redirect('admin_edit_course', course_id=course_id)

        if price:
            try:
                price_value = float(price)
                if price_value <= 0:
                    messages.error(request, 'Цена должна быть положительным числом')
                    return redirect('admin_edit_course', course_id=course_id)
            except (ValueError, TypeError):
                messages.error(request, 'Неверный формат цены')
                return redirect('admin_edit_course', course_id=course_id)
        else:
            price_value = course.price

        # Валидация дат
        if start_date and end_date:
            from datetime import datetime
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()

                if start > end:
                    messages.error(request, 'Дата начала не может быть позже даты окончания')
                    return redirect('admin_edit_course', course_id=course_id)
            except ValueError:
                messages.error(request, 'Неверный формат даты')
                return redirect('admin_edit_course', course_id=course_id)

        try:
            course.name = request.POST.get('name')
            course.description = request.POST.get('description')
            course.teacher_id = request.POST.get('teacher_id')
            course.level = request.POST.get('level')
            course.price = request.POST.get('price')
            course.start_date = request.POST.get('start_date')
            course.end_date = request.POST.get('end_date')
            course.raspisanie = request.POST.get('raspisanie')
            course.photo_url = request.POST.get('photo_url', '')
            course.max_students = request.POST.get('max_students', course.max_students)

            # Обработка фото
            if request.FILES.get('photo'):
                course.photo = request.FILES['photo']

            # Удаление фото
            if request.POST.get('photo-clear') == 'on':
                course.photo.delete(save=False)
                course.photo = None

            course.save()
            messages.success(request, 'Курс успешно обновлен!')
            return redirect('admin_courses')

        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении курса')
            return redirect('admin_edit_course', course_id=course_id)

    return render(request, 'admin/edit_course.html', {
        'course': course,
        'teachers': teachers,
    })

# Управление преподавателями
@staff_member_required
def admin_teachers(request):
    teachers = Teacher.objects.select_related('user').filter(is_activ=True).all()
    return render(request, 'admin/teachers.html', {'teachers': teachers})


@staff_member_required
def admin_add_teacher(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        # 🔍 ВАЛИДАЦИЯ ЛОГИНА
        if not username:
            messages.error(request, 'Логин обязателен')
            return redirect('admin_add_teacher')

        if len(username) < 3:
            messages.error(request, 'Логин должен содержать минимум 3 символа')
            return redirect('admin_add_teacher')

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messages.error(request, 'Логин может содержать только буквы, цифры и _')
            return redirect('admin_add_teacher')

        # 🔍 ВАЛИДАЦИЯ ПАРОЛЯ
        if not password or len(password) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов')
            return redirect('admin_add_teacher')

        # 🔍 ВАЛИДАЦИЯ ИМЕНИ (только буквы)
        if not first_name:
            messages.error(request, 'Имя обязательно')
            return redirect('admin_add_teacher')

        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', first_name):
            messages.error(request, 'Имя должно содержать только буквы, пробелы и дефис')
            return redirect('admin_add_teacher')

        # 🔍 ВАЛИДАЦИЯ ФАМИЛИИ (только буквы)
        if not last_name:
            messages.error(request, 'Фамилия обязательна')
            return redirect('admin_add_teacher')

        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', last_name):
            messages.error(request, 'Фамилия должна содержать только буквы, пробелы и дефис')
            return redirect('admin_add_teacher')

        # 🔍 ВАЛИДАЦИЯ EMAIL
        if not email:
            messages.error(request, 'Email обязателен')
            return redirect('admin_add_teacher')

        if '@' not in email:
            messages.error(request, 'Email должен содержать символ @')
            return redirect('admin_add_teacher')

        domain_part = email.split('@')[-1]
        if '.' not in domain_part:
            messages.error(request, 'Email должен содержать точку и домен (например, @example.com)')
            return redirect('admin_add_teacher')

        if len(domain_part.split('.')[-1]) < 2:
            messages.error(request, 'Некорректный домен email')
            return redirect('admin_add_teacher')

        # 🔍 ПРОВЕРКА УНИКАЛЬНОСТИ ЛОГИНА
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким логином уже существует')
            return redirect('admin_add_teacher')

        # 🔍 ПРОВЕРКА УНИКАЛЬНОСТИ EMAIL
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return redirect('admin_add_teacher')

        try:
            # Создаем нового пользователя
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name.strip().title(),
                last_name=last_name.strip().title(),
                is_staff=False,
                is_active=True,
            )

            # Создаем запись в таблице Teacher
            teacher = Teacher(
                user_id=user.id,
                first_name=first_name.strip().title(),
                last_name=last_name.strip().title(),
                description=request.POST.get('description', ''),
                photo_url=request.POST.get('photo_url', ''),
                email=email.lower().strip(),
            )
            # Обработка фото
            if request.FILES.get('photo'):
                teacher.photo = request.FILES['photo']

            teacher.save()

            messages.success(request, f'Преподаватель {username} успешно добавлен!')
            return redirect('admin_teachers')

        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении данных преподавателя')
            return redirect('admin_add_teacher')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('admin_add_teacher')

    return render(request, 'admin/add_teacher.html')


@staff_member_required
def admin_edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, teacher_id=teacher_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()

        # 🔍 ВАЛИДАЦИЯ ИМЕНИ
        if not first_name:
            messages.error(request, 'Имя обязательно')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', first_name):
            messages.error(request, 'Имя должно содержать только буквы, пробелы и дефис')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

        # 🔍 ВАЛИДАЦИЯ ФАМИЛИИ
        if not last_name:
            messages.error(request, 'Фамилия обязательна')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', last_name):
            messages.error(request, 'Фамилия должна содержать только буквы, пробелы и дефис')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

        # 🔍 ВАЛИДАЦИЯ EMAIL
        if not email:
            messages.error(request, 'Email обязателен')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

        if '@' not in email:
            messages.error(request, 'Email должен содержать @')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

        domain_part = email.split('@')[-1]
        if '.' not in domain_part:
            messages.error(request, 'Email должен содержать домен')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

        try:
            # Обновляем данные пользователя
            user = teacher.user
            user.first_name = first_name.strip().title()
            user.last_name = last_name.strip().title()
            user.email = email.lower().strip()
            user.save()

            # Обновляем данные преподавателя
            teacher.first_name = first_name.strip().title()
            teacher.last_name = last_name.strip().title()
            teacher.description = request.POST.get('description', '')
            teacher.photo_url = request.POST.get('photo_url', '')
            teacher.email = email.lower().strip()

            # Обработка фото
            if request.FILES.get('photo'):
                teacher.photo = request.FILES['photo']

            # Удаление фото
            if request.POST.get('photo-clear') == 'on':
                teacher.photo.delete(save=False)
                teacher.photo = None

            teacher.save()

            messages.success(request, f'Преподаватель {last_name} {first_name} успешно обновлен!')
            return redirect('admin_teachers')

        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении данных')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('admin_edit_teacher', teacher_id=teacher_id)

    return render(request, 'admin/edit_teacher.html', {'teacher': teacher})


# Управление заявками на курсы
@staff_member_required
def admin_records(request):
    records = RecordCourse.objects.select_related('abiturient', 'course__teacher').all()
    return render(request, 'admin/records.html', {'records': records})

# Обновление статуса заявки
@staff_member_required
def admin_update_record_status(request, record_id):
    record = get_object_or_404(RecordCourse, record_id=record_id)
    valid_statuses = ['В обработке', 'Подтверждена', 'Отклонена', 'Завершена']

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if not new_status or new_status not in valid_statuses:
            messages.error(request, 'Неверный статус')
            return redirect('admin_update_record_status', record_id=record_id)

        old_status = record.status

        try:
            record.status = new_status
            record.save()

            # Отправка уведомления об изменении статуса
            if old_status != new_status:
                try:
                    from .emails import send_status_change_notification
                    send_status_change_notification(
                        abiturient=record.abiturient,
                        course=record.course,
                        old_status=old_status,
                        new_status=new_status
                    )
                    messages.success(request, 'Статус заявки обновлен! Уведомление отправлено на email.')
                except Exception as e:
                    messages.warning(request, f'Статус обновлен, но email не отправлен: {str(e)}')
            else:
                messages.success(request, 'Статус заявки обновлен!')

            return redirect('admin_records')

        except IntegrityError:
            messages.error(request, 'Ошибка при обновлении статуса')
            return redirect('admin_update_record_status', record_id=record_id)

    return render(request, 'admin/update_record_status.html', {'record': record})

# Управление школами
@staff_member_required
def admin_schools(request):
    schools = School.objects.all()
    return render(request, 'admin/schools.html', {'schools': schools})

@staff_member_required
def admin_add_school(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        director_last_name = request.POST.get('director_last_name', '').strip()
        director_first_name = request.POST.get('director_first_name', '').strip()
        director_middle_name = request.POST.get('director_middle_name', '').strip()

        # Валидация обязательных полей
        if not name:
            messages.error(request, 'Название школы обязательно')
            return redirect('admin_add_school')

        if not address:
            messages.error(request, 'Адрес школы обязателен')
            return redirect('admin_add_school')

        if not director_last_name:
            messages.error(request, 'Фамилия директора обязательна')
            return redirect('admin_add_school')

        if not director_first_name:
            messages.error(request, 'Имя директора обязательно')
            return redirect('admin_add_school')

        if not director_middle_name:
            messages.error(request, 'Отчество директора обязательно')
            return redirect('admin_add_school')

        # Проверка на дубликат
        existing_school = School.objects.filter(
            name=name,
            address=address
        ).first()

        if existing_school:
            messages.warning(request, 'Школа с таким названием и адресом уже существует')
            return redirect('admin_schools')

        try:
            school = School(
                name=name,
                address=address,
                director_last_name=director_last_name,
                director_first_name=director_first_name,
                director_middle_name=director_middle_name,
            )
            school.save()
            messages.success(request, 'Школа успешно добавлена!')
            return redirect('admin_schools')
        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении школы')
            return redirect('admin_add_school')

    return render(request, 'admin/add_school.html')

@staff_member_required
def admin_edit_school(request, school_id):
    school = get_object_or_404(School, school_id=school_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        director_last_name = request.POST.get('director_last_name', '').strip()
        director_first_name = request.POST.get('director_first_name', '').strip()
        director_middle_name = request.POST.get('director_middle_name', '').strip()

        if not name or not address or not director_last_name or not director_first_name or not director_middle_name:
            messages.error(request, 'Все поля обязательны для заполнения')
            return redirect('admin_edit_school', school_id=school_id)

        # Проверка на дубликат
        existing_school = School.objects.filter(
            name=name,
            address=address
        ).exclude(school_id=school_id).first()

        if existing_school:
            messages.warning(request, 'Школа с таким названием и адресом уже существует')
            return redirect('admin_schools')

        try:
            school.name = name
            school.address = address
            school.director_last_name = director_last_name
            school.director_first_name = director_first_name
            school.director_middle_name = director_middle_name
            school.save()
            messages.success(request, f'Школа "{name}" успешно обновлена!')
            return redirect('admin_schools')
        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении школы')
            return redirect('admin_edit_school', school_id=school_id)

    return render(request, 'admin/edit_school.html', {'school': school})

@staff_member_required
def admin_delete_school(request, school_id):
    school = get_object_or_404(School, school_id=school_id)
    school_name = school.name
    school.delete()
    messages.success(request, f'Школа "{school_name}" успешно удалена!')
    return redirect('admin_schools')


# Управление абитуриентами
@staff_member_required
def admin_students(request):
    students = Abiturient.objects.select_related('school', 'parent').filter(is_activ=True).all()
    return render(request, 'admin/students.html', {'students': students})

@staff_member_required
def admin_add_student(request):
    schools = School.objects.all()

    if request.method == 'POST':
        # 🔍 ПОЛУЧАЕМ ДАННЫЕ
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        class_name = request.POST.get('class_name', '').strip()
        school_id = request.POST.get('school_id')

        # Данные родителя
        parent_first_name = request.POST.get('parent_first_name', '').strip()
        parent_last_name = request.POST.get('parent_last_name', '').strip()
        parent_phone = request.POST.get('parent_phone', '').strip()
        parent_pasport = request.POST.get('parent_pasport', '').strip()
        parent_inn = request.POST.get('parent_inn', '').strip()
        parent_address = request.POST.get('parent_address', '').strip()

        # Логин
        if not username:
            messages.error(request, 'Логин обязателен')
            return redirect('admin_add_student')
        if len(username) < 3:
            messages.error(request, 'Логин должен содержать минимум 3 символа')
            return redirect('admin_add_student')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            messages.error(request, 'Логин может содержать только буквы, цифры и _')
            return redirect('admin_add_student')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким логином уже существует')
            return redirect('admin_add_student')

        # Email
        if not email:
            messages.error(request, 'Email обязателен')
            return redirect('admin_add_student')
        if '@' not in email:
            messages.error(request, 'Email должен содержать символ @')
            return redirect('admin_add_student')
        domain_part = email.split('@')[-1]
        if '.' not in domain_part:
            messages.error(request, 'Email должен содержать точку и домен')
            return redirect('admin_add_student')
        if len(domain_part.split('.')[-1]) < 2:
            messages.error(request, 'Некорректный домен email')
            return redirect('admin_add_student')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return redirect('admin_add_student')

        # Пароль
        if not password or len(password) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов')
            return redirect('admin_add_student')
        if not re.search(r'[A-Za-z]', password):
            messages.error(request, 'Пароль должен содержать хотя бы одну букву')
            return redirect('admin_add_student')
        if not re.search(r'\d', password):
            messages.error(request, 'Пароль должен содержать хотя бы одну цифру')
            return redirect('admin_add_student')

        # Имя (только буквы)
        if not first_name:
            messages.error(request, 'Имя обязательно')
            return redirect('admin_add_student')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', first_name):
            messages.error(request, 'Имя должно содержать только буквы, пробелы и дефис')
            return redirect('admin_add_student')

        # Фамилия (только буквы)
        if not last_name:
            messages.error(request, 'Фамилия обязательна')
            return redirect('admin_add_student')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', last_name):
            messages.error(request, 'Фамилия должна содержать только буквы, пробелы и дефис')
            return redirect('admin_add_student')

        # Телефон (11 цифр)
        if not phone:
            messages.error(request, 'Телефон обязателен')
            return redirect('admin_add_student')
        phone_digits = re.sub(r'\D', '', phone)
        if len(phone_digits) != 11:
            messages.error(request, f'Телефон должен содержать 11 цифр (сейчас: {len(phone_digits)})')
            return redirect('admin_add_student')
        if not phone_digits.startswith(('7', '8')):
            messages.error(request, 'Телефон должен начинаться с 7 или 8')
            return redirect('admin_add_student')

        # Класс (1-11)
        if not class_name:
            messages.error(request, 'Класс обязателен')
            return redirect('admin_add_student')
        class_match = re.match(r'^([1-9]|10|11)([а-яА-Я]?)$', class_name.strip())
        if not class_match:
            messages.error(request, 'Класс в формате 9а, 10б, 11в')
            return redirect('admin_add_student')
        grade = int(class_match.group(1))
        if grade > 11:
            messages.error(request, 'Класс должен быть не больше 11')
            return redirect('admin_add_student')

        # Имя родителя
        if not parent_first_name:
            messages.error(request, 'Имя родителя обязательно')
            return redirect('admin_add_student')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', parent_first_name):
            messages.error(request, 'Имя родителя должно содержать только буквы')
            return redirect('admin_add_student')

        # Фамилия родителя
        if not parent_last_name:
            messages.error(request, 'Фамилия родителя обязательна')
            return redirect('admin_add_student')
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', parent_last_name):
            messages.error(request, 'Фамилия родителя должна содержать только буквы')
            return redirect('admin_add_student')

        # Телефон родителя (11 цифр)
        if not parent_phone:
            messages.error(request, 'Телефон родителя обязателен')
            return redirect('admin_add_student')
        parent_phone_digits = re.sub(r'\D', '', parent_phone)
        if len(parent_phone_digits) != 11:
            messages.error(request, f'Телефон родителя: 11 цифр (сейчас: {len(parent_phone_digits)})')
            return redirect('admin_add_student')

        # Паспорт (10 цифр)
        if not parent_pasport:
            messages.error(request, 'Паспорт родителя обязателен')
            return redirect('admin_add_student')
        passport_digits = re.sub(r'\s', '', parent_pasport)
        if len(passport_digits) != 10:
            messages.error(request, 'Паспорт: 10 цифр (4 серия + 6 номер)')
            return redirect('admin_add_student')

        # ИНН (12 цифр)
        if not parent_inn:
            messages.error(request, 'ИНН родителя обязателен')
            return redirect('admin_add_student')
        inn_digits = re.sub(r'\D', '', parent_inn)
        if len(inn_digits) != 12:
            messages.error(request, 'ИНН должен содержать 12 цифр')
            return redirect('admin_add_student')
        if inn_digits[0] not in '1234':
            messages.warning(request, 'ИНН физ.лица обычно начинается с 1, 2, 3 или 4')

        parent = Parent.objects.filter(pasport=passport_digits, inn=inn_digits).first()

        if not parent:
            try:
                parent = Parent.objects.create(
                    first_name=parent_first_name.strip().title(),
                    last_name=parent_last_name.strip().title(),
                    phone=parent_phone_digits,
                    pasport=passport_digits,
                    inn=inn_digits,
                    addres=parent_address,
                )
            except IntegrityError:
                messages.error(request, 'Ошибка при сохранении данных родителя')
                return redirect('admin_add_student')

        try:
            # 1. Создаем пользователя
            user = User.objects.create_user(
                username=username,
                email=email.lower().strip(),
                password=password,
                first_name=first_name.strip().title(),
                last_name=last_name.strip().title(),
                is_staff=False,
                is_active=True,
            )

            # 2. Создаем абитуриента
            abiturient = Abiturient.objects.create(
                user_id=user.id,
                first_name=first_name.strip().title(),
                last_name=last_name.strip().title(),
                email=email.lower().strip(),
                phone=phone_digits,
                class_name=class_name.strip(),
                school_id=school_id or None,
                parent_id=parent.parent_id,
            )

            messages.success(request, f'Абитуриент {username} успешно добавлен!')
            return redirect('admin_students')

        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении данных абитуриента')
            return redirect('admin_add_student')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('admin_add_student')

    return render(request, 'admin/add_student.html', {'schools': schools})


@staff_member_required
def admin_edit_student(request, abitur_id):
    abiturient = get_object_or_404(Abiturient, abitur_id=abitur_id)
    schools = School.objects.all()
    parent = abiturient.parent if abiturient.parent else None

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        class_name = request.POST.get('class_name', '').strip()
        school_id = request.POST.get('school_id')

        # Данные родителя
        parent_first_name = request.POST.get('parent_first_name', '').strip()
        parent_last_name = request.POST.get('parent_last_name', '').strip()
        parent_phone = request.POST.get('parent_phone', '').strip()
        parent_pasport = request.POST.get('parent_pasport', '').strip()
        parent_inn = request.POST.get('parent_inn', '').strip()
        parent_address = request.POST.get('parent_address', '').strip()

        # Имя (только буквы)
        if not first_name:
            messages.error(request, 'Имя обязательно')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', first_name):
            messages.error(request, 'Имя должно содержать только буквы, пробелы и дефис')
            return redirect('admin_edit_student', abitur_id=abitur_id)

        # Фамилия (только буквы)
        if not last_name:
            messages.error(request, 'Фамилия обязательна')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', last_name):
            messages.error(request, 'Фамилия должна содержать только буквы, пробелы и дефис')
            return redirect('admin_edit_student', abitur_id=abitur_id)

        # Email
        if not email:
            messages.error(request, 'Email обязателен')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        if '@' not in email:
            messages.error(request, 'Email должен содержать символ @')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        domain_part = email.split('@')[-1]
        if '.' not in domain_part:
            messages.error(request, 'Email должен содержать точку и домен')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        if len(domain_part.split('.')[-1]) < 2:
            messages.error(request, 'Некорректный домен email')
            return redirect('admin_edit_student', abitur_id=abitur_id)

        # Проверка уникальности email (исключая текущего пользователя)
        if User.objects.filter(email=email).exclude(id=abiturient.user_id).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return redirect('admin_edit_student', abitur_id=abitur_id)

        # Телефон (11 цифр)
        if not phone:
            messages.error(request, 'Телефон обязателен')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        phone_digits = re.sub(r'\D', '', phone)
        if len(phone_digits) != 11:
            messages.error(request, f'Телефон должен содержать 11 цифр (сейчас: {len(phone_digits)})')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        if not phone_digits.startswith(('7', '8')):
            messages.error(request, 'Телефон должен начинаться с 7 или 8')
            return redirect('admin_edit_student', abitur_id=abitur_id)

        # Класс (1-11)
        if not class_name:
            messages.error(request, 'Класс обязателен')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        class_match = re.match(r'^([1-9]|10|11)([а-яА-Я]?)$', class_name.strip())
        if not class_match:
            messages.error(request, 'Класс в формате 9а, 10б, 11в')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        grade = int(class_match.group(1))
        if grade > 11:
            messages.error(request, 'Класс должен быть не больше 11')
            return redirect('admin_edit_student', abitur_id=abitur_id)

        if parent:
            # Имя родителя
            if not parent_first_name:
                messages.error(request, 'Имя родителя обязательно')
                return redirect('admin_edit_student', abitur_id=abitur_id)
            if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', parent_first_name):
                messages.error(request, 'Имя родителя должно содержать только буквы')
                return redirect('admin_edit_student', abitur_id=abitur_id)

            # Фамилия родителя
            if not parent_last_name:
                messages.error(request, 'Фамилия родителя обязательна')
                return redirect('admin_edit_student', abitur_id=abitur_id)
            if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', parent_last_name):
                messages.error(request, 'Фамилия родителя должна содержать только буквы')
                return redirect('admin_edit_student', abitur_id=abitur_id)

            # Телефон родителя (11 цифр)
            if not parent_phone:
                messages.error(request, 'Телефон родителя обязателен')
                return redirect('admin_edit_student', abitur_id=abitur_id)
            parent_phone_digits = re.sub(r'\D', '', parent_phone)
            if len(parent_phone_digits) != 11:
                messages.error(request, f'Телефон родителя: 11 цифр (сейчас: {len(parent_phone_digits)})')
                return redirect('admin_edit_student', abitur_id=abitur_id)

            # Паспорт (10 цифр)
            if parent_pasport:
                passport_digits = re.sub(r'\s', '', parent_pasport)
                if len(passport_digits) != 10:
                    messages.error(request, 'Паспорт: 10 цифр (4 серия + 6 номер)')
                    return redirect('admin_edit_student', abitur_id=abitur_id)
            else:
                passport_digits = parent.pasport

            # ИНН (12 цифр)
            if parent_inn:
                inn_digits = re.sub(r'\D', '', parent_inn)
                if len(inn_digits) != 12:
                    messages.error(request, 'ИНН должен содержать 12 цифр')
                    return redirect('admin_edit_student', abitur_id=abitur_id)
                if inn_digits[0] not in '1234':
                    messages.warning(request, 'ИНН физ.лица обычно начинается с 1, 2, 3 или 4')
            else:
                inn_digits = parent.inn
        else:
            # Если родителя нет, используем старые значения
            passport_digits = parent.pasport if parent else ''
            inn_digits = parent.inn if parent else ''
            parent_phone_digits = parent.phone if parent else ''

        try:
            # Обновляем данные пользователя
            user = abiturient.user
            user.first_name = first_name.strip().title()
            user.last_name = last_name.strip().title()
            user.email = email.lower().strip()
            user.save()

            # Обновляем данные абитуриента
            abiturient.first_name = first_name.strip().title()
            abiturient.last_name = last_name.strip().title()
            abiturient.email = email.lower().strip()
            abiturient.phone = phone_digits
            abiturient.class_name = class_name.strip()
            abiturient.school_id = school_id or None
            abiturient.save()

            # Обновляем данные родителя
            if parent:
                parent.first_name = parent_first_name.strip().title()
                parent.last_name = parent_last_name.strip().title()
                parent.phone = parent_phone_digits
                parent.pasport = passport_digits
                parent.inn = inn_digits
                parent.addres = parent_address
                parent.save()

            messages.success(request, f'Абитуриент {last_name} {first_name} успешно обновлен!')
            return redirect('admin_students')

        except IntegrityError:
            messages.error(request, 'Ошибка при сохранении данных')
            return redirect('admin_edit_student', abitur_id=abitur_id)
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
            return redirect('admin_edit_student', abitur_id=abitur_id)

    return render(request, 'admin/edit_student.html', {
        'abiturient': abiturient,
        'schools': schools,
        'parent': parent,
    })

# Редактирование страницы 'О нас'
@staff_member_required
def admin_edit_about(request):
    about = AboutPage.get_content()

    if request.method == 'POST':
        try:
            about.page_title = request.POST.get('page_title', '').strip()
            about.main_heading = request.POST.get('main_heading', '').strip()

            about.address_title = request.POST.get('address_title', '').strip()
            about.address_content = request.POST.get('address_content', '').strip()

            about.director_title = request.POST.get('director_title', '').strip()
            about.director_content = request.POST.get('director_content', '').strip()

            about.teachers_title = request.POST.get('teachers_title', '').strip()
            about.teachers_content = request.POST.get('teachers_content', '').strip()

            about.about_heading = request.POST.get('about_heading', '').strip()
            about.about_paragraph1 = request.POST.get('about_paragraph1', '').strip()
            about.about_paragraph2 = request.POST.get('about_paragraph2', '').strip()

            about.advantages_heading = request.POST.get('advantages_heading', '').strip()

            for i in range(1, 7):
                about.__setattr__(f'adv{i}_icon', request.POST.get(f'adv{i}_icon', '').strip())
                about.__setattr__(f'adv{i}_title', request.POST.get(f'adv{i}_title', '').strip())
                about.__setattr__(f'adv{i}_desc', request.POST.get(f'adv{i}_desc', '').strip())

            about.contacts_heading = request.POST.get('contacts_heading', '').strip()
            about.contact_address = request.POST.get('contact_address', '').strip()
            about.contact_director = request.POST.get('contact_director', '').strip()
            about.contact_phone = request.POST.get('contact_phone', '').strip()
            about.contact_email = request.POST.get('contact_email', '').strip()
            about.contact_schedule = request.POST.get('contact_schedule', '').strip()

            about.save()

            messages.success(request, 'Информация о школе успешно обновлена!')
            return redirect('admin_edit_about')

        except Exception as e:
            messages.error(request, f'Ошибка при сохранении: {str(e)}')

    context = {
        'about': about,
    }
    return render(request, 'admin/edit_about.html', context)

# Управление отзывами
@staff_member_required
def admin_feedbacks(request):
    status_filter = request.GET.get('status', '')

    feedbacks = Feedback.objects.select_related('abiturient', 'course__teacher').all()

    # Фильтрация по статусу
    if status_filter:
        feedbacks = feedbacks.filter(status=status_filter)

    # Сортировка по дате
    feedbacks = feedbacks.order_by('-created_at')

    # Подсчёт статистики
    total_count = Feedback.objects.count()
    pending_count = Feedback.objects.filter(status='pending').count()
    approved_count = Feedback.objects.filter(status='approved').count()
    rejected_count = Feedback.objects.filter(status='rejected').count()

    context = {
        'feedbacks': feedbacks,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'current_status': status_filter,
    }
    return render(request, 'admin/feedbacks.html', context)

# Редактирование отзыва
@staff_member_required
def admin_edit_feedback(request, feedback_id):
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    if request.method == 'POST':
        comment = request.POST.get('comment', '')
        status = request.POST.get('status', feedback.status)

        if len(comment) > 1000:
            messages.error(request, 'Комментарий не должен превышать 1000 символов')
            return redirect('admin_edit_feedback', feedback_id=feedback_id)

        try:
            feedback.comment = comment
            feedback.status = status
            feedback.moderated_at = timezone.now()
            feedback.moderated_by = request.user
            feedback.save()

            messages.success(request, f'Отзыв успешно обновлен!')
            return redirect('admin_feedbacks')

        except Exception as e:
            messages.error(request, f'Ошибка при сохранении: {str(e)}')
            return redirect('admin_edit_feedback', feedback_id=feedback_id)

    return render(request, 'admin/edit_feedback.html', {'feedback': feedback})

# Удаление отзыва
@staff_member_required
def admin_delete_feedback(request, feedback_id):
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    if request.method == 'POST':
        course_id = feedback.course.course_id
        feedback.delete()
        messages.success(request, 'Отзыв успешно удален!')
        return redirect('admin_feedbacks')

    return render(request, 'admin/delete_feedback.html', {'feedback': feedback})

# Одобрение отзыва
@staff_member_required
def admin_approve_feedback(request, feedback_id):
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    feedback.status = 'approved'
    feedback.moderated_at = timezone.now()
    feedback.moderated_by = request.user
    feedback.save()

    messages.success(request, 'Отзыв одобрен!')
    return redirect('admin_feedbacks')

# Отклонение отзыва
@staff_member_required
def admin_reject_feedback(request, feedback_id):
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    feedback.status = 'rejected'
    feedback.moderated_at = timezone.now()
    feedback.moderated_by = request.user
    feedback.save()

    messages.success(request, 'Отзыв отклонен!')
    return redirect('admin_feedbacks')

# Архивация и восстановление
@staff_member_required
def admin_archive(request):
    archived_courses_count = Course.objects.filter(is_activ=False).count()
    archived_teachers_count = Teacher.objects.filter(is_activ=False).count()
    archived_students_count = Abiturient.objects.filter(is_activ=False).count()

    context = {
        'archived_courses_count': archived_courses_count,
        'archived_teachers_count': archived_teachers_count,
        'archived_students_count': archived_students_count,
    }
    return render(request, 'admin/archive.html', context)

# Архивированные курсы
@staff_member_required
def admin_archive_courses(request):
    archived_courses = Course.objects.filter(is_activ=False).select_related('teacher')
    return render(request, 'admin/archive_courses.html', {'archived_courses': archived_courses})

# Архивированные преподаватели
@staff_member_required
def admin_archive_teachers(request):
    archived_teachers = Teacher.objects.filter(is_activ=False).select_related('user')
    return render(request, 'admin/archive_teachers.html', {'archived_teachers': archived_teachers})

# Архивированные абитуриенты
@staff_member_required
def admin_archive_students(request):
    archived_students = Abiturient.objects.filter(is_activ=False).select_related('user', 'school', 'parent')
    return render(request, 'admin/archive_students.html', {'archived_students': archived_students})

# Архивация/восстановление курса
@staff_member_required
def admin_toggle_course_archive(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)

    if request.method == 'POST':
        course.is_activ = not course.is_activ
        course.save()

        status = "архивирован" if not course.is_activ else "восстановлен"
        messages.success(request, f'Курс "{course.name}" {status}!')
        return redirect('admin_courses')

    return render(request, 'admin/confirm_archive.html', {
        'object': course,
        'object_type': 'course',
        'action': 'архивировать' if course.is_activ else 'восстановить'
    })

# Архивация преподавателя + все его курсы
@staff_member_required
def admin_toggle_teacher_archive(request, teacher_id):
    teacher = get_object_or_404(Teacher, teacher_id=teacher_id)

    if request.method == 'POST':
        should_archive = teacher.is_activ

        teacher.is_activ = not should_archive
        teacher.save()

        # Если архивируем препода - архивируем все его курсы
        if should_archive:
            Course.objects.filter(teacher=teacher).update(is_activ=False)
            messages.success(request, f'Преподаватель "{teacher.last_name} {teacher.first_name}" и все его курсы архивированы!')
        else:
            messages.success(request, f'Преподаватель "{teacher.last_name} {teacher.first_name}" восстановлен!')

        return redirect('admin_teachers')

    return render(request, 'admin/confirm_archive.html', {
        'object': teacher,
        'object_type': 'teacher',
        'action': 'архивировать' if teacher.is_activ else 'восстановить'
    })

# Архивация абитуриента
@staff_member_required
def admin_toggle_student_archive(request, abitur_id):
    abiturient = get_object_or_404(Abiturient, abitur_id=abitur_id)

    if request.method == 'POST':
        abiturient.is_activ = not abiturient.is_activ
        abiturient.save()

        status = "архивирован" if not abiturient.is_activ else "восстановлен"
        messages.success(request, f'Абитуриент "{abiturient.last_name} {abiturient.first_name}" {status}!')
        return redirect('admin_students')

    return render(request, 'admin/confirm_archive.html', {
        'object': abiturient,
        'object_type': 'student',
        'action': 'архивировать' if abiturient.is_activ else 'восстановить'
    })

# Восстановление курса
@staff_member_required
def admin_restore_course(request, course_id):
    course = get_object_or_404(Course, course_id=course_id)

    # Eсли преподаватель не активен - нельзя восстановить курс
    if not course.teacher.is_activ:
        messages.error(request, f'Нельзя восстановить курс: преподаватель "{course.teacher.last_name} {course.teacher.first_name}" архивирован! Сначала восстановите преподавателя.')
        return redirect('admin_archive_courses')

    if request.method == 'POST':
        course.is_activ = True
        course.save()

        messages.success(request, f'Курс "{course.name}" восстановлен!')
        return redirect('admin_archive_courses')

    return render(request, 'admin/confirm_restore.html', {
        'object': course,
        'object_type': 'course'
    })

# Восстановление преподавателя
@staff_member_required
def admin_restore_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, teacher_id=teacher_id)

    if request.method == 'POST':
        teacher.is_activ = True
        teacher.save()

        messages.success(request, f'Преподаватель "{teacher.last_name} {teacher.first_name}" восстановлен!')
        return redirect('admin_archive_teachers')

    return render(request, 'admin/confirm_restore.html', {
        'object': teacher,
        'object_type': 'teacher'
    })

# Восстановление абитуриента
@staff_member_required
def admin_restore_student(request, abitur_id):
    abiturient = get_object_or_404(Abiturient, abitur_id=abitur_id)

    if request.method == 'POST':
        abiturient.is_activ = True
        abiturient.save()

        messages.success(request, f'Абитуриент "{abiturient.last_name} {abiturient.first_name}" восстановлен!')
        return redirect('admin_archive_students')

    return render(request, 'admin/confirm_restore.html', {
        'object': abiturient,
        'object_type': 'student'
    })