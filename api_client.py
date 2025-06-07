# api_client.py
import httpx
import json
from typing import Optional, Dict, Any, List
from kivy.logger import Logger
from kivy.storage.jsonstore import JsonStore
import asyncio
from pathlib import Path

class APIClient:
    """HTTP клиент для взаимодействия с Django Ninja API"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.token_store = JsonStore('tokens.json')
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._load_tokens()
        
        # Создаем HTTP клиент с настройками
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        )
    
    def _load_tokens(self):
        """Загружает токены из хранилища"""
        try:
            if self.token_store.exists('auth'):
                auth_data = self.token_store.get('auth')
                self._access_token = auth_data.get('access_token')
                self._refresh_token = auth_data.get('refresh_token')
        except Exception as e:
            Logger.warning(f"Не удалось загрузить токены: {e}")
    
    def _save_tokens(self, access_token: str, refresh_token: str):
        """Сохраняет токены в хранилище"""
        try:
            self.token_store.put('auth', 
                access_token=access_token,
                refresh_token=refresh_token
            )
            self._access_token = access_token
            self._refresh_token = refresh_token
        except Exception as e:
            Logger.error(f"Не удалось сохранить токены: {e}")
    
    def _clear_tokens(self):
        """Удаляет токены"""
        try:
            if self.token_store.exists('auth'):
                self.token_store.delete('auth')
            self._access_token = None
            self._refresh_token = None
        except Exception as e:
            Logger.error(f"Не удалось удалить токены: {e}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Возвращает заголовки аутентификации"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        return headers
    
    async def _refresh_access_token(self) -> bool:
        """Обновляет access токен используя refresh токен"""
        if not self._refresh_token:
            return False
        
        try:
            response = await self.client.post(
                f"{self.api_base}/auth/refresh/",
                json={"refresh": self._refresh_token},
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data['access']
                # Обновляем только access токен
                self.token_store.put('auth', 
                    access_token=self._access_token,
                    refresh_token=self._refresh_token
                )
                return True
        except Exception as e:
            Logger.error(f"Ошибка обновления токена: {e}")
        
        return False
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Выполняет HTTP запрос с автоматическим обновлением токена"""
        url = f"{self.api_base}{endpoint}"
        headers = kwargs.get('headers', {})
        headers.update(self._get_auth_headers())
        kwargs['headers'] = headers
        
        # Первая попытка
        response = await self.client.request(method, url, **kwargs)
        
        # Если получили 401, пытаемся обновить токен
        if response.status_code == 401 and self._refresh_token:
            if await self._refresh_access_token():
                # Обновляем заголовки и повторяем запрос
                headers.update(self._get_auth_headers())
                kwargs['headers'] = headers
                response = await self.client.request(method, url, **kwargs)
        
        return response
    
    # Методы аутентификации
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Авторизация пользователя"""
        try:
            response = await self.client.post(
                f"{self.api_base}/auth/login/",
                json={"username": username, "password": password},
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._save_tokens(data['access'], data['refresh'])
                return {"success": True, "user": data['user']}
            else:
                error_data = response.json()
                return {"success": False, "error": error_data.get('detail', 'Ошибка входа')}
                
        except Exception as e:
            Logger.error(f"Ошибка входа: {e}")
            return {"success": False, "error": "Ошибка сети"}
    
    async def register(self, username: str, email: str, password: str, 
                      first_name: str, last_name: str) -> Dict[str, Any]:
        """Регистрация нового пользователя"""
        try:
            response = await self.client.post(
                f"{self.api_base}/auth/register/",
                json={
                    "username": username,
                    "email": email, 
                    "password": password,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": "student"
                },
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 201:
                data = response.json()
                return {"success": True, "message": data['message']}
            else:
                error_data = response.json()
                return {"success": False, "error": error_data.get('detail', 'Ошибка регистрации')}
                
        except Exception as e:
            Logger.error(f"Ошибка регистрации: {e}")
            return {"success": False, "error": "Ошибка сети"}
    
    async def logout(self):
        """Выход из системы"""
        try:
            if self._access_token:
                await self._make_request('POST', '/auth/logout/')
        except Exception as e:
            Logger.error(f"Ошибка выхода: {e}")
        finally:
            self._clear_tokens()
    
    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Получение информации о текущем пользователе"""
        try:
            response = await self._make_request('GET', '/auth/me/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения пользователя: {e}")
        return None
    
    # Методы для работы с курсами
    async def get_courses(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение списка курсов"""
        try:
            params = {}
            if category_id:
                params['category_id'] = category_id
            
            response = await self._make_request('GET', '/courses/', params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения курсов: {e}")
        return []
    
    async def get_course_detail(self, course_id: int) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о курсе"""
        try:
            response = await self._make_request('GET', f'/courses/{course_id}/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения курса: {e}")
        return None
    
    async def subscribe_to_course(self, course_id: int) -> bool:
        """Подписка на курс"""
        try:
            response = await self._make_request('POST', f'/courses/{course_id}/subscribe/')
            return response.status_code == 200
        except Exception as e:
            Logger.error(f"Ошибка подписки на курс: {e}")
            return False
    
    # Методы для работы с главами
    async def get_chapters(self, course_id: int) -> List[Dict[str, Any]]:
        """Получение списка глав курса"""
        try:
            response = await self._make_request('GET', f'/chapters/course/{course_id}/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения глав: {e}")
        return []
    
    async def get_chapter_detail(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о главе"""
        try:
            response = await self._make_request('GET', f'/chapters/{chapter_id}/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения главы: {e}")
        return None
    
    async def complete_chapter(self, chapter_id: int) -> bool:
        """Отметить главу как завершенную"""
        try:
            response = await self._make_request('POST', f'/chapters/{chapter_id}/complete/')
            return response.status_code == 200
        except Exception as e:
            Logger.error(f"Ошибка завершения главы: {e}")
            return False
    
    # Методы для работы с тестами
    async def get_chapter_test(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        """Получение теста для самопроверки"""
        try:
            response = await self._make_request('GET', f'/tests/chapter/{chapter_id}/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения теста: {e}")
        return None
    
    async def submit_chapter_test(self, chapter_id: int, answers: Dict[str, List[int]]) -> Optional[Dict[str, Any]]:
        """Отправка ответов на тест для самопроверки"""
        try:
            response = await self._make_request('POST', f'/tests/chapter/{chapter_id}/submit/', 
                                               json={"answers": answers})
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка отправки теста: {e}")
        return None
    
    async def get_control_tests(self) -> List[Dict[str, Any]]:
        """Получение списка контрольных тестов"""
        try:
            response = await self._make_request('GET', '/tests/control/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения контрольных тестов: {e}")
        return []
    
    async def get_control_test(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Получение контрольного теста"""
        try:
            response = await self._make_request('GET', f'/tests/control/{test_id}/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения контрольного теста: {e}")
        return None
    
    async def submit_control_test(self, test_id: int, answers: Dict[str, List[int]]) -> Optional[Dict[str, Any]]:
        """Отправка ответов на контрольный тест"""
        try:
            response = await self._make_request('POST', f'/tests/control/{test_id}/submit/', 
                                               json={"answers": answers})
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка отправки контрольного теста: {e}")
        return None
    
    # Методы для работы с прогрессом
    async def get_course_progress(self) -> List[Dict[str, Any]]:
        """Получение прогресса по курсам"""
        try:
            response = await self._make_request('GET', '/progress/courses/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения прогресса: {e}")
        return []
    
    async def get_user_statistics(self) -> Optional[Dict[str, Any]]:
        """Получение статистики пользователя"""
        try:
            response = await self._make_request('GET', '/progress/statistics/')
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            Logger.error(f"Ошибка получения статистики: {e}")
        return None
    
    # Методы для работы с медиафайлами
    def get_video_url(self, content_id: int) -> str:
        """Получение URL для видео"""
        return f"{self.api_base}/media/video/{content_id}/"
    
    def get_file_url(self, content_id: int) -> str:
        """Получение URL для скачивания файла"""
        return f"{self.api_base}/media/file/{content_id}/"
    
    async def close(self):
        """Закрытие HTTP клиента"""
        await self.client.aclose()

# Глобальный экземпляр API клиента
api_client = APIClient()
