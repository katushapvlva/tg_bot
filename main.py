import logging
import psycopg2
import telebot
import os

# Настройка логгирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN', '6624184020:AAES-8_2r1hb9CJ0YZMeMc8dXKY6lw7OX98')

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://katusha:password@localhost:5432/tgbot')

bot = telebot.TeleBot(TOKEN)

def create_articles_table() -> None:
    """
    Создание таблицы в базе данных, если она не существует.
    """
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id SERIAL PRIMARY KEY,
            article_url TEXT NOT NULL,
            user_id INTEGER NOT NULL
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_articles_table()

@bot.message_handler(commands=['start'])
def start(message: telebot.types.Message) -> None:
    """
    Обработка команды /start.

    Аргумент:
    message - сообщение от пользователя.
    """
    bot.send_message(message.chat.id, "Привет! Я бот, который поможет не забыть прочитать статьи, найденные тобой в интернете :)\n\n"
                                      "- Чтобы я запомнил статью, достаточно передать мне ссылку на нее. К примеру https://example.com.\n\n"
                                      "- Чтобы получить случайную статью, достаточно передать мне команду /get_article.\n\n"
                                      "Но помни, отдавая статью тебе на прочтения, она больше не хранится в моей базе. Так что тебе точно нужно ее изучить!")

@bot.message_handler(commands=['get_article'])
def get_article(message: telebot.types.Message) -> None:
    """
    Обработка команды /get_article.

    Аргумент:
    message - сообщение от полльзователя.
    """
    user_id = message.from_user.id
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        # Выполнение запроса к базе данных для получения случайной статьи
        cursor.execute("SELECT article_url FROM articles WHERE user_id = %s ORDER BY RANDOM() LIMIT 1;", (user_id,))
        article = cursor.fetchone()
        if article:
            # Отправка сообщения с найденной статьей
            bot.send_message(message.chat.id, f"Вы хотели прочитать: {article[0]}\nСамое время это сделать!")
            # Удаление ссылки из базы данных после отправки пользователю
            cursor.execute("DELETE FROM articles WHERE user_id = %s AND article_url = %s;", (user_id, article[0]))
            conn.commit()
        else:
            bot.send_message(message.chat.id, "Вы пока не сохранили ни одной статьи :(\nЕсли нашли что-то стоящее, я жду!")
    except Exception as e:
        logger.error(f"Error occurred while fetching article: {e}")
    finally:
        # Закрываем соединение с базой данных
        cursor.close()
        conn.close()

# Функция для сохранения статьи в базу данных
@bot.message_handler(func=lambda message: message.text.startswith('http'))
def save_article(message: telebot.types.Message) -> None:
    """
    Сохранение ссылки на статью в базу данных.

    Аргумент:
    message - сообщение от пользователя.
    """
    user_id = message.from_user.id
    article_url = message.text

    try:
        # Подключение к базе данных
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Проверка, есть ли уже такая ссылка в базе данных
        cursor.execute("SELECT article_url FROM articles WHERE user_id = %s AND article_url = %s;", (user_id, article_url))
        existing_article = cursor.fetchone()
        if existing_article:
            bot.send_message(message.chat.id, "Упс, вы уже это сохраняли :)")
        else:
            # Если ссылка еще не сохранена, то сохраняем
            cursor.execute("INSERT INTO articles (article_url, user_id) VALUES (%s, %s);", (article_url, user_id))
            conn.commit()
            bot.send_message(message.chat.id, "Сохранил, спасибо!")
    except Exception as e:
        logger.error(f"Error occurred while saving article: {e}")
    finally:
        # Закрываем соединение с базой данных
        cursor.close()
        conn.close()

@bot.message_handler(func=lambda message: True)
def unknown(message: telebot.types.Message) -> None:
    """
    Обработка неизвестных команд.
    """
    bot.send_message(message.chat.id, "Извините, такая команда мне неизвестна.")

# Запуск бота
def main() -> None:
    """
    Запуск бота.
    """
    bot.polling()

if __name__ == '__main__':
    main()