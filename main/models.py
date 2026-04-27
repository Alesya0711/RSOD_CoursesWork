from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date

# Модель Пользователи
class Users(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('teacher', 'Преподаватель'),
        ('student', 'Абитуриент'),
    ]

    user_id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    password = models.CharField(max_length=255)
    login = models.CharField(max_length=100, unique=True)
    is_activ = models.BooleanField(default=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.login


# Модель Школа
class School(models.Model):
    school_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)

    director_last_name = models.CharField(max_length=100, verbose_name='Фамилия директора')
    director_first_name = models.CharField(max_length=100, verbose_name='Имя директора')
    director_middle_name = models.CharField(max_length=100, verbose_name='Отчество директора')

    class Meta:
        db_table = 'school'
        constraints = [
            models.UniqueConstraint(fields=['name', 'address'], name='unique_school_name_address')
        ]

    def __str__(self):
        return self.name

    @property
    def director_full_name(self):
            return f"{self.director_last_name} {self.director_first_name} {self.director_middle_name}"

    def clean(self):
        if not self.name or not self.name.strip():
            raise ValidationError('Название школы обязательно')
        if not self.address or not self.address.strip():
            raise ValidationError('Адрес школы обязателен')
        if not self.director_last_name or not self.director_last_name.strip():
            raise ValidationError('Фамилия директора обязательна')
        if not self.director_first_name or not self.director_first_name.strip():
            raise ValidationError('Имя директора обязательно')
        if not self.director_middle_name or not self.director_middle_name.strip():
            raise ValidationError('Отчество директора обязательно')

# Модель Родитель
class Parent(models.Model):
    parent_id = models.AutoField(primary_key=True)
    first_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z]{2,50}$',
                message='Имя должно содержать от 2 до 50 букв'
            )
        ]
    )
    last_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z]{2,50}$',
                message='Фамилия должна содержать от 2 до 50 букв'
            )
        ]
    )
    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[\+]?[0-9\s\-\(\)]{10,20}$',
                message='Введите телефон в формате +7 (___) ___-__-__'
            )
        ]
    )
    pasport = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\d{4}\s?\d{6}$',
                message='Паспорт в формате: 4501 123456 (4 цифры + 6 цифр)'
            )
        ]
    )
    inn = models.CharField(
        max_length=12,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$|^\d{12}$',
                message='ИНН должен содержать 10 или 12 цифр'
            )
        ]
    )
    address = models.CharField(max_length=255)

    class Meta:
        db_table = 'parent'
        constraints = [
            models.UniqueConstraint(fields=['pasport', 'inn'], name='unique_parent_document')
        ]

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def clean(self):
        if not self.first_name or not self.first_name.strip():
            raise ValidationError('Имя родителя обязательно')
        if not self.last_name or not self.last_name.strip():
            raise ValidationError('Фамилия родителя обязательна')
        if not self.phone or not self.phone.strip():
            raise ValidationError('Телефон родителя обязателен')
        if not self.pasport or not self.pasport.strip():
            raise ValidationError('Паспорт обязателен')
        if not self.inn or not self.inn.strip():
            raise ValidationError('ИНН обязателен')


# Модель Преподаватель
class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    first_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z]{2,50}$',
                message='Имя должно содержать от 2 до 50 букв'
            )
        ]
    )
    last_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z]{2,50}$',
                message='Фамилия должна содержать от 2 до 50 букв'
            )
        ]
    )
    description = models.TextField(blank=True, null=True)
    email = models.EmailField(
        max_length=255,
        validators=[EmailValidator(message='Введите корректный email адрес')]
    )

    photo_url = models.CharField(max_length=500, blank=True, null=True)
    photo = models.ImageField(
        upload_to='teachers/photos/',
        blank=True,
        null=True,
        help_text='Фотография преподавателя (необязательно)'
    )
    is_activ = models.BooleanField(default=True)

    class Meta:
        db_table = 'teachers'

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def clean(self):
        if not self.first_name or not self.first_name.strip():
            raise ValidationError('Имя преподавателя обязательно')
        if not self.last_name or not self.last_name.strip():
            raise ValidationError('Фамилия преподавателя обязательна')
        if not self.email:
            raise ValidationError('Email преподавателя обязателен')


# Модель Абитуриент
class Abiturient(models.Model):
    abitur_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    first_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z]{2,50}$',
                message='Имя должно содержать от 2 до 50 букв'
            )
        ]
    )
    last_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z]{2,50}$',
                message='Фамилия должна содержать от 2 до 50 букв'
            )
        ]
    )
    email = models.EmailField(
        max_length=255,
        validators=[EmailValidator(message='Введите корректный email адрес')]
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[\+]?[0-9\s\-\(\)]{10,20}$',
                message='Введите телефон в формате +7 (___) ___-__-__'
            )
        ]
    )
    class_name = models.CharField(
        max_length=20,
        db_column='class',
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[1-4]?[0-9][а-яА-Я]?$',
                message='Введите класс в формате 9а, 10б, 11в'
            )
        ]
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        db_column='school_id',
        null=True,
        blank=True
    )
    parent = models.ForeignKey(
        Parent,
        on_delete=models.SET_NULL,
        db_column='parent_id',
        null=True,
        blank=True
    )

    photo = models.ImageField(
        upload_to='students/photos/',
        blank=True,
        null=True,
        help_text='Фотография абитуриента (необязательно)'
    )
    is_activ = models.BooleanField(default=True)

    class Meta:
        db_table = 'abiturients'

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def clean(self):
        if not self.first_name or not self.first_name.strip():
            raise ValidationError('Имя абитуриента обязательно')
        if not self.last_name or not self.last_name.strip():
            raise ValidationError('Фамилия абитуриента обязательна')
        if not self.email:
            raise ValidationError('Email абитуриента обязателен')


# Модель Курсы
class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, db_column='teacher_id')
    level = models.CharField(max_length=50)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    start_date = models.DateField()
    end_date = models.DateField()
    raspisanie = models.CharField(max_length=255, blank=True, null=True)
    is_activ = models.BooleanField(default=True)

    max_students = models.PositiveIntegerField(
        default=15,
        help_text='Максимальное количество студентов на курсе'
    )

    photo_url = models.CharField(max_length=500, blank=True, null=True)
    photo = models.ImageField(
        upload_to='courses/photos/',
        blank=True,
        null=True,
        help_text='Фотография курса (необязательно)'
    )

    class Meta:
        db_table = 'courses'

    def __str__(self):
        return self.name

    def get_enrolled_count(self):
        return RecordCourse.objects.filter(
            course=self,
            status='Подтверждена'
        ).count()

    def is_full(self):
        return self.get_enrolled_count() >= self.max_students

    def get_available_spots(self):
        return max(0, self.max_students - self.get_enrolled_count())

    def is_started(self):
        return self.start_date < date.today()

    def is_ended(self):
        return self.end_date < date.today()

    def is_enrollment_open(self):
        return not self.is_started() and not self.is_ended() and self.is_activ and not self.is_full()

    def clean(self):
        if not self.name or not self.name.strip():
            raise ValidationError('Название курса обязательно')
        if not self.description or not self.description.strip():
            raise ValidationError('Описание курса обязательно')
        if not self.teacher_id:
            raise ValidationError('Преподаватель обязателен')
        if not self.level or not self.level.strip():
            raise ValidationError('Уровень курса обязателен')
        if self.price is not None and self.price <= 0:
            raise ValidationError('Цена должна быть положительным числом')
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError('Дата начала не может быть позже даты окончания')
        if self.max_students and self.max_students < 1:
            raise ValidationError('Максимальное количество студентов должно быть не менее 1')


# Модель Записи на курсы
class RecordCourse(models.Model):
    STATUS_CHOICES = [
        ('В обработке', 'В обработке'),
        ('Подтверждена', 'Подтверждена'),
        ('Отклонена', 'Отклонена'),
        ('Завершена', 'Завершена'),
    ]

    record_id = models.AutoField(primary_key=True)
    abiturient = models.ForeignKey(Abiturient, on_delete=models.CASCADE, db_column='abitur_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, db_column='course_id')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='В обработке'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = 'record_course'
        constraints = [
            models.UniqueConstraint(
                fields=['abiturient', 'course'],
                name='unique_enrollment_per_course'
            )
        ]

    def __str__(self):
        return f"{self.abiturient} - {self.course}"

    def clean(self):
        if not self.abiturient_id:
            raise ValidationError('Абитуриент обязателен')
        if not self.course_id:
            raise ValidationError('Курс обязателен')
        if self.status and self.status not in [choice[0] for choice in self.STATUS_CHOICES]:
            raise ValidationError('Неверный статус записи')


# Модель Отзывы
class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    abiturient = models.ForeignKey(Abiturient, on_delete=models.CASCADE, db_column='abitur_id')
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        db_column='course_id',
        related_name='feedbacks'
    )
    rating = models.SmallIntegerField(
        validators=[
            MinValueValidator(1, message='Минимальная оценка: 1'),
            MaxValueValidator(5, message='Максимальная оценка: 5')
        ]
    )
    comment = models.TextField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    MODERATION_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонён'),
    ]
    status = models.CharField(
        max_length=20,
        choices=MODERATION_CHOICES,
        default='pending'
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_feedbacks'
    )

    class Meta:
        db_table = 'feedbacks'
        constraints = [
            models.UniqueConstraint(
                fields=['abiturient', 'course'],
                name='unique_feedback_per_course'
            )
        ]

    def __str__(self):
        return f"Отзыв {self.abiturient} на курс {self.course}"

    def clean(self):
        if self.rating is not None and (self.rating < 1 or self.rating > 5):
            raise ValidationError('Оценка должна быть от 1 до 5')
        if self.comment and len(self.comment) > 1000:
            raise ValidationError('Комментарий не должен превышать 1000 символов')

# Модель страницы 'О нас'
class AboutPage(models.Model):
    page_title = models.CharField(max_length=255, default="🏫 О нашей школе", verbose_name="Заголовок страницы")
    main_heading = models.CharField(max_length=255, default="Образовательная школа подготовки к ОГЭ и ЕГЭ",  verbose_name="Главный заголовок")

    address_title = models.CharField(max_length=100, default="📍 Адрес", verbose_name="Заголовок: Адрес")
    address_content = models.TextField(default="г. Муром\nул. Московская, д. 24", verbose_name="Содержимое: Адрес")

    director_title = models.CharField(max_length=100, default="👤 Директор", verbose_name="Заголовок: Директор")
    director_content = models.TextField(default="Писарева\nАлеся Дмитриевна", verbose_name="Содержимое: Директор")

    teachers_title = models.CharField(max_length=100, default="👨‍🏫 Преподаватели", verbose_name="Заголовок: Преподаватели")
    teachers_content = models.TextField(default="Большой штат\nквалифицированных специалистов", verbose_name="Содержимое: Преподаватели")

    about_heading = models.CharField(max_length=255, default="📚 О нашей деятельности", verbose_name="Заголовок: О деятельности")
    about_paragraph1 = models.TextField(default="Наша образовательная школа специализируется на подготовке учащихся к успешной сдаче ОГЭ и ЕГЭ...", verbose_name="Первый абзац")
    about_paragraph2 = models.TextField(default="Благодаря современному подходу к обучению...", verbose_name="Второй абзац")

    advantages_heading = models.CharField(max_length=255, default="🌟 Наши преимущества", verbose_name="Заголовок: Преимущества")
    advantages = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Список преимуществ",
        help_text='Формат: [{"title": "🎯 Заголовок", "desc": "Описание"}]'
    )

    contacts_heading = models.CharField(max_length=255, default="📞 Контактная информация", verbose_name="Заголовок: Контакты")
    contact_address = models.CharField(max_length=255, default="г. Муром, ул. Московская, д. 24", verbose_name="Адрес")
    contact_director = models.CharField(max_length=255, default="Писарева Алеся Дмитриевна", verbose_name="Директор")
    contact_phone = models.CharField(max_length=50, default="+7 (999) 999-99-99", verbose_name="Телефон")
    contact_email = models.EmailField(default="director.shcol@gmail.com", verbose_name="Email")
    contact_schedule = models.CharField(max_length=255, default="Пн-Пт: 9:00 - 19:00, Сб: 10:00 - 16:00", verbose_name="Режим работы")

    class Meta:
        db_table = 'about_page'
        verbose_name = 'Страница "О нас"'
        verbose_name_plural = 'Страница "О нас"'

    def __str__(self):
        return 'Настройки страницы "О нас"'

    @classmethod
    def get_content(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj