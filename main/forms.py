import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, EmailValidator
from .models import Abiturient, Parent, RecordCourse, Feedback, Course, School
from django.core.validators import EmailValidator, RegexValidator
from django.core.exceptions import ValidationError

class RegisterForm(UserCreationForm):
    # Данные абитуриента
    username = forms.CharField(
        max_length=150,
        required=True,
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Логин',
            'minlength': 3,
            'maxlength': 150,
        })
    )

    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
        })
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        label='Имя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя',
        })
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        label='Фамилия',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия',
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        label='Телефон абитуриента',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 999-99-99',
            'maxlength': 20
        })
    )
    class_name = forms.CharField(
        max_length=20,
        required=True,
        label='Класс',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '9а, 10б, 11в',
            'maxlength': 5
        })
    )
    school_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label='Выберите школу из списка',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'school_choice',
        }),
    )
    add_new_school = forms.BooleanField(
        required=False,
        label='Добавить новую школу (если нет в списке)',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_add_new_school',
            'onchange': 'toggleSchoolFields()',
        }),
    )
    # Поля для новой школы (скрытые по умолчанию)
    new_school_name = forms.CharField(
        max_length=255,
        required=False,
        label='Название новой школы',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'МБОУ СОШ №...',
            'id': 'new_school_name',
        }),
    )
    new_school_address = forms.CharField(
        max_length=255,
        required=False,
        label='Адрес школы',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'г. Город, ул. Улица, д. 1',
            'id': 'new_school_address',
        }),
    )
    new_school_director_last_name = forms.CharField(
        max_length=100,
        required=False,
        label='Фамилия директора',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия',
            'id': 'new_school_director_last_name',
        }),
    )
    new_school_director_first_name = forms.CharField(
        max_length=100,
        required=False,
        label='Имя директора',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя',
            'id': 'new_school_director_first_name',
        }),
    )
    new_school_director_middle_name = forms.CharField(
        max_length=100,
        required=False,
        label='Отчество директора',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Отчество',
            'id': 'new_school_director_middle_name',
        }),
    )

    # Данные родителя
    parent_first_name = forms.CharField(
        max_length=100,
        required=True,
        label='Имя родителя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя родителя',
        })
    )
    parent_last_name = forms.CharField(
        max_length=100,
        required=True,
        label='Фамилия родителя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия родителя',
        })
    )
    parent_phone = forms.CharField(
        max_length=20,
        required=True,
        label='Телефон родителя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 999-99-99',
            'maxlength': 20
        })
    )
    parent_pasport = forms.CharField(
        max_length=20,
        required=True,
        label='Паспорт родителя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '4501 123456',
            'maxlength': 11,
        })
    )
    parent_inn = forms.CharField(
        max_length=12,
        required=True,
        label='ИНН родителя',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12 цифр',
            'maxlength': 12,
        })
    )
    parent_address = forms.CharField(
        max_length=255,
        required=True,
        label='Адрес',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Адрес проживания',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        error_messages = {
            'username': {
                'unique': 'Пользователь с таким логином уже существует',
                'required': 'Логин обязателен',
                'max_length': 'Логин не должен превышать 150 символов'
            },
            'email': {
                'unique': 'Пользователь с таким email уже зарегистрирован',
                'required': 'Email обязателен',
                'invalid': 'Введите корректный email адрес'
            },
            'first_name': {
                'required': 'Имя обязательно',
                'max_length': 'Имя не должно превышать 100 символов'
            },
            'last_name': {
                'required': 'Фамилия обязательна',
                'max_length': 'Фамилия не должна превышать 100 символов'
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Логин',
            'maxlength': 150,
            'minlength': 3
        })
        self.fields['password1'].label = 'Пароль'
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Пароль',
            'minlength': 8,
        })
        self.fields['password2'].label = 'Подтверждение пароля'
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Подтверждение пароля',
            'minlength': 8
        })

        # Заполняем выбор школ
        schools = School.objects.all()
        school_choices = [('', '-- Выберите школу --')]
        for school in schools:
            school_choices.append((school.school_id, f'{school.name} ({school.address})'))
        self.fields['school_choice'].choices = school_choices

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and len(username) < 3:
            raise forms.ValidationError('Логин должен содержать минимум 3 символа')
        if username and not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise forms.ValidationError('Логин может содержать только буквы, цифры и _')
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password and len(password) < 8:
            raise forms.ValidationError('Пароль должен содержать минимум 8 символов')
        if password and not re.search(r'[A-Za-z]', password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну букву')
        if password and not re.search(r'\d', password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну цифру')
        return password

    def clean_first_name(self):
        """Имя - только буквы"""
        first_name = self.cleaned_data.get('first_name')
        if first_name and not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', first_name):
            raise ValidationError('Имя должно содержать только буквы, пробелы и дефис')
        return first_name.strip().title()

    def clean_last_name(self):
        """Фамилия - только буквы"""
        last_name = self.cleaned_data.get('last_name')
        if last_name and not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', last_name):
            raise ValidationError('Фамилия должна содержать только буквы, пробелы и дефис')
        return last_name.strip().title()

    def clean_email(self):
        """Email - проверка на @ и точку с доменом"""
        email = self.cleaned_data.get('email')
        if email:
            if '@' not in email:
                raise ValidationError('Email должен содержать символ @')
            domain_part = email.split('@')[-1]
            if '.' not in domain_part:
                raise ValidationError('Email должен содержать точку и домен (например, @example.com)')
            if len(domain_part.split('.')[-1]) < 2:
                raise ValidationError('Некорректный домен email')
        return email.lower().strip()

    def clean_phone(self):
        """Телефон - ровно 11 цифр"""
        phone = self.cleaned_data.get('phone')
        if phone:
            digits = re.sub(r'\D', '', phone)
            if len(digits) != 11:
                raise ValidationError(f'Телефон должен содержать ровно 11 цифр (сейчас: {len(digits)})')
            if not digits.startswith(('7', '8')):
                raise ValidationError('Телефон должен начинаться с 7 или 8')
            return digits
        return phone

    def clean_class_name(self):
        """Класс - не больше 11"""
        class_name = self.cleaned_data.get('class_name')
        if class_name:
            class_match = re.match(r'^([1-9]|10|11)([а-яА-Я]?)$', class_name.strip())
            if not class_match:
                raise ValidationError('Введите класс в формате 9а, 10б, 11в')
            grade = int(class_match.group(1))
            if grade > 11:
                raise ValidationError('Класс должен быть не больше 11')
        return class_name.strip()

    def clean_parent_first_name(self):
        """Имя родителя - только буквы"""
        first_name = self.cleaned_data.get('parent_first_name')
        if first_name and not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', first_name):
            raise ValidationError('Имя родителя должно содержать только буквы, пробелы и дефис')
        return first_name.strip().title()

    def clean_parent_last_name(self):
        """Фамилия родителя - только буквы"""
        last_name = self.cleaned_data.get('parent_last_name')
        if last_name and not re.match(r'^[а-яА-ЯёЁa-zA-Z\s-]+$', last_name):
            raise ValidationError('Фамилия родителя должна содержать только буквы, пробелы и дефис')
        return last_name.strip().title()

    def clean_parent_phone(self):
        """Телефон родителя - ровно 11 цифр"""
        phone = self.cleaned_data.get('parent_phone')
        if phone:
            digits = re.sub(r'\D', '', phone)
            if len(digits) != 11:
                raise ValidationError(f'Телефон должен содержать ровно 11 цифр (сейчас: {len(digits)})')
            if not digits.startswith(('7', '8')):
                raise ValidationError('Телефон должен начинаться с 7 или 8')
            return digits
        return phone

    def clean_parent_pasport(self):
        """Паспорт - 10 цифр"""
        pasport = self.cleaned_data.get('parent_pasport')
        if pasport:
            digits = re.sub(r'\s', '', pasport)
            if len(digits) != 10:
                raise ValidationError('Паспорт должен содержать 10 цифр (4 цифры серия + 6 цифр номер)')
            return digits
        return pasport

    def clean_parent_inn(self):
        """ИНН - 12 цифр для физ.лица"""
        inn = self.cleaned_data.get('parent_inn')
        if inn:
            digits = re.sub(r'\D', '', inn)
            if len(digits) == 10:
                raise ValidationError('ИНН физического лица должен содержать 12 цифр')
            if len(digits) != 12:
                raise ValidationError('ИНН должен содержать 12 цифр')
            return digits
        return inn

    def clean(self):
        cleaned_data = super().clean()

        # Валидация школы
        add_new_school = cleaned_data.get('add_new_school')

        if add_new_school:
            if not cleaned_data.get('new_school_name'):
                self.add_error('new_school_name', 'Укажите название школы')
            if not cleaned_data.get('new_school_address'):
                self.add_error('new_school_address', 'Укажите адрес школы')
            if not cleaned_data.get('new_school_director_last_name'):
                self.add_error('new_school_director_last_name', 'Укажите фамилию директора')
            if not cleaned_data.get('new_school_director_first_name'):
                self.add_error('new_school_director_first_name', 'Укажите имя директора')
        else:
            if not cleaned_data.get('school_choice'):
                self.add_error('school_choice', 'Выберите школу из списка или добавьте новую')

        return cleaned_data


# Форма входа
class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Логин',
            'required': 'required',
            'autofocus': 'autofocus'
        })
        self.fields['password'].label = 'Пароль'
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Пароль',
            'required': 'required'
        })

    error_messages = {
        'invalid_login': 'Неверный логин или пароль',
        'inactive': 'Этот аккаунт не активен',
    }


# Форма записи на курс
class RecordCourseForm(forms.ModelForm):
    class Meta:
        model = RecordCourse
        fields = []


# Форма отзыва
class FeedbackForm(forms.ModelForm):
    rating = forms.IntegerField(
        label='Оценка',
        validators=[
            MinValueValidator(1, message='Минимальная оценка: 1'),
            MaxValueValidator(5, message='Максимальная оценка: 5')
        ],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 5,
            'step': 1,
            'required': 'required'
        })
    )
    comment = forms.CharField(
        label='Комментарий',
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Ваш отзыв...',
            'maxlength': 1000
        })
    )

    class Meta:
        model = Feedback
        fields = ['rating', 'comment']


# Форма редактирования профиля пользователя
class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя',
                'pattern': r'^[а-яА-Яa-zA-Z]{2,50}$',
                'maxlength': 100
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Фамилия',
                'pattern': r'^[а-яА-Яa-zA-Z]{2,50}$',
                'maxlength': 100
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email',
                'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'maxlength': 254
            }),
        }
        error_messages = {
            'email': {
                'unique': 'Пользователь с таким email уже зарегистрирован',
                'invalid': 'Введите корректный email адрес'
            }
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise forms.ValidationError('Введите корректный email адрес')
        return email


# Форма редактирования данных абитуриента
class AbiturientForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=20,
        required=True,
        label='Телефон',
        validators=[
            RegexValidator(
                regex=r'^[\+]?[0-9\s\-\(\)]{10,20}$',
                message='Введите телефон в формате +7 (___) ___-__-__'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (___) ___-__-__',
            'pattern': r'^[\+]?[0-9\s\-\(\)]{10,20}$',
            'maxlength': 20
        })
    )
    class_name = forms.CharField(
        max_length=20,
        required=True,
        label='Класс',
        validators=[
            RegexValidator(
                regex=r'^[1-4]?[0-9][а-яА-Я]?$',
                message='Введите класс в формате 9а, 10б, 11в'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Класс (например, 9а)',
            'pattern': r'^[1-4]?[0-9][а-яА-Я]?$',
            'maxlength': 5
        })
    )

    photo = forms.ImageField(
        required=False,
        label='Фотография',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = Abiturient
        fields = ['phone', 'class_name', 'photo']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (___) ___-__-__'
            }),
            'class_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Класс (например, 9а)'
            }),
        }

    def clean_class_name(self):
        class_name = self.cleaned_data.get('class_name')
        if class_name:
            class_match = re.match(r'^([1-4]?[0-9])([а-яА-Я]?)$', class_name)
            if not class_match:
                raise forms.ValidationError('Введите класс в формате 9а, 10б, 11в')
            else:
                grade = int(class_match.group(1))
                if grade < 1 or grade > 11:
                    raise forms.ValidationError('Класс должен быть от 1 до 11')
        return class_name

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'raspisanie': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_activ': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
        }