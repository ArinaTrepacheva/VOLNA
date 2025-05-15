import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session

SqlAlchemyBase = orm.declarative_base()

__factory = None


def global_init(db_file):
    global __factory

    if __factory:
        print("Повторная инициализация базы данных.  Игнорируется.")  # Добавлено для отладки
        return

    if not db_file or not db_file.strip():
        raise Exception("Необходимо указать файл базы данных.")

    db_file = db_file.strip()  # Убедимся, что пробелы обрезаны
    conn_str = f'sqlite:///{db_file}?check_same_thread=False'
    print(f"Подключение к базе данных по адресу {conn_str}")

    try:
        engine = sa.create_engine(conn_str, echo=False)  # echo=True для отладки
        SqlAlchemyBase.metadata.create_all(engine)  # Создаем таблицы

        __factory = orm.sessionmaker(bind=engine)

        # noinspection PyUnresolvedReferences
        from . import __all_models  # Импорт моделей *после* создания движка

        # Проверка успешности инициализации
        if __factory is None:
            raise Exception("Ошибка инициализации sessionmaker.")

        print("База данных успешно инициализирована.")  # Добавлено для отладки

    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        raise  # Перебрасываем исключение, чтобы вызывающая сторона знала об ошибке


def create_session() -> Session:
    global __factory
    if __factory is None:
        raise Exception("База данных не инициализирована.  Вызовите global_init() перед create_session().")
    return __factory()
