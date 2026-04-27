from django.core.mail import send_mail
from django.conf import settings

# Отправляем приветственное письмо при регистрации нового пользователя
def send_welcome_email(user):
    subject = 'Добро пожаловать на образовательную платформу!'
    message = f'''
    Здравствуйте, {user.first_name}!

    Спасибо за регистрацию на нашей образовательной платформе.

    Теперь вы можете:
    - Просматривать доступные курсы
    - Записываться на курсы
    - Оставлять отзывы
    - Отслеживать статус заявок в личном кабинете

    Если у вас возникли вопросы, свяжитесь с нами:
    Телефон: +7 (999) 999-99-99
    Email: director.shcol@gmail.com

    С уважением,
    Команда образовательной школы "Лесенка"
    '''

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

# Отправляем уведомление о записи на курс
def send_enrollment_notification(abiturient, course):
    subject = f'Заявка на курс "{course.name}"'
    message = f'''
    Здравствуйте, {abiturient.first_name}!

    Вы успешно подали заявку на курс "{course.name}".

    Информация о курсе:
    Преподаватель: {course.teacher.last_name} {course.teacher.first_name}
    Дата начала: {course.start_date}
    Дата окончания: {course.end_date}
    Стоимость: {course.price} руб.

    Статус заявки: В обработке

    Мы рассмотрим вашу заявку в ближайшее время.
    Вы можете отслеживать статус заявки в личном кабинете.

    Если у вас возникли вопросы, свяжитесь с нами:
    Телефон: +7 (999) 999-99-99
    Email: director.shcol@gmail.com

    С уважением,
    Команда образовательной школы "Лесенка"
    '''

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[abiturient.email],
        fail_silently=False,
    )

# Отправляем уведомление об изменении статуса заявки на курс
def send_status_change_notification(abiturient, course, old_status, new_status):
    subject = f'Изменение статуса заявки на курс "{course.name}"'

    # Разные сообщения для разных статусов
    status_messages = {
        'Подтверждена': f'''
    Здравствуйте, {abiturient.first_name}!

    Ваша заявка на курс "{course.name}" была ПОДТВЕРЖДЕНА!

    Информация о курсе:
    Преподаватель: {course.teacher.last_name} {course.teacher.first_name}
    Дата начала: {course.start_date}
    Дата окончания: {course.end_date}
    Стоимость: {course.price} руб.

    Следующие шаги:
    1. Оплатите обучение до начала курса
    2. Свяжитесь с преподавателем для уточнения деталей
    3. Подготовьте необходимые материалы

    Контакты:
    Телефон: +7 (999) 999-99-99
    Email: director.shcol@gmail.com

    Ждём вас на занятиях!

    С уважением,
    Команда образовательной школы "Лесенка"
    ''',

        'Отклонена': f'''
    Здравствуйте, {abiturient.first_name}!

    К сожалению, ваша заявка на курс "{course.name}" была ОТКЛОНЕНА.

    Информация о курсе:
    Преподаватель: {course.teacher.last_name} {course.teacher.first_name}
    Дата начала: {course.start_date}
    Дата окончания: {course.end_date}
    
    Что вы можете сделать:
    1. Подать заявку на другой курс
    2. Связаться с администрацией для уточнения деталей
    3. Дождаться следующего потока

    Контакты:
    Телефон: +7 (999) 999-99-99
    Email: director.shcol@gmail.com

    С уважением,
    Команда образовательной школы "Лесенка"
    ''',

        'Завершена': f'''
    Здравствуйте, {abiturient.first_name}!

    Ваш курс "{course.name}" ЗАВЕРШЕН!

    Информация о курсе:
    Преподаватель: {course.teacher.last_name} {course.teacher.first_name}
    Дата начала: {course.start_date}
    Дата окончания: {course.end_date}

    Что дальше:
    1. Оставьте отзыв о курсе (это поможет другим абитуриентам)
    2. Запишитесь на следующий курс обучения

    Контакты:
    Телефон: +7 (999) 999-99-99
    Email: director.shcol@gmail.com

    Благодарим вас за обучение!

    С уважением,
    Команда образовательной школы "Лесенка"
    ''',

        'В обработке': f'''
    Здравствуйте, {abiturient.first_name}!

    Статус вашей заявки на курс "{course.name}" изменён на "В обработке".

    Информация о курсе:
    Преподаватель: {course.teacher.last_name} {course.teacher.first_name}
    Дата начала: {course.start_date}
    Дата окончания: {course.end_date}

    Мы рассматриваем вашу заявку и свяжемся с вами в ближайшее время.

    Контакты:
    Телефон: +7 (999) 999-99-99
    Email: director.shcol@gmail.com

    С уважением,
    Команда образовательной школы "Лесенка"
    '''
    }

    message = status_messages.get(new_status, f'''
    Здравствуйте, {abiturient.first_name}!

    Статус вашей заявки на курс "{course.name}" изменён.

    Информация о курсе:
    Преподаватель: {course.teacher.last_name} {course.teacher.first_name}
    Дата начала: {course.start_date}
    Дата окончания: {course.end_date}

    Изменения:
    Старый статус: {old_status}
    Новый статус: {new_status}

    Контакты:
    Телефон: +7 (999) 999-99-99
    Email: director.shcol@gmail.com

    С уважением,
    Команда образовательной школы "Лесенка"
    ''')

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[abiturient.email],
        fail_silently=False,
    )