# screens.py
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineListItem, TwoLineListItem
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
from kivy.properties import ObjectProperty, StringProperty
from kivy.metrics import dp
from kivy.clock import Clock

class DialogMixin:
    def show_error_dialog(self, text):
        """Показать диалог ошибки"""
        def _show_dialog(dt):
            dialog = MDDialog(
                title="Ошибка",
                text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
            )
            dialog.open()
        Clock.schedule_once(_show_dialog, 0)

    def show_success_dialog(self, text):
        """Показать диалог успеха"""
        def _show_dialog(dt):
            dialog = MDDialog(
                title="Успех",
                text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())]
            )
            dialog.open()
        Clock.schedule_once(_show_dialog, 0)

    def show_notification_snackbar(self, text):
        """Показать уведомление"""
        def _show_snackbar(dt):
            Snackbar(text=text, duration=3).open()
        Clock.schedule_once(_show_snackbar, 0)

class LoginScreen(Screen, DialogMixin):
    def on_pre_enter(self):
        self.username = self.ids.username_field
        self.password = self.ids.password_field

    def try_login(self):
        """Запуск входа"""
        username = self.username.text.strip()
        password = self.password.text.strip()
        
        if not username or not password:
            self.show_error_dialog("Заполните все поля")
            return

        app = MDApp.get_running_app()
        app.login_user(username, password)

    def show_register_dialog(self):
        """Диалог регистрации"""
        content = MDBoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None, height=dp(300))
        
        username_field = MDTextField(hint_text="Логин")
        email_field = MDTextField(hint_text="Email")
        first_name_field = MDTextField(hint_text="Имя")
        last_name_field = MDTextField(hint_text="Фамилия")
        password_field = MDTextField(hint_text="Пароль", password=True)
        confirm_password_field = MDTextField(hint_text="Повторите пароль", password=True)
        
        content.add_widget(username_field)
        content.add_widget(email_field)
        content.add_widget(first_name_field)
        content.add_widget(last_name_field)
        content.add_widget(password_field)
        content.add_widget(confirm_password_field)

        dialog = MDDialog(
            title="Регистрация",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda x: dialog.dismiss()),
                MDFlatButton(text="Зарегистрироваться",
                    on_release=lambda x: self.process_registration(
                        username_field.text, email_field.text,
                        first_name_field.text, last_name_field.text,
                        password_field.text, confirm_password_field.text, dialog))
            ]
        )
        dialog.open()

    def process_registration(self, username, email, first_name, last_name, password, confirm_password, dialog):
        """Обработка регистрации"""
        if not all([username, email, first_name, last_name, password, confirm_password]):
            self.show_error_dialog("Заполните все поля")
            return
        
        if password != confirm_password:
            self.show_error_dialog("Пароли не совпадают")
            return

        dialog.dismiss()
        app = MDApp.get_running_app()
        app.register_user(username, email, password, first_name, last_name)

class MainScreen(Screen, DialogMixin):
    def on_enter(self):
        self.load_courses()
        self.load_tests()

    def load_courses(self):
        """Загрузка курсов"""
        app = MDApp.get_running_app()
        
        async def async_load_courses():
            try:
                courses = await app.api_client.get_courses()
                return courses
            except Exception as e:
                return []

        def handle_courses_result(courses):
            self._update_courses_ui(courses or [])

        app.run_async_task(async_load_courses(), handle_courses_result)

    def _update_courses_ui(self, courses):
        """Обновление UI со списком курсов"""
        if not hasattr(self.ids, 'courses_list'):
            return
            
        self.ids.courses_list.clear_widgets()
        
        for course in courses:
            card = MDCard(
                size_hint_y=None,
                height=dp(120),
                elevation=3,
                padding=dp(8),
                spacing=dp(8),
                on_release=lambda x, c=course: self.go_to_course(c)
            )
            
            card_content = MDBoxLayout(orientation="vertical")
            
            title_label = MDLabel(
                text=course['title'], 
                font_style="H6", 
                size_hint_y=None, 
                height=dp(30)
            )
            
            desc_label = MDLabel(
                text=course['description'][:100] + "...",
                size_hint_y=None, 
                height=dp(40)
            )
            
            status_text = "Подписан" if course.get('is_subscribed') else "Доступен"
            progress_text = f"Прогресс: {course.get('progress_percentage', 0):.1f}%"
            status_label = MDLabel(
                text=f"{status_text} • {progress_text}",
                size_hint_y=None, 
                height=dp(20)
            )
            
            card_content.add_widget(title_label)
            card_content.add_widget(desc_label)
            card_content.add_widget(status_label)
            card.add_widget(card_content)
            
            self.ids.courses_list.add_widget(card)

    def load_tests(self):
        """Загрузка тестов"""
        app = MDApp.get_running_app()
        
        async def async_load_tests():
            try:
                tests = await app.api_client.get_control_tests()
                return tests
            except Exception as e:
                return []

        def handle_tests_result(tests):
            self._update_tests_ui(tests or [])

        app.run_async_task(async_load_tests(), handle_tests_result)

    def _update_tests_ui(self, tests):
        """Обновление UI со списком тестов"""
        if not hasattr(self.ids, 'tests_list'):
            return
            
        self.ids.tests_list.clear_widgets()
        
        for test in tests:
            status = "Пройден" if test.get('is_completed') else "Доступен"
            result_text = f" ({test['result']} баллов)" if test.get('result') is not None else ""

            item = TwoLineListItem(
                text=test['title'],
                secondary_text=f"Статус: {status}{result_text}",
                on_release=lambda x, t=test: self.go_to_control_test(t)
            )
            self.ids.tests_list.add_widget(item)

    def go_to_course(self, course):
        """Переход к курсу"""
        self.manager.current_course = course
        self.manager.current = "course_details"

    def go_to_control_test(self, test):
        """Переход к контрольному тесту"""
        self.manager.current_test = test
        self.manager.current = "control_test_screen"

    def logout(self):
        """Выход из системы"""
        app = MDApp.get_running_app()
        app.logout()

class CourseDetailsScreen(Screen, DialogMixin):
    def on_pre_enter(self):
        course = self.manager.current_course
        if course:
            self.ids.course_title_label.text = course['title']
            self.ids.course_description_label.text = course['description']
            self.load_chapters()

    def load_chapters(self):
        """Загрузка глав курса"""
        course = self.manager.current_course
        if not course:
            return
        
        app = MDApp.get_running_app()
        
        async def async_load_chapters():
            try:
                chapters = await app.api_client.get_chapters(course['id'])
                return chapters
            except Exception as e:
                return []

        def handle_chapters_result(chapters):
            self._update_chapters_ui(chapters or [])

        app.run_async_task(async_load_chapters(), handle_chapters_result)

    def _update_chapters_ui(self, chapters):
        """Обновление UI со списком глав"""
        if not hasattr(self.ids, 'chapters_list'):
            return
            
        self.ids.chapters_list.clear_widgets()
        
        for chapter in chapters:
            status = "✓" if chapter.get('is_completed') else "○"
            test_indicator = " 📝" if chapter.get('has_test') else ""
            
            item = TwoLineListItem(
                text=f"{status} {chapter['title']}{test_indicator}",
                secondary_text="Завершено" if chapter.get('is_completed') else "Не пройдено",
                on_release=lambda x, ch=chapter: self.go_to_chapter(ch)
            )
            self.ids.chapters_list.add_widget(item)

    def go_to_chapter(self, chapter):
        """Переход к главе"""
        self.manager.current_chapter = chapter
        self.manager.current = "course_content"

class ChapterContentScreen(Screen, DialogMixin):
    def on_pre_enter(self):
        chapter = self.manager.current_chapter
        if chapter:
            self.ids.chapter_title.title = chapter['title']
            self.load_content()

    def load_content(self):
        """Загрузка содержания главы"""
        chapter = self.manager.current_chapter
        if not chapter:
            return
        
        app = MDApp.get_running_app()
        
        async def async_load_content():
            try:
                chapter_detail = await app.api_client.get_chapter_detail(chapter['id'])
                return chapter_detail
            except Exception as e:
                return None

        def handle_content_result(chapter_detail):
            if chapter_detail:
                self._update_content_ui(chapter_detail)

        app.run_async_task(async_load_content(), handle_content_result)

    def _update_content_ui(self, chapter_detail):
        """Обновление UI с содержанием главы"""
        if not hasattr(self.ids, 'content_container'):
            return
            
        content_container = self.ids.content_container
        content_container.clear_widgets()
        
        content = chapter_detail.get('content')
        if content:
            # Текстовое содержание
            if content.get('text'):
                text_label = MDLabel(
                    text=content['text'],
                    text_size=(None, None),
                    halign="left",
                    size_hint_y=None
                )
                text_label.bind(texture_size=text_label.setter('size'))
                content_container.add_widget(text_label)
            
            # Видео
            if content.get('video'):
                video_button = MDRaisedButton(
                    text="▶ Смотреть видео",
                    size_hint_y=None,
                    height=dp(50),
                    on_release=lambda x: self.open_video(content['video'])
                )
                content_container.add_widget(video_button)
            
            # Файлы
            if content.get('files'):
                file_button = MDRaisedButton(
                    text="📄 Скачать файлы",
                    size_hint_y=None,
                    height=dp(50),
                    on_release=lambda x: self.download_files(content['files'])
                )
                content_container.add_widget(file_button)
        
        # Кнопка теста
        if chapter_detail.get('has_test'):
            test_button = MDRaisedButton(
                text="📝 Пройти тест для самопроверки",
                size_hint_y=None,
                height=dp(50),
                on_release=lambda x: self.take_self_check_test()
            )
            content_container.add_widget(test_button)
        
        # Кнопка завершения главы
        complete_text = "✓ Глава завершена" if chapter_detail.get('is_completed') else "Завершить главу"
        complete_button = MDRaisedButton(
            text=complete_text,
            size_hint_y=None,
            height=dp(50),
            disabled=chapter_detail.get('is_completed', False),
            on_release=lambda x: self.complete_chapter()
        )
        content_container.add_widget(complete_button)

    def open_video(self, video_path):
        """Открытие видео"""
        import webbrowser
        app = MDApp.get_running_app()
        video_url = app.api_client.get_video_url(self.manager.current_chapter['id'])
        webbrowser.open(video_url)

    def download_files(self, files_path):
        """Скачивание файлов"""
        import webbrowser
        app = MDApp.get_running_app()
        file_url = app.api_client.get_file_url(self.manager.current_chapter['id'])
        webbrowser.open(file_url)

    def complete_chapter(self):
        """Завершение главы"""
        chapter = self.manager.current_chapter
        if not chapter:
            return
        
        app = MDApp.get_running_app()
        
        async def async_complete_chapter():
            try:
                success = await app.api_client.complete_chapter(chapter['id'])
                return success
            except Exception as e:
                return False

        def handle_completion_result(success):
            if success:
                self.show_success_dialog("Глава завершена!")
                # Обновляем статус главы
                chapter['is_completed'] = True
                # Перезагружаем содержание
                Clock.schedule_once(lambda dt: self.load_content(), 0.5)
            else:
                self.show_error_dialog("Не удалось завершить главу")

        app.run_async_task(async_complete_chapter(), handle_completion_result)

    def take_self_check_test(self):
        """Переход к тесту для самопроверки"""
        self.manager.current = "selfcheck_test"

class SelfCheckTestScreen(Screen, DialogMixin):
    def on_pre_enter(self):
        self.load_test()

    def load_test(self):
        """Загрузка теста"""
        self.show_notification_snackbar("Функция в разработке")

    def submit_test(self):
        """Отправка ответов теста"""
        self.show_notification_snackbar("Функция в разработке")

class ControlTestScreen(Screen, DialogMixin):
    def on_pre_enter(self):
        self.load_test()

    def load_test(self):
        """Загрузка контрольного теста"""
        self.show_notification_snackbar("Функция в разработке")

    def finish_test(self):
        """Завершение контрольного теста"""
        self.show_notification_snackbar("Функция в разработке")
