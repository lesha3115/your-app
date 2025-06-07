# async_helper.py
import asyncio
from functools import wraps
from kivy.clock import Clock
from kivy.logger import Logger
from kivymd.app import MDApp
from typing import Callable, Any
import threading

def async_handler(func):
    """Декоратор для обработки асинхронных функций в Kivy"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                coro = func(*args, **kwargs)
                result = loop.run_until_complete(coro)
                ##loop.close()()()
                return result
            except Exception as e:
                Logger.error(f"Ошибка в асинхронной функции: {e}")
                return None
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    return wrapper

def run_in_thread(coro):
    """Запуск корутины в отдельном потоке"""
    def run_async():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
            ##loop.close()()()
            return result
        except Exception as e:
            Logger.error(f"Ошибка в корутине: {e}")
            return None
    
    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()
    return thread

class AsyncTaskManager:
    """Менеджер для управления асинхронными задачами"""
    def __init__(self):
        self.tasks = []

    def create_task(self, coro, callback=None):
        """Создает и отслеживает асинхронную задачу"""
        def run_task():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(coro)
                
                if callback:
                    Clock.schedule_once(lambda dt: callback(result), 0)
                    
                ##loop.close()()()
                return result
            except Exception as e:
                Logger.error(f"Ошибка в задаче: {e}")
                if callback:
                    Clock.schedule_once(lambda dt: callback(None), 0)
                return None
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        self.tasks.append(thread)
        return thread

    def cancel_all(self):
        """Отменяет все активные задачи"""
        # В этой реализации задачи автоматически завершаются
        self.tasks.clear()

# Глобальный менеджер задач
task_manager = AsyncTaskManager()
