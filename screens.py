# screens_fixed.py - исправленная версия screens.py для работы с API

from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineListItem
from kivymd.uix.label import MDLabel
from kivy.properties import ObjectProperty, StringProperty
from kivy.metrics import dp
from kivy.factory import Factory
from kivymd.uix.textfield import MDTextField
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.gridlayout import GridLayout
import re
from kivy.clock import Clock
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.card import MDCard
from kivymd.uix.expansionpanel import MDExpansionPanel, MDExpansionPanelOneLine
import logging
import io
from kivy.core.image import Image as CoreImage
from kivy.logger import Logger

# ---------- Общие инструменты и виджеты ----------

class DialogMixin:
    def show_error_dialog(self, text):
        dialog = MDDialog(
            title="Ошибка",
            text=text,
            buttons=[MDFlatButton(text="OK")]
        )
        dialog.buttons[0].bind(on_release=lambda x: dialog.dismiss())
        dialog.open()

    def show_success_dialog(self, text):
        dialog = MDDialog(
            title="Успех",
            text=text,
            buttons=[MDFlatButton(text="OK")]
        )
        dialog.buttons[0].bind(on_release=lambda x: dialog.dismiss())
        dialog.open()

class LoginScreen(Screen, DialogMixin):
    username = ObjectProperty(None)
    password = ObjectProperty(None)
    dialog = None

    def on_enter(self):
        Clock.schedule_once(self._init_widgets)

    def _init_widgets(self, dt):
        if 'username_field' in self.ids:
            self.username = self.ids.username_field

        if 'password_field' in self.ids:
            self.password = self.ids.password_field

    def try_login(self):
        """Попытка входа через API клиент"""
        try:
            api_client = self.manager.api_client
            
            username = self.username.text.strip()
            password = self.password.text.strip()
            
            if not username or not password:
                self.show_error_dialog("Заполните все поля")
                return
            
            Logger.info(f"Attempting login for user: {username}")
            
            # Попытка входа через API
            user = api_client.login(username, password)
            
            if user and isinstance(user, dict):
                self.manager.current_user = user
                Logger.info(f"Login successful for user: {username}")
                self.manager.current = "main_screen"
            else:
                Logger.warning(f"Login failed for user: {username}")
                self.show_error_dialog("Неверные учетные данные или проблема с сервером")
                
        except Exception as e:
            Logger.error(f"Login exception: {str(e)}")
            self.show_error_dialog(f"Ошибка входа: {str(e)}")

    def show_register_dialog(self):
        """Показать диалог регистрации"""
        content = Factory.RegisterContent()
        self.dialog = MDDialog(
            title="Регистрация",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda x: self.dialog.dismiss()),
                MDFlatButton(text="OK", on_release=self.process_registration)
            ]
        )
        self.dialog.open()

    def process_registration(self, *args):
        """Обработка регистрации (пока заглушка)"""
        self.show_error_dialog("Регистрация пока недоступна. Используйте тестовые аккаунты: student1/password123")
        self.dialog.dismiss()

class MainScreen(Screen, DialogMixin):
    def on_enter(self):
        """Загрузка данных при входе на экран"""
        try:
            user = self.manager.current_user
            if not user:
                self.manager.current = "login"
                return
                
            user_role = user.get('role', 'student').lower()
            
            if user_role == "teacher":
                self.load_teacher_courses()
                # Очищаем список в основной вкладке "Курсы" для преподавателя
                if hasattr(self.ids, 'courses_list'):
                    self.ids.courses_list.clear_widgets()
            else:
                self.load_courses()
                self.load_tests()
                # Убираем вкладку "Преподавание" для студентов
                if hasattr(self.ids, 'teaching_tab') and hasattr(self.ids, 'bottom_nav'):
                    try:
                        self.ids.bottom_nav.remove_widget(self.ids.teaching_tab)
                    except:
                        pass  # Вкладка уже удалена или не существует
                        
        except Exception as e:
            Logger.error(f"MainScreen on_enter error: {str(e)}")
            self.show_error_dialog(f"Ошибка загрузки: {str(e)}")

    def load_courses(self):
        """Загрузка курсов через API"""
        try:
            api_client = self.manager.api_client
            courses = api_client.get_courses()
            
            if hasattr(self.ids, 'courses_list'):
                self.ids.courses_list.clear_widgets()
                
                if courses:
                    for course in courses:
                        item = OneLineListItem(
                            text=course.get('title', 'Без названия'),
                            on_release=lambda instance, c=course: self.go_to_course(c)
                        )
                        self.ids.courses_list.add_widget(item)
                else:
                    # Добавляем сообщение, если курсов нет
                    no_courses_label = MDLabel(
                        text="Нет доступных курсов",
                        halign="center"
                    )
                    self.ids.courses_list.add_widget(no_courses_label)
                    
        except Exception as e:
            Logger.error(f"Load courses error: {str(e)}")
            self.show_error_dialog(f"Ошибка загрузки курсов: {str(e)}")

    def load_tests(self):
        """Загрузка тестов"""
        try:
            if hasattr(self.ids, 'tests_list'):
                self.ids.tests_list.clear_widgets()
                
                # Добавляем тестовый экземпляр теста
                test_item = OneLineListItem(
                    text="Тест по программированию",
                    on_release=lambda x: self.go_to_test(None)
                )
                self.ids.tests_list.add_widget(test_item)
                
        except Exception as e:
            Logger.error(f"Load tests error: {str(e)}")

    def load_teacher_courses(self):
        """Загрузка курсов для преподавателя"""
        try:
            api_client = self.manager.api_client
            courses = api_client.get_courses()
            
            if hasattr(self.ids, 'teacher_course_list'):
                self.ids.teacher_course_list.clear_widgets()
                
                if courses:
                    for course in courses:
                        item = OneLineListItem(
                            text=course.get('title', 'Без названия'),
                            on_release=lambda instance, c=course: self.go_to_course(c)
                        )
                        self.ids.teacher_course_list.add_widget(item)
                        
        except Exception as e:
            Logger.error(f"Load teacher courses error: {str(e)}")

    def go_to_course(self, course):
        """Переход к курсу"""
        try:
            self.manager.current_course = course
            user_role = self.manager.current_user.get('role', 'student').lower()
            
            if user_role == "teacher":
                self.manager.current = "course_info"
            else:
                self.manager.current = "course_details"
                
        except Exception as e:
            Logger.error(f"Go to course error: {str(e)}")
            self.show_error_dialog(f"Ошибка перехода к курсу: {str(e)}")

    def go_to_test(self, test):
        """Переход к тесту"""
        self.manager.current = "test_details"

    def logout(self):
        """Выход из системы"""
        self.manager.current_user = None
        self.manager.current = "login"

class CourseDetailsScreen(Screen, DialogMixin):
    """Экран для выполнения курса (для студентов)"""
    
    def on_pre_enter(self):
        """Загрузка информации о курсе"""
        try:
            course = self.manager.current_course
            if not course:
                self.show_error_dialog("Курс не выбран")
                self.manager.current = "main_screen"
                return
                
            # Обновляем информацию о курсе
            if hasattr(self.ids, 'course_title_label'):
                self.ids.course_title_label.text = course.get('title', 'Без названия')
            if hasattr(self.ids, 'course_description_label'):
                self.ids.course_description_label.text = course.get('description', 'Без описания')
            
            # Загружаем разделы курса
            self.load_chapters()
            
        except Exception as e:
            Logger.error(f"CourseDetailsScreen on_pre_enter error: {str(e)}")
            self.show_error_dialog(f"Ошибка загрузки курса: {str(e)}")

    def load_chapters(self):
        """Загрузка разделов курса"""
        try:
            course = self.manager.current_course
            if not course:
                return
                
            api_client = self.manager.api_client
            chapters = api_client.get_chapters(course.get('id'))
            
            if hasattr(self.ids, 'chapters_list'):
                self.ids.chapters_list.clear_widgets()
                
                if chapters:
                    for chapter in chapters:
                        label = MDLabel(
                            text=chapter.get('title', 'Без названия'),
                            halign="center",
                            theme_text_color="Primary",
                            font_style="Body1"
                        )
                        self.ids.chapters_list.add_widget(label)
                else:
                    no_chapters_label = MDLabel(
                        text="Нет доступных разделов",
                        halign="center"
                    )
                    self.ids.chapters_list.add_widget(no_chapters_label)
                    
        except Exception as e:
            Logger.error(f"Load chapters error: {str(e)}")

class CourseChaptersScreen(Screen, DialogMixin):
    """Экран со списком разделов курса"""
    
    def on_pre_enter(self):
        """Загрузка разделов курса"""
        try:
            course = self.manager.current_course
            if not course:
                self.show_error_dialog("Курс не выбран")
                self.manager.current = "main_screen"
                return
                
            self.load_chapters()
            
        except Exception as e:
            Logger.error(f"CourseChaptersScreen on_pre_enter error: {str(e)}")
            self.show_error_dialog(f"Ошибка: {str(e)}")

    def load_chapters(self):
        """Загрузка разделов"""
        try:
            course = self.manager.current_course
            api_client = self.manager.api_client
            chapters = api_client.get_chapters(course.get('id'))
            
            if hasattr(self.ids, 'chapters_list'):
                self.ids.chapters_list.clear_widgets()
                
                if chapters:
                    for chapter in chapters:
                        item = OneLineListItem(
                            text=chapter.get('title', 'Без названия'),
                            on_release=lambda instance, ch=chapter: self.go_to_chapter(ch)
                        )
                        self.ids.chapters_list.add_widget(item)
                        
        except Exception as e:
            Logger.error(f"Load chapters error: {str(e)}")

    def go_to_chapter(self, chapter):
        """Переход к разделу"""
        self.manager.current_chapter = chapter
        self.manager.current = "course_content"

class CourseContentScreen(Screen, DialogMixin):
    """Экран для отображения содержимого раздела курса"""
    
    def on_pre_enter(self):
        """Загрузка контента раздела"""
        try:
            chapter = self.manager.current_chapter
            if not chapter:
                self.manager.current = "course_chapters"
                return
                
            # Обновляем заголовок
            if hasattr(self.ids, 'chapter_title'):
                self.ids.chapter_title.title = chapter.get('title', 'Без названия')
            
            # Загружаем контент
            api_client = self.manager.api_client
            content = api_client.get_content(chapter.get('id'))
            
            if hasattr(self.ids, 'content_label'):
                if content:
                    content_text = ""
                    if content.get('text'):
                        content_text += f"{content['text']}\n"
                    if content.get('video'):
                        content_text += f"Видео: {content['video']}\n"
                    if content.get('files'):
                        content_text += f"Файлы: {content['files']}\n"
                    
                    if content_text:
                        self.ids.content_label.text = content_text
                    else:
                        self.ids.content_label.text = "Контент загружается..."
                else:
                    self.ids.content_label.text = "Нет контента для этого раздела."
            
            # Проверяем статус завершения
            self.check_completion_status()
            
        except Exception as e:
            Logger.error(f"CourseContentScreen on_pre_enter error: {str(e)}")
            self.show_error_dialog(f"Ошибка загрузки контента: {str(e)}")

    def check_completion_status(self):
        """Проверка статуса завершения раздела"""
        try:
            # Пока упрощенная версия - всегда доступна кнопка "Далее"
            if hasattr(self.ids, 'next_button'):
                self.ids.next_button.disabled = False
        except Exception as e:
            Logger.error(f"Check completion status error: {str(e)}")

    def next_content(self):
        """Переход к следующему контенту"""
        try:
            chapter = self.manager.current_chapter
            user = self.manager.current_user
            course = self.manager.current_course
            
            if not all([chapter, user, course]):
                self.show_error_dialog("Недостаточно данных для продолжения")
                return
            
            # Отмечаем раздел как завершенный
            api_client = self.manager.api_client
            success = api_client.mark_chapter_completed(
                user.get('id'),
                course.get('id'),
                chapter.get('id')
            )
            
            if success:
                self.show_success_dialog("Раздел отмечен как выполненный.")
                if hasattr(self.ids, 'next_button'):
                    self.ids.next_button.disabled = True
                
                # Пытаемся найти следующий раздел
                self.find_next_chapter()
            else:
                self.show_error_dialog("Ошибка при сохранении прогресса")
                
        except Exception as e:
            Logger.error(f"Next content error: {str(e)}")
            self.show_error_dialog(f"Ошибка: {str(e)}")

    def find_next_chapter(self):
        """Поиск следующего раздела"""
        try:
            # Упрощенная версия - возвращаемся к списку разделов
            Clock.schedule_once(lambda dt: self.go_back_to_chapters(), 2)
            
        except Exception as e:
            Logger.error(f"Find next chapter error: {str(e)}")
            
    def go_back_to_chapters(self):
        """Возврат к списку разделов"""
        self.manager.current = "course_chapters"



class TestDetailsScreen(Screen, DialogMixin):
    def on_pre_enter(self):
        """Инициализация тестовых данных"""
        # Упрощенные тестовые данные
        self.test_data = {
            "id": 1,
            "title": "Тест по программированию",
            "questions": [
                {
                    "id": 1,
                    "text": "Что такое Python?",
                    "type": "single_choice",
                    "options": ["Язык программирования", "Операционная система", "База данных"],
                    "correct_answer": 0
                }
            ]
        }
        self.current_question_index = 0
        self.answers = {}
        self.update_question_display()

    def update_question_display(self):
        """Обновление отображения вопроса"""
        try:
            if hasattr(self.ids, 'test_title'):
                self.ids.test_title.text = self.test_data["title"]
            if hasattr(self.ids, 'question_text'):
                question = self.test_data["questions"][0]
                self.ids.question_text.text = question["text"]
        except Exception as e:
            Logger.error(f"Update question display error: {str(e)}")

    def next_question(self):
        """Переход к следующему вопросу"""
        self.finish_test()

    def prev_question(self):
        """Возврат к предыдущему вопросу"""
        pass

    def finish_test(self):
        """Завершение теста"""
        result = {"score": 1, "total": 1, "percentage": 100}
        result_screen = self.manager.get_screen('result_screen')
        result_screen.set_result(result)
        self.manager.current = 'result_screen'

    def go_back(self):
        """Возврат назад"""
        self.manager.current = 'main_screen'

class ResultScreen(Screen, DialogMixin):
    def set_result(self, result):
        """Установка результата теста"""
        self.result = result
        self.update_display()

    def update_display(self):
        """Обновление отображения результата"""
        try:
            if hasattr(self, 'result') and self.result:
                if hasattr(self.ids, 'score_label'):
                    self.ids.score_label.text = f"Результат: {self.result['score']} из {self.result['total']}"
                if hasattr(self.ids, 'percentage_label'):
                    self.ids.percentage_label.text = f"Процент: {self.result['percentage']:.1f}%"
        except Exception as e:
            Logger.error(f"Update result display error: {str(e)}")

    def go_back(self):
        """Возврат к главному меню"""
        self.manager.current = 'main_screen'

# Заглушки для остальных экранов
class CourseInfoScreen(Screen, DialogMixin):
    def on_pre_enter(self):
        """Загрузка информации о курсе для преподавателя"""
        try:
            course = self.manager.current_course
            if course and hasattr(self.ids, 'info_title'):
                self.ids.info_title.text = course.get('title', 'Без названия')
                self.ids.info_description.text = course.get('description', 'Без описания')
                self.ids.info_status.text = course.get('status', 'Неизвестно')
        except Exception as e:
            Logger.error(f"CourseInfoScreen error: {str(e)}")

class CourseProgressScreen(Screen, DialogMixin):
    def on_enter(self):
        """Отображение прогресса курса"""
        try:
            index = getattr(self.manager, 'current_course_index', 1)
            # Заглушка с фиктивными данными
            if hasattr(self.ids, 'details_label'):
                self.ids.details_label.text = f"Прогресс курса {index}: 75%"
        except Exception as e:
            Logger.error(f"CourseProgressScreen error: {str(e)}")