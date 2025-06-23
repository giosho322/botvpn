from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Подключение к SQLite (файл vpnbot.db создастся сам)
engine = create_engine('sqlite:///vpnbot.db', echo=True)  # echo=True чтобы видеть SQL запросы (для дебага)

# Базовый класс для таблиц
Base = declarative_base()

# Таблица пользователей (тут всё про них)
class User(Base):
    __tablename__ = 'users'  # Название таблицы, блять
    id = Column(Integer, primary_key=True)  # ID записи (автоинкремент)
    user_id = Column(Integer, unique=True)  # Telegram ID (уникальный)
    username = Column(String)  # Юзернейм (@username)
    join_date = Column(DateTime)  # Дата регистрации
    is_active = Column(Boolean, default=False)  # Есть ли активная подписка

# Таблица подписок (кто купил, на сколько)
class Subscription(Base):
    __tablename__ = 'subscriptions'  
    id = Column(Integer, primary_key=True)  
    user_id = Column(Integer)  # ID юзера (из таблицы users)
    start_date = Column(DateTime)  # Когда подписка началась
    end_date = Column(DateTime)  # Когда подписка кончится
    payment_id = Column(String)  # ID платежа (чтобы проверять оплату)

# Создаём таблицы (если их нет – хуяк и готово)
Base.metadata.create_all(engine)

# Сессия для работы с базой (это типа подключение)
Session = sessionmaker(bind=engine)
session = Session()  # Теперь можно session.add(), session.query() и т.д.