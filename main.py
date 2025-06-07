# main.py
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivy.core.window import Window
from kivymd.uix.snackbar import Snackbar
from kivy.clock import Clock
from screens import *
import os
import json
from pathlib import Path
from api_client import APIClient
import logging
import threading
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка размера окна для мобильных устройств
Window.size = (360, 640)

class EduScreenManager(ScreenManager):
    """Расширенный менеджер экранов с поддержкой API"""
    current_user = None
    current_course = None
    current_chapter = None
    current_test = None
    api_client = None

class EduApp(MDApp):
    """Главное приложение с интеграцией API"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_user = None
        self.api_client = None
        self.token_storage_path = Path("user_token.json")

    def build(self):
        """Построение основного интерфейса"""
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # Инициализируем API клиент
        self.init_api_client()

        # Загружаем KV файл
        try:
            Builder.load_file('app.kv')
        except FileNotFoundError:
            logger.error("Файл app.kv не найден!")
            self.show_notification("Ошибка: файл интерфейса не найден")
            return None

        # Создаем менеджер экранов
        sm = EduScreenManager()
        sm.api_client = self.api_client

        # Добавляем все экраны
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main_screen'))
        sm.add_widget(CourseDetailsScreen(name='course_details'))
        sm.add_widget(ChapterContentScreen(name='course_content'))
        sm.add_widget(SelfCheckTestScreen(name='selfcheck_test'))
        sm.add_widget(ControlTestScreen(name='control_test_screen'))

        return sm

    def run_async_task(self, coro, callback=None):
        """Безопасный запуск асинхронной задачи"""
        def run_in_thread():
            try:
                # Создаем новый event loop для каждой задачи
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Выполняем корутину
                result = loop.run_until_complete(coro)
                
                # Планируем callback в главном потоке
                if callback:
                    Clock.schedule_once(lambda dt: callback(result), 0)
                
                # Закрываем loop
                #loop.close()()
                
            except Exception as e:
                logger.error(f"Ошибка в асинхронной задаче: {e}")
                if callback:
                    Clock.schedule_once(lambda dt: callback(None), 0)

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

    def init_api_client(self):
        """Инициализация API клиента"""
        try:
            # Базовый URL вашего Django сервера
            base_url = "http://127.0.0.1:8000"  # Замените на ваш URL
            self.api_client = APIClient(base_url)

            # Пытаемся загрузить сохраненный токен
            self.load_saved_token()

            logger.info("API клиент инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации API клиента: {e}")
            self.show_notification("Ошибка подключения к серверу")

    def load_saved_token(self):
        """Загрузка сохраненного токена пользователя"""
        try:
            if self.token_storage_path.exists():
                with open(self.token_storage_path, 'r') as f:
                    token_data = json.load(f)

                if 'access_token' in token_data and 'user_info' in token_data:
                    # Сохраняем токены в API клиенте
                    self.api_client._access_token = token_data['access_token']
                    self.api_client._refresh_token = token_data.get('refresh_token')
                    self._current_user = token_data['user_info']

                    # Проверяем валидность токена
                    Clock.schedule_once(self.validate_stored_token, 0.5)

        except Exception as e:
            logger.error(f"Ошибка загрузки токена: {e}")
            self.clear_saved_token()

    def validate_stored_token(self, dt):
        """Проверка валидности сохраненного токена"""
        async def check_token():
            try:
                user_data = await self.api_client.get_current_user()
                return user_data
            except Exception as e:
                logger.error(f"Ошибка проверки токена: {e}")
                return None

        def handle_result(result):
            if result:
                logger.info("Токен валиден, автоматический вход")
                self.root.current = "main_screen"
            else:
                logger.info("Токен недействителен")
                self.clear_saved_token()

        self.run_async_task(check_token(), handle_result)

    def save_user_token(self, access_token, refresh_token, user_info):
        """Сохранение токена пользователя"""
        try:
            token_data = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_info': user_info
            }

            with open(self.token_storage_path, 'w') as f:
                json.dump(token_data, f)

            logger.info("Токен сохранен")
        except Exception as e:
            logger.error(f"Ошибка сохранения токена: {e}")

    def clear_saved_token(self):
        """Очистка сохраненного токена"""
        try:
            if self.token_storage_path.exists():
                self.token_storage_path.unlink()

            if self.api_client:
                self.api_client._access_token = None
                self.api_client._refresh_token = None

            self._current_user = None
            logger.info("Токен очищен")
        except Exception as e:
            logger.error(f"Ошибка очистки токена: {e}")

    def get_current_user(self):
        """Получение текущего пользователя"""
        return self._current_user

    def set_current_user(self, user):
        """Установка текущего пользователя"""
        self._current_user = user
        if hasattr(self.root, 'current_user'):
            self.root.current_user = user

    def login_user(self, username, password):
        """Вход пользователя"""
        async def async_login():
            try:
                result = await self.api_client.login(username, password)
                return result
            except Exception as e:
                logger.error(f"Ошибка входа: {e}")
                return {"success": False, "error": "Ошибка сети"}

        def handle_login_result(result):
            if result and result.get('success'):
                user_info = result.get('user')
                if user_info:
                    self.set_current_user(user_info)
                    self.save_user_token(
                        self.api_client._access_token,
                        self.api_client._refresh_token,
                        user_info
                    )
                    self.root.current = "main_screen"
                    self.show_notification(f"Добро пожаловать, {user_info.get('first_name', '')}!")
            else:
                error_msg = result.get('error', 'Ошибка входа') if result else 'Ошибка сети'
                self.show_notification(error_msg)

        self.run_async_task(async_login(), handle_login_result)

    def register_user(self, username, email, password, first_name, last_name):
        """Регистрация пользователя"""
        async def async_register():
            try:
                result = await self.api_client.register(username, email, password, first_name, last_name)
                return result
            except Exception as e:
                logger.error(f"Ошибка регистрации: {e}")
                return {"success": False, "error": "Ошибка сети"}

        def handle_register_result(result):
            if result and result.get('success'):
                self.show_notification("Регистрация прошла успешно!")
            else:
                error_msg = result.get('error', 'Ошибка регистрации') if result else 'Ошибка сети'
                self.show_notification(error_msg)

        self.run_async_task(async_register(), handle_register_result)

    def logout(self):
        """Выход из системы"""
        async def async_logout():
            try:
                await self.api_client.logout()
            except Exception as e:
                logger.error(f"Ошибка выхода: {e}")

        self.run_async_task(async_logout())
        
        self.clear_saved_token()
        self.set_current_user(None)

        # Очищаем данные в менеджере экранов
        if hasattr(self.root, 'current_course'):
            self.root.current_course = None
        if hasattr(self.root, 'current_chapter'):
            self.root.current_chapter = None
        if hasattr(self.root, 'current_test'):
            self.root.current_test = None

        self.root.current = "login"
        self.show_notification("Вы вышли из системы")

    def show_notification(self, message):
        """Показать уведомление"""
        try:
            Snackbar(text=message, duration=3).open()
        except Exception as e:
            logger.error(f"Ошибка показа уведомления: {e}")

    def on_start(self):
        """Выполняется при запуске приложения"""
        logger.info("Приложение запущено")
        # Проверяем доступность сервера
        Clock.schedule_once(self.check_server_connection, 1.0)

    def check_server_connection(self, dt):
        """Проверка подключения к серверу"""
        async def check_connection():
            try:
                response = await self.api_client.client.get(f"{self.api_client.api_base}/health/")
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Ошибка проверки соединения: {e}")
                return False

        def handle_connection_result(is_connected):
            if is_connected:
                logger.info("Соединение с сервером установлено")
                self.show_notification("Подключение к серверу OK")
            else:
                logger.warning("Нет соединения с сервером")
                self.show_notification("Проблемы с подключением к серверу")

        self.run_async_task(check_connection(), handle_connection_result)

    def on_pause(self):
        """Приложение свернуто"""
        logger.info("Приложение свернуто")
        return True

    def on_resume(self):
        """Приложение восстановлено"""
        logger.info("Приложение восстановлено")
        # Проверяем соединение при восстановлении
        Clock.schedule_once(self.check_server_connection, 0.5)

    def on_stop(self):
        """Выполняется при закрытии приложения"""
        logger.info("Приложение закрыто")

# Функция запуска приложения с обработкой ошибок
def main():
    """Главная функция запуска приложения"""
    try:
        app = EduApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Приложение прервано пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
