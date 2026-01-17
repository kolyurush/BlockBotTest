import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes
from telegram.constants import ChatMemberStatus

# ========== НАСТРОЙКИ КАНАЛА ==========
BOT_TOKEN = "8532986886:AAEALnU0_ixdpmzx0eVkphcqRrY3e3Xrj04"  # Создать отдельного бота через @BotFather
CHANNEL_ID = -1001984149622  # ID вашего канала (с минусом!)
ADMIN_IDS = [555987462, 1052198330, 852296356]  # Администраторы
# ======================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('channel_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ChannelBotData:
    def __init__(self):
        self.blocked_users = set()

    def add_blocked(self, user_id):
        self.blocked_users.add(user_id)

    def is_blocked(self, user_id):
        return user_id in self.blocked_users


bot_data = ChannelBotData()


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
        f"📢 БОТ ДЛЯ КАНАЛА\n\n"
        f"ID канала: {CHANNEL_ID}\n"
        f"Администраторы:\n{admin_list}\n"
        f"Заблокировано: {len(bot_data.blocked_users)} пользователей\n\n"
        f"Функции:\n"
        f"• Автоматический бан отписавшихся\n"
        f"• Уведомления администраторам\n\n"
        f"Команды:\n"
        f"/stats - статистика\n"
        f"/check [id] - проверить пользователя\n"
        f"/unban [id] - разбанить"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    admin_list = ", ".join([str(admin_id) for admin_id in ADMIN_IDS])

    await update.message.reply_text(
        f"📊 Статистика канала:\n"
        f"• Заблокировано: {len(bot_data.blocked_users)}\n"
        f"• ID канала: {CHANNEL_ID}\n"
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
            member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
            status = member.status
        except:
            status = "не найден"

        is_blocked = bot_data.is_blocked(user_id)

        await update.message.reply_text(
            f"🔍 Проверка пользователя {user_id}:\n\n"
            f"📢 Канал: {status}\n"
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
            await context.bot.unban_chat_member(CHANNEL_ID, user_id)
            success = True
        except Exception as e:
            success = False
            logger.error(f"Ошибка разбана в канале {user_id}: {e}")

        if user_id in bot_data.blocked_users:
            bot_data.blocked_users.remove(user_id)

        response = (
            f"🔓 Результат разбана пользователя {user_id}:\n\n"
            f"📢 Канал: {'✅ Успешно' if success else '❌ Ошибка'}\n"
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
                        f"👮 Админ {admin_name} разбанил в канале:\n"
                        f"👤 Пользователь: {user_id}"
                    )
                except:
                    pass

    except ValueError:
        await update.message.reply_text("❌ Неверный ID пользователя")


async def handle_channel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик событий канала"""
    try:
        difference = update.chat_member

        # Проверяем, что это наш канал
        if difference.chat.id != CHANNEL_ID:
            return

        user = difference.new_chat_member.user
        user_id = user.id
        user_name = user.username or user.first_name
        old_status = difference.old_chat_member.status
        new_status = difference.new_chat_member.status

        logger.info(f"Канал: {user_name} ({user_id}) - {old_status} -> {new_status}")

        # Пользователь отписался от канала
        if (old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and
                new_status == ChatMemberStatus.LEFT):

            logger.info(f"🚫 Отписка от канала: {user_name}")

            try:
                # Баним в канале
                await context.bot.ban_chat_member(CHANNEL_ID, user_id)

                # Добавляем в список заблокированных
                bot_data.add_blocked(user_id)

                logger.info(f"✅ Забанен в канале: {user_name}")

                # Уведомляем админов
                await notify_admins(
                    context.bot,
                    f"📢 ОТПИСКА ОТ КАНАЛА\n\n"
                    f"👤 Пользователь: {user_name}\n"
                    f"🆔 ID: {user_id}\n"
                    f"🚫 Забанен в канале"
                )

            except Exception as e:
                logger.error(f"Ошибка бана в канале: {e}")
                await notify_admins(
                    context.bot,
                    f"⚠️ ОШИБКА БАНА В КАНАЛЕ\n\n"
                    f"👤 Пользователь: {user_name}\n"
                    f"🆔 ID: {user_id}\n"
                    f"❌ Ошибка: {str(e)[:100]}"
                )

        # Пользователь подписался на канал
        elif (old_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED] and
              new_status == ChatMemberStatus.MEMBER):

            logger.info(f"✅ Подписка на канал: {user_name}")

            await notify_admins(
                context.bot,
                f"📢 НОВАЯ ПОДПИСКА НА КАНАЛ\n\n"
                f"👤 Пользователь: {user_name}\n"
                f"🆔 ID: {user_id}"
            )

    except Exception as e:
        logger.error(f"Ошибка обработки канала: {e}")


def main():
    print("=" * 60)
    print("📢 БОТ ДЛЯ КАНАЛА")
    print("=" * 60)
    print(f"Канал ID: {CHANNEL_ID}")
    print(f"Администраторы: {ADMIN_IDS}")
    print("=" * 60)
    print("Запуск...")

    if not ADMIN_IDS:
        print("❌ ОШИБКА: Не указаны ID администраторов!")
        return

    if CHANNEL_ID > 0:
        print("⚠️ ВНИМАНИЕ: CHANNEL_ID должен быть отрицательным!")

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("check", check_user))
    application.add_handler(CommandHandler("unban", unban_user))

    # Обработчик событий канала
    application.add_handler(ChatMemberHandler(
        handle_channel_subscription,
        ChatMemberHandler.CHAT_MEMBER
    ))

    # Запускаем бота
    print("✅ Бот для канала запущен!")
    print("=" * 60)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == '__main__':
    main()