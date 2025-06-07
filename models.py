# models.py - Исправленные модели для полной совместимости с Django БД

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Enum, Float, Table
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# Ассоциативные таблицы для Django-совместимых моделей
test_tasks = Table(
    'tests_testtask',
    Base.metadata,
    Column('id', BigInteger, primary_key=True),
    Column('task_id', BigInteger, ForeignKey('tests_task.id'), nullable=False),
    Column('test_id', BigInteger, ForeignKey('tests_test.id'), nullable=False),
    extend_existing=True
)

control_test_tasks = Table(
    'tests_controltesttask',
    Base.metadata,
    Column('id', BigInteger, primary_key=True),
    Column('control_test_id', BigInteger, ForeignKey('tests_controltest.id')),
    Column('task_id', BigInteger, ForeignKey('tests_task.id')),
    extend_existing=True
)

# Django-совместимые модели пользователей
class User(Base):
    __tablename__ = 'users_user'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    last_login = Column(DateTime)
    is_superuser = Column(Boolean, nullable=False, default=False)
    email = Column(String(254), nullable=False)
    is_staff = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    date_joined = Column(DateTime, nullable=False, default=datetime.utcnow)
    username = Column(String(30), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    role = Column(String(10), nullable=False)
    
    # Relationships
    course_subscriptions = relationship("CourseSubscription", back_populates="user")
    control_test_subscriptions = relationship("ControlTestSubscription", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"

# Модели курсов
class Category(Base):
    __tablename__ = 'courses_category'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(50), nullable=False)
    
    # Relationships
    courses = relationship("Course", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"

class Course(Base):
    __tablename__ = 'courses_course'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    category_id = Column(BigInteger, ForeignKey('courses_category.id'))
    
    # Relationships
    category = relationship("Category", back_populates="courses")
    chapters = relationship("Chapter", back_populates="course")
    subscriptions = relationship("CourseSubscription", back_populates="course")

    def __repr__(self):
        return f"<Course {self.title}>"

class Chapter(Base):
    __tablename__ = 'courses_chapter'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    title = Column(String(100), nullable=False)
    course_id = Column(BigInteger, ForeignKey('courses_course.id'), nullable=False)
    
    # Relationships
    course = relationship("Course", back_populates="chapters")
    content = relationship("Content", back_populates="chapter", uselist=False)
    test = relationship("Test", back_populates="chapter", uselist=False)
    chapter_progresses = relationship("ChapterProgress", back_populates="chapter")

    def __repr__(self):
        return f"<Chapter {self.title}>"

class Content(Base):
    __tablename__ = 'courses_content'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    text = Column(Text)
    video = Column(String(100))
    files = Column(String(100))
    chapter_id = Column(BigInteger, ForeignKey('courses_chapter.id'), nullable=False, unique=True)
    
    # Relationships
    chapter = relationship("Chapter", back_populates="content")

    def __repr__(self):
        return f"<Content for chapter {self.chapter_id}>"

# Модели тестирования
class Task(Base):
    __tablename__ = 'tests_task'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    question = Column(Text, nullable=False)
    is_text_input = Column(Boolean, nullable=False)
    is_multiple_choice = Column(Boolean, nullable=False)
    is_compiler = Column(Boolean, nullable=False)
    point = Column(Integer, nullable=False, default=1)
    
    # Relationships
    answers = relationship("Answer", back_populates="task")
    tests = relationship("Test", secondary=test_tasks, back_populates="tasks")
    control_tests = relationship("ControlTest", secondary=control_test_tasks, back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.question[:50]}>"

class Answer(Base):
    __tablename__ = 'tests_answer'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    task_id = Column(BigInteger, ForeignKey('tests_task.id'), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="answers")

    def __repr__(self):
        return f"<Answer {self.text[:30]}>"

class Test(Base):
    __tablename__ = 'tests_test'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    chapter_id = Column(BigInteger, ForeignKey('courses_chapter.id'), nullable=False, unique=True)
    
    # Relationships
    chapter = relationship("Chapter", back_populates="test")
    tasks = relationship("Task", secondary=test_tasks, back_populates="tests")

    def __repr__(self):
        return f"<Test for chapter {self.chapter_id}>"

class ControlTest(Base):
    __tablename__ = 'tests_controltest'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    title = Column(String(100), nullable=False)
    
    # Relationships
    tasks = relationship("Task", secondary=control_test_tasks, back_populates="control_tests")
    subscriptions = relationship("ControlTestSubscription", back_populates="control_test")

    def __repr__(self):
        return f"<ControlTest {self.title}>"

# Модели прогресса
class CourseSubscription(Base):
    __tablename__ = 'users_coursesubscription'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users_user.id'), nullable=False)
    course_id = Column(BigInteger, ForeignKey('courses_course.id'), nullable=False)
    # УБРАНО: enrolled_at - этого поля нет в реальной БД Django
    
    # Relationships
    user = relationship("User", back_populates="course_subscriptions")
    course = relationship("Course", back_populates="subscriptions")
    chapter_progresses = relationship("ChapterProgress", back_populates="subscription")

    def __repr__(self):
        return f"<CourseSubscription user:{self.user_id} course:{self.course_id}>"

class ChapterProgress(Base):
    __tablename__ = 'users_chapterprogress'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    subscription_id = Column(BigInteger, ForeignKey('users_coursesubscription.id'), nullable=False)
    chapter_id = Column(BigInteger, ForeignKey('courses_chapter.id'), nullable=False)
    is_completed = Column(Boolean, nullable=False, default=False)
    
    
    # Relationships
    subscription = relationship("CourseSubscription", back_populates="chapter_progresses")
    chapter = relationship("Chapter", back_populates="chapter_progresses")
    task_progresses = relationship("TaskProgress", back_populates="chapter_progress")

    def __repr__(self):
        return f"<ChapterProgress chapter:{self.chapter_id} completed:{self.is_completed}>"

class TaskProgress(Base):
    __tablename__ = 'users_taskprogress'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    chapter_progress_id = Column(BigInteger, ForeignKey('users_chapterprogress.id'), nullable=False)
    test_task_id = Column(BigInteger, ForeignKey('tests_testtask.id'), nullable=False)
    
    
    # Relationships
    chapter_progress = relationship("ChapterProgress", back_populates="task_progresses")

    def __repr__(self):
        return f"<TaskProgress test_task:{self.test_task_id}>"

class ControlTestSubscription(Base):
    __tablename__ = 'users_controltestsubscription'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users_user.id'), nullable=False)
    control_test_id = Column(BigInteger, ForeignKey('tests_controltest.id'), nullable=False)
    result = Column(Integer, nullable=False, default=0)
    is_completed = Column(Boolean, nullable=False, default=False)
    
    
    # Relationships
    user = relationship("User", back_populates="control_test_subscriptions")
    control_test = relationship("ControlTest", back_populates="subscriptions")

    def __repr__(self):
        return f"<ControlTestSubscription user:{self.user_id} test:{self.control_test_id}>"

# Модели групп (если нужны)
class Group(Base):
    __tablename__ = 'users_group'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    number = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<Group {self.number} ({self.year})>"

# Уведомления (если нужны) - создаем собственную таблицу так как её нет в Django
'''class Notification(Base):
    __tablename__ = 'mobile_notifications'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users_user.id'), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    related_id = Column(Integer)

    def __repr__(self):
        return f"<Notification {self.title}>"'''

# Дополнительные модели для совместимости с Django (если нужны)
class TestTask(Base):
    __tablename__ = 'tests_testtask'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    task_id = Column(BigInteger, ForeignKey('tests_task.id'), nullable=False)
    test_id = Column(BigInteger, ForeignKey('tests_test.id'), nullable=False)

class ControlTestTask(Base):
    __tablename__ = 'tests_controltesttask'
    __table_args__ = {'extend_existing': True}
    
    id = Column(BigInteger, primary_key=True)
    control_test_id = Column(BigInteger, ForeignKey('tests_controltest.id'), nullable=False)
    task_id = Column(BigInteger, ForeignKey('tests_task.id'), nullable=False)