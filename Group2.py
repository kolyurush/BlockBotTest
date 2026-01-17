import logging
import pickle
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ChatMemberStatus

# ========== НАСТРОЙКИ ГРУППЫ ==========
BOT_TOKEN = "7511227141:AAH-XwA_Mzj1maCuxaLnjNmLOLYj4UaAAIo"  # Создать отдельного бота через @BotFather
GROUP_ID = -1002013382461  # ID вашей группы (с минусом!)
ADMIN_IDS = [555987462, 1052198330, 852296356]  # Администраторы
# ======================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('group_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GroupBotData:
    def __init__(self):
        self.blocked_users = set()
        self.group_members = set()  # Все участники группы
        self.data_file = "group_data.pkl"
        self.load_data()

    def add_blocked(self, user_id):
        self.blocked_users.add(user_id)
        self.save_data()

    def is_blocked(self, user_id):
        return user_id in self.blocked_users

    def add_group_member(self, user_id):
        if user_id not in self.group_members:
            self.group_members.add(user_id)
            self.save_data()
            logger.info(f"Добавлен участник: {user_id}")

    def remove_group_member(self, user_id):
        if user_id in self.group_members:
            self.group_members.remove(user_id)
            self.save_data()
            logger.info(f"Удален участник: {user_id}")

    def save_data(self):
        try:
            data = {
                'blocked_users': list(self.blocked_users),
                'group_members': list(self.group_members)
            }
            with open(self.data_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")

    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'rb') as f:
                    data = pickle.load(f)
                    self.blocked_users = set(data.get('blocked_users', []))
                    self.group_members = set(data.get('group_members', []))
                logger.info(f"Загружено {len(self.group_members)} участников")
        except Exception as e:
            logger.error(f"Ошибка загрузки: {e}")


bot_data = GroupBotData()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def notify_admins(bot, message: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text=message)
        except Exception as e:
            logger.error(f"Не удалось уведомить {admin_id}: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    admin_list = "\n".join([f"• {admin_id}" for admin_id in ADMIN_IDS])

    await update.message.reply_text(
        f"👥 БОТ ДЛЯ ГРУППЫ\n\n"
        f"ID группы: {GROUP_ID}\n"
        f"Администраторы:\n{admin_list}\n"
        f"Заблокировано: {len(bot_data.blocked_users)} пользователей\n"
        f"Участников в памяти: {len(bot_data.group_members)}\n\n"
        f"Функции:\n"
        f"• Автоматический бан вышедших участников\n"
        f"• Отслеживание вступлений/выходов\n"
        f"• Уведомления администраторам\n\n"
        f"Команды:\n"
        f"/stats - статистика\n"
        f"/check [id] - проверить пользователя\n"
        f"/unban [id] - разбанить\n"
        f"/members - список участников\n"
        f"/clear - очистить список участников"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    admin_list = ", ".join([str(admin_id) for admin_id in ADMIN_IDS])

    await update.message.reply_text(
        f"📊 Статистика группы:\n"
        f"• Заблокировано: {len(bot_data.blocked_users)}\n"
        f"• Участников в памяти: {len(bot_data.group_members)}\n"
        f"• ID группы: {GROUP_ID}\n"
        f"• Администраторы: {admin_list}"
    )


async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Использование: /check user_id")
        return

    try:
        user_id = int(context.args[0])

        try:
            member = await context.bot.get_chat_member(GROUP_ID, user_id)
            status = member.status
        except:
            status = "не найден"

        is_blocked = bot_data.is_blocked(user_id)
        in_memory = user_id in bot_data.group_members

        await update.message.reply_text(
            f"🔍 Проверка пользователя {user_id}:\n\n"
            f"👥 Группа: {status}\n"
            f"🧠 В памяти: {'✅ Да' if in_memory else '❌ Нет'}\n"
            f"🚫 В списке заблокированных: {'✅ Да' if is_blocked else '❌ Нет'}"
        )

    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя")


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Использование: /unban user_id")
        return

    try:
        user_id = int(context.args[0])

        try:
            await context.bot.unban_chat_member(GROUP_ID, user_id)
            success = True
        except Exception as e:
            success = False
            logger.error(f"Ошибка разбана в группе {user_id}: {e}")

        if user_id in bot_data.blocked_users:
            bot_data.blocked_users.remove(user_id)
            bot_data.save_data()

        response = (
            f"🔓 Результат разбана пользователя {user_id}:\n\n"
            f"👥 Группа: {'✅ Успешно' if success else '❌ Ошибка'}\n"
            f"🚫 Удален из списка заблокированных"
        )

        await update.message.reply_text(response)

        # Уведомляем других админов
        admin_name = update.effective_user.username or update.effective_user.first_name
        for admin_id in ADMIN_IDS:
            if admin_id != update.effective_user.id:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"👮 Админ {admin_name} разбанил в группе:\n"
                        f"👤 Пользователь: {user_id}"
                    )
                except:
                    pass

    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя")


async def show_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    members = list(bot_data.group_members)[:50]  # Показываем первые 50
    if not members:
        await update.message.reply_text("📭 Список участников пуст")
        return

    members_list = "\n".join([f"• {user_id}" for user_id in members])

    await update.message.reply_text(
        f"👥 Участников в памяти: {len(bot_data.group_members)}\n\n"
        f"Первые 50 ID:\n{members_list}"
    )


async def clear_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    # Сохраняем количество перед очисткой
    count = len(bot_data.group_members)

    # Очищаем список
    bot_data.group_members.clear()
    bot_data.save_data()

    await update.message.reply_text(
        f"🧹 Очищен список участников!\n"
        f"🗑️ Удалено: {count} записей"
    )


async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик новых участников группы"""
    try:
        if update.message and update.message.new_chat_members:
            for member in update.message.new_chat_members:
                if not member.is_bot:
                    user_id = member.id
                    user_name = member.username or member.first_name

                    # Добавляем в список участников
                    bot_data.add_group_member(user_id)

                    logger.info(f"✅ Новый участник: {user_name} ({user_id})")

                    # Уведомляем админов
                    await notify_admins(
                        context.bot,
                        f"👥 НОВЫЙ УЧАСТНИК ГРУППЫ\n\n"
                        f"👤 Пользователь: {user_name}\n"
                        f"🆔 ID: {user_id}\n"
                        f"👥 Всего участников: {len(bot_data.group_members)}"
                    )

    except Exception as e:
        logger.error(f"Ошибка обработки нового участника: {e}")


async def handle_left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик вышедших участников группы"""
    try:
        if update.message and update.message.left_chat_member:
            member = update.message.left_chat_member
            if not member.is_bot:
                user_id = member.id
                user_name = member.username or member.first_name

                logger.info(f"🚫 Участник вышел: {user_name} ({user_id})")

                # Удаляем из списка участников
                bot_data.remove_group_member(user_id)

                # Пытаемся забанить
                try:
                    await context.bot.ban_chat_member(GROUP_ID, user_id)
                    bot_data.add_blocked(user_id)

                    logger.info(f"✅ Забанен вышедший участник: {user_name}")

                    # Уведомляем админов
                    await notify_admins(
                        context.bot,
                        f"👥 УЧАСТНИК ВЫШЕЛ ИЗ ГРУППЫ\n\n"
                        f"👤 Пользователь: {user_name}\n"
                        f"🆔 ID: {user_id}\n"
                        f"🚫 Забанен в группе"
                    )

                except Exception as e:
                    logger.error(f"Ошибка бана {user_name}: {e}")
                    # Все равно уведомляем админов
                    await notify_admins(
                        context.bot,
                        f"👥 УЧАСТНИК ВЫШЕЛ ИЗ ГРУППЫ\n\n"
                        f"👤 Пользователь: {user_name}\n"
                        f"🆔 ID: {user_id}\n"
                        f"⚠️ Не удалось забанить: {str(e)[:100]}"
                    )

    except Exception as e:
        logger.error(f"Ошибка обработки вышедшего участника: {e}")


def main():
    print("=" * 60)
    print("👥 БОТ ДЛЯ ГРУППЫ")
    print("=" * 60)
    print(f"Группа ID: {GROUP_ID}")
    print(f"Администраторы: {ADMIN_IDS}")
    print("=" * 60)
    print("Запуск...")

    if not ADMIN_IDS:
        print("❌ ОШИБКА: Не указаны ID администраторов!")
        return

    if GROUP_ID > 0:
        print("⚠️ ВНИМАНИЕ: GROUP_ID должен быть отрицательным!")

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("check", check_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("members", show_members))
    application.add_handler(CommandHandler("clear", clear_members))

    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_chat_members
    ))
    application.add_handler(MessageHandler(
        filters.StatusUpdate.LEFT_CHAT_MEMBER,
        handle_left_chat_member
    ))

    # Запускаем бота
    print("✅ Бот для группы запущен!")
    print("=" * 60)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == '__main__':
    main()