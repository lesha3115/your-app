import requests
import json
import sqlite3
import os
from datetime import datetime, timedelta
from kivy.logger import Logger
from kivy.utils import platform

class APIClient:
    def __init__(self, base_url="http://172.22.151.6:8000"):
        self.init_local_db()
        """
        API клиент для работы с Django Ninja сервером
        base_url: адрес сервера (замените на IP вашего компьютера для Android)
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.refresh_token = None
        
        # Настройки для Android совместимости
        self.session.verify = False  # Отключаем SSL проверку для development
        self.session.timeout = 15  # Таймаут 15 секунд
        
        # Инициализация локальной базы данных
        
        
        # Загружаем токены если есть
        self.load_tokens()
    
    def init_local_db(self):
        """Инициализация локальной SQLite базы для кэширования"""
        try:
            # Определяем, на какой платформе мы работаем
            if platform == 'android':
                try:
                    from android.storage import primary_external_storage_path  # type: ignore
                    base_path = primary_external_storage_path()
                except ImportError:
                    Logger.error("APIClient: Не удалось импортировать android.storage, будет использоваться локальный файл")
                    base_path = ''
                db_path = os.path.join(base_path, 'edu_app_cache.db') if base_path else 'edu_app_cache.db'
            else:
                db_path = 'edu_app_cache.db'

            self.db_path = db_path
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    email TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    role TEXT
                )
            ''')
            
            # Таблица курсов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    category_id INTEGER
                )
            ''')
            
            # Таблица глав
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    course_id INTEGER
                )
            ''')
            
            # Таблица контента
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY,
                    text TEXT,
                    video TEXT,
                    files TEXT,
                    chapter_id INTEGER
                )
            ''')
            
            # Таблица для токенов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY,
                    access_token TEXT,
                    refresh_token TEXT,
                    expires_at TEXT
                )
            ''')
            
            # Таблица для несинхронизированных изменений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_sync (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    table_name TEXT,
                    data TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            Logger.info("APIClient: Локальная база данных инициализирована")
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка инициализации БД: {e}")
    
    def save_tokens(self, access_token, refresh_token):
        """Сохранение JWT токенов в локальную базу"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Удаляем старые токены
            cursor.execute('DELETE FROM tokens')
            
            # Сохраняем новые токены
            expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
            cursor.execute('''
                INSERT INTO tokens (access_token, refresh_token, expires_at)
                VALUES (?, ?, ?)
            ''', (access_token, refresh_token, expires_at))
            
            conn.commit()
            conn.close()
            
            self.token = access_token
            self.refresh_token = refresh_token
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка сохранения токенов: {e}")
    
    def load_tokens(self):
        """Загрузка JWT токенов из локальной базы"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT access_token, refresh_token, expires_at FROM tokens ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()
            
            if result:
                access_token, refresh_token, expires_at_str = result
                expires_at = datetime.fromisoformat(expires_at_str)
                
                if datetime.now() < expires_at:
                    self.token = access_token
                    self.refresh_token = refresh_token
                    Logger.info("APIClient: Токены загружены из кэша")
                else:
                    Logger.info("APIClient: Токены истекли")
            
            conn.close()
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка загрузки токенов: {e}")
    
    def get_auth_headers(self):
        """Получение заголовков авторизации"""
        if self.token:
            return {'Authorization': f'Bearer {self.token}'}
        return {}
    
    def make_request(self, method, endpoint, data=None, use_cache=True):
        """Универсальный метод для HTTP запросов с fallback на кэш"""
        try:
            url = f"{self.base_url}/api{endpoint}"
            headers = self.get_auth_headers()
            headers['Content-Type'] = 'application/json'
            
            Logger.info(f"APIClient: {method} запрос к {url}")
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Неподдерживаемый HTTP метод: {method}")
            
            if response.status_code == 200:
                result = response.json()
                Logger.info(f"APIClient: Успешный ответ от сервера")
                return result
            elif response.status_code == 401:
                Logger.warning("APIClient: Токен истек, попытка обновления")
                if self.refresh_access_token():
                    return self.make_request(method, endpoint, data, use_cache)
                else:
                    Logger.error("APIClient: Не удалось обновить токен")
                    return None
            else:
                Logger.error(f"APIClient: HTTP ошибка {response.status_code}")
                return None
                
        except requests.exceptions.ConnectionError:
            Logger.warning("APIClient: Нет соединения, используем кэш")
            if use_cache and method.upper() == 'GET':
                return self.get_from_cache(endpoint)
            return None
        except requests.exceptions.Timeout:
            Logger.warning("APIClient: Таймаут запроса")
            if use_cache and method.upper() == 'GET':
                return self.get_from_cache(endpoint)
            return None
        except Exception as e:
            Logger.error(f"APIClient: Ошибка запроса: {e}")
            return None
    
    def refresh_access_token(self):
        """Обновление access токена используя refresh токен"""
        if not self.refresh_token:
            return False
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/refresh/",
                json={'refresh': self.refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.save_tokens(data['access'], self.refresh_token)
                return True
            else:
                Logger.error("APIClient: Не удалось обновить токен")
                return False
                
        except Exception as e:
            Logger.error(f"APIClient: Ошибка обновления токена: {e}")
            return False
    
    def login(self, username, password):
        """Авторизация пользователя"""
        try:
            data = {
                'username': username,
                'password': password
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/login/",
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.save_tokens(result['access'], result['refresh'])
                
                # Сохраняем информацию о пользователе
                self.cache_user_data(result['user'])
                
                Logger.info("APIClient: Успешная авторизация")
                return result
            else:
                Logger.error(f"APIClient: Ошибка авторизации: {response.status_code}")
                return None
                
        except Exception as e:
            Logger.error(f"APIClient: Ошибка авторизации: {e}")
            return None
    
    def get_courses(self):
        """Получение списка курсов"""
        result = self.make_request('GET', '/courses/')
        if result:
            self.cache_courses(result)
        return result or self.get_courses_from_cache()
    
    def get_course_chapters(self, course_id):
        """Получение глав курса"""
        result = self.make_request('GET', f'/courses/{course_id}/chapters/')
        if result:
            self.cache_chapters(result, course_id)
        return result or self.get_chapters_from_cache(course_id)
    
    def get_chapter_content(self, chapter_id):
        """Получение контента главы"""
        result = self.make_request('GET', f'/chapters/{chapter_id}/content/')
        if result:
            self.cache_content(result, chapter_id)
        return result or self.get_content_from_cache(chapter_id)
    
    def mark_chapter_completed(self, chapter_id):
        """Отметка главы как выполненной"""
        data = {'chapter_id': chapter_id, 'completed': True}
        result = self.make_request('POST', '/progress/', data)
        
        if not result:
            # Сохраняем в pending_sync для последующей синхронизации
            self.save_pending_sync('POST', 'progress', data)
        
        return result
    
    # Методы кэширования
    def cache_user_data(self, user_data):
        """Сохранение данных пользователя в кэш"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO users (id, username, email, first_name, last_name, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_data['id'], user_data['username'], user_data.get('email', ''),
                user_data.get('first_name', ''), user_data.get('last_name', ''),
                user_data.get('role', 'student')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка кэширования пользователя: {e}")
    
    def cache_courses(self, courses_data):
        """Сохранение курсов в кэш"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for course in courses_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO courses (id, title, description, status, category_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    course['id'], course['title'], course['description'],
                    course['status'], course.get('category_id')
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка кэширования курсов: {e}")
    
    def cache_chapters(self, chapters_data, course_id):
        """Сохранение глав в кэш"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for chapter in chapters_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO chapters (id, title, course_id)
                    VALUES (?, ?, ?)
                ''', (chapter['id'], chapter['title'], course_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка кэширования глав: {e}")
    
    def cache_content(self, content_data, chapter_id):
        """Сохранение контента в кэш"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO content (id, text, video, files, chapter_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                content_data['id'], content_data.get('text', ''),
                content_data.get('video', ''), content_data.get('files', ''),
                chapter_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка кэширования контента: {e}")
    
    def get_courses_from_cache(self):
        """Получение курсов из кэша"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, title, description, status, category_id FROM courses')
            rows = cursor.fetchall()
            
            courses = []
            for row in rows:
                courses.append({
                    'id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'status': row[3],
                    'category_id': row[4]
                })
            
            conn.close()
            return courses
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка получения курсов из кэша: {e}")
            return []
    
    def get_chapters_from_cache(self, course_id):
        """Получение глав из кэша"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, title FROM chapters WHERE course_id = ?', (course_id,))
            rows = cursor.fetchall()
            
            chapters = []
            for row in rows:
                chapters.append({
                    'id': row[0],
                    'title': row[1]
                })
            
            conn.close()
            return chapters
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка получения глав из кэша: {e}")
            return []
    
    def get_content_from_cache(self, chapter_id):
        """Получение контента из кэша"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, text, video, files FROM content WHERE chapter_id = ?', (chapter_id,))
            row = cursor.fetchone()
            
            if row:
                content = {
                    'id': row[0],
                    'text': row[1],
                    'video': row[2],
                    'files': row[3]
                }
                conn.close()
                return content
            
            conn.close()
            return None
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка получения контента из кэша: {e}")
            return None
    
    def get_from_cache(self, endpoint):
        """Универсальный метод получения данных из кэша по endpoint"""
        if '/courses/' in endpoint and '/chapters/' in endpoint:
            course_id = endpoint.split('/courses/')[1].split('/')[0]
            return self.get_chapters_from_cache(course_id)
        elif '/chapters/' in endpoint and '/content/' in endpoint:
            chapter_id = endpoint.split('/chapters/')[1].split('/')[0]
            return self.get_content_from_cache(chapter_id)
        elif endpoint == '/courses/':
            return self.get_courses_from_cache()
        else:
            return None
    
    def save_pending_sync(self, action, table_name, data):
        """Сохранение операции для последующей синхронизации"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pending_sync (action, table_name, data, created_at)
                VALUES (?, ?, ?, ?)
            ''', (action, table_name, json.dumps(data), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка сохранения pending sync: {e}")
    
    def sync_pending_changes(self):
        """Синхронизация несинхронизированных изменений"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, action, table_name, data FROM pending_sync ORDER BY created_at')
            rows = cursor.fetchall()
            
            synced_ids = []
            for row in rows:
                sync_id, action, table_name, data_str = row
                data = json.loads(data_str)
                
                if table_name == 'progress' and action == 'POST':
                    result = self.make_request('POST', '/progress/', data, use_cache=False)
                    if result:
                        synced_ids.append(sync_id)
            
            # Удаляем синхронизированные записи
            for sync_id in synced_ids:
                cursor.execute('DELETE FROM pending_sync WHERE id = ?', (sync_id,))
            
            conn.commit()
            conn.close()
            
            Logger.info(f"APIClient: Синхронизировано {len(synced_ids)} изменений")
            
        except Exception as e:
            Logger.error(f"APIClient: Ошибка синхронизации: {e}")
    
    def is_online(self):
        """Проверка доступности сервера"""
        try:
            response = self.session.get(f"{self.base_url}/api/health/", timeout=5)
            return response.status_code == 200
        except:
            return False

# Глобальный экземпляр API клиента
api_client = APIClient(base_url="http://172.22.151.6:8000")