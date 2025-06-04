# main.py
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivy.logger import Logger

# Импортируем API клиент вместо прямого подключения к БД
from api_client import APIClient

# Импортируем экраны
from screens import (
    LoginScreen, MainScreen, CourseDetailsScreen, 
    TestDetailsScreen, ResultScreen, 
    CourseInfoScreen, CourseProgressScreen, 
    CourseChaptersScreen, CourseContentScreen
)

# Главный экранный менеджер
class EduScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user = None
        self.current_teacher = None
        self.current_course = None
        self.current_course_index = 1
        self.current_chapter = None
        self.current_test = None
        # Инициализируем API клиент
        self.api_client = APIClient(base_url="http://172.22.151.6:8000")

# Основное приложение
class EduApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        
        # Загружаем KV файл
        try:
            Builder.load_file('app.kv')
        except Exception as e:
            Logger.error(f"Failed to load app.kv: {str(e)}")
        
        # Менеджер экранов
        sm = EduScreenManager()
        
        # Добавляем экраны
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main_screen'))
        sm.add_widget(CourseDetailsScreen(name='course_details'))
        sm.add_widget(TestDetailsScreen(name='test_details'))
        sm.add_widget(ResultScreen(name="result_screen"))
        sm.add_widget(CourseInfoScreen(name="course_info"))
        sm.add_widget(CourseProgressScreen(name="course_progress"))
        sm.add_widget(CourseChaptersScreen(name="course_chapters"))
        sm.add_widget(CourseContentScreen(name="course_content"))
        
        return sm

    def show_course_progress(self, index):
        """Показать прогресс курса"""
        self.root.current_course_index = index
        self.root.current = "course_progress"

    def logout(self):
        """Выход из системы"""
        if hasattr(self.root, 'current_user'):
            self.root.current_user = None
        self.root.current = "login"

if __name__ == '__main__':
    EduApp().run()