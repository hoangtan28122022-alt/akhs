import logging
import json
import os
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Thông tin bot
BOT_TOKEN = "8492258360:AAGD8zC5GpzvWZMzKgEqF9xQ38PCixoLfEA"
GROUP_ID = -1002650132166
ADMIN_ID = 7273145338

# File lưu từ khóa lọc
FILTER_FILE = "filter_keywords.json"
MUTED_USERS_FILE = "muted_users.json"

# Danh sách từ khóa lọc
filtered_keywords = []
muted_users = {}  # {user_id: {"username": "", "first_name": "", "muted_at": ""}}

def load_keywords():
    """Tải danh sách từ khóa từ file"""
    global filtered_keywords
    try:
        if os.path.exists(FILTER_FILE):
            with open(FILTER_FILE, 'r', encoding='utf-8') as f:
                filtered_keywords = json.load(f)
        else:
            filtered_keywords = []
    except Exception as e:
        logger.error(f"Lỗi khi tải từ khóa: {e}")
        filtered_keywords = []

def save_keywords():
    """Lưu danh sách từ khóa vào file"""
    try:
        with open(FILTER_FILE, 'w', encoding='utf-8') as f:
            json.dump(filtered_keywords, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi khi lưu từ khóa: {e}")

def load_muted_users():
    """Tải danh sách user bị mute"""
    global muted_users
    try:
        if os.path.exists(MUTED_USERS_FILE):
            with open(MUTED_USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert string keys back to int
                muted_users = {int(k): v for k, v in data.items()}
        else:
            muted_users = {}
    except Exception as e:
        logger.error(f"Lỗi khi tải danh sách muted users: {e}")
        muted_users = {}

def save_muted_users():
    """Lưu danh sách user bị mute"""
    try:
        with open(MUTED_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(muted_users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi khi lưu danh sách muted users: {e}")

def add_muted_user(user_id, username, first_name, last_name=""):
    """Thêm user vào danh sách bị mute"""
    from datetime import datetime
    muted_users[user_id] = {
        "username": username or "",
        "first_name": first_name or "",
        "last_name": last_name or "",
        "muted_at": datetime.now().isoformat()
    }
    save_muted_users()
    logger.info(f"Đã thêm user {user_id} vào danh sách muted. Tổng: {len(muted_users)} users")

def remove_muted_user(user_id):
    """Xóa user khỏi danh sách bị mute"""
    if user_id in muted_users:
        del muted_users[user_id]
        save_muted_users()
        logger.info(f"Đã xóa user {user_id} khỏi danh sách muted. Còn lại: {len(muted_users)} users")

def find_user_by_identifier(identifier):
    """Tìm user ID theo username hoặc tên"""
    identifier = identifier.lower().strip()
    
    # Xóa @ nếu có
    if identifier.startswith('@'):
        identifier = identifier[1:]
    
    for user_id, user_info in muted_users.items():
        username = (user_info.get('username') or '').lower()
        first_name = (user_info.get('first_name') or '').lower()
        last_name = (user_info.get('last_name') or '').lower()
        full_name = f"{first_name} {last_name}".strip().lower()
        
        if identifier == username or identifier in first_name or identifier in last_name or identifier in full_name:
            return user_id, user_info
    
    return None, None

def check_username(username, first_name="", last_name=""):
    """Kiểm tra xem username, first name hoặc last name có chứa từ khóa bị cấm không"""
    if not username and not first_name and not last_name:
        return False
    
    text_to_check = f"{username or ''} {first_name or ''} {last_name or ''}".lower()
    
    for keyword in filtered_keywords:
        if keyword.lower() in text_to_check:
            return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /start"""
    await update.message.reply_text(
        "🤖 *Bot Lọc Tên Người Dùng*\n\n"
        "Bot này sẽ tự động xóa tin nhắn và tắt tiếng người dùng có tên chứa từ khóa bị cấm.\n\n"
        "*Lệnh dành cho Admin:*\n"
        "📝 *Quản lý từ khóa:*\n"
        "/add <từ khóa> - Thêm từ khóa lọc\n"
        "/remove <từ khóa> - Xóa từ khóa\n"
        "/list - Xem danh sách từ khóa\n"
        "/check <username> - Kiểm tra username\n\n"
        "👥 *Quản lý người dùng:*\n"
        "/unmute <@username/tên/ID> - Mở khóa 1 người\n"
        "/unmuteall - Mở khóa tất cả\n"
        "/mutedlist - Xem danh sách bị mute\n\n"
        "💡 Bạn cũng có thể dùng `/unban` và `/unbanall`",
        parse_mode='Markdown'
    )

async def add_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thêm từ khóa vào danh sách lọc"""
    user_id = update.effective_user.id
    
    # Kiểm tra quyền admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Chỉ admin mới có thể sử dụng lệnh này!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập từ khóa cần thêm!\nVí dụ: /add tukhoa")
        return
    
    keyword = " ".join(context.args)
    
    if keyword.lower() in [k.lower() for k in filtered_keywords]:
        await update.message.reply_text(f"⚠️ Từ khóa '{keyword}' đã có trong danh sách!")
        return
    
    filtered_keywords.append(keyword)
    save_keywords()
    
    await update.message.reply_text(
        f"✅ Đã thêm từ khóa lọc: *{keyword}*\n"
        f"📊 Tổng số từ khóa: {len(filtered_keywords)}",
        parse_mode='Markdown'
    )

async def remove_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa từ khóa khỏi danh sách lọc"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Chỉ admin mới có thể sử dụng lệnh này!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập từ khóa cần xóa!\nVí dụ: /remove tukhoa")
        return
    
    keyword = " ".join(context.args)
    
    # Tìm và xóa từ khóa (không phân biệt hoa thường)
    removed = False
    for i, k in enumerate(filtered_keywords):
        if k.lower() == keyword.lower():
            filtered_keywords.pop(i)
            removed = True
            break
    
    if removed:
        save_keywords()
        await update.message.reply_text(
            f"✅ Đã xóa từ khóa: *{keyword}*\n"
            f"📊 Tổng số từ khóa: {len(filtered_keywords)}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ Không tìm thấy từ khóa '{keyword}' trong danh sách!")

async def list_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị danh sách từ khóa"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Chỉ admin mới có thể sử dụng lệnh này!")
        return
    
    if not filtered_keywords:
        await update.message.reply_text("📝 Danh sách từ khóa lọc đang trống!")
        return
    
    keywords_text = "\n".join([f"{i+1}. {k}" for i, k in enumerate(filtered_keywords)])
    await update.message.reply_text(
        f"📝 *Danh sách từ khóa lọc:*\n\n{keywords_text}\n\n"
        f"📊 Tổng số: {len(filtered_keywords)}",
        parse_mode='Markdown'
    )

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kiểm tra username"""
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập username cần kiểm tra!\nVí dụ: /check username")
        return
    
    username = " ".join(context.args)
    is_filtered = check_username(username)
    
    if is_filtered:
        await update.message.reply_text(f"⚠️ Username '{username}' chứa từ khóa bị cấm!")
    else:
        await update.message.reply_text(f"✅ Username '{username}' không chứa từ khóa bị cấm.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mở khóa cho người dùng"""
    user_id = update.effective_user.id
    chat = update.message.chat
    
    # Kiểm tra quyền admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Chỉ admin mới có thể sử dụng lệnh này!")
        return
    
    # Chỉ hoạt động trong group được chỉ định
    if chat.id != GROUP_ID:
        await update.message.reply_text("❌ Lệnh này chỉ hoạt động trong group được cấu hình!")
        return
    
    target_user_id = None
    target_name = None
    
    # Kiểm tra xem có reply tin nhắn của người cần unban không
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_user_id = target_user.id
        target_name = "Người dùng"
    elif context.args:
        identifier = " ".join(context.args)
        
        # Xóa @ nếu có
        if identifier.startswith('@'):
            identifier = identifier[1:]
        
        # Thử parse như user ID
        try:
            target_user_id = int(identifier)
            target_name = "Người dùng"
        except ValueError:
            # Không phải ID, tìm theo username hoặc tên
            found_id, found_info = find_user_by_identifier(identifier)
            if found_id:
                target_user_id = found_id
                target_name = "Người dùng"
            else:
                # Không tìm thấy trong danh sách, nhưng vẫn thử unban bằng cách tìm trong group
                await update.message.reply_text(
                    f"⚠️ Không tìm thấy '{identifier}' trong danh sách lưu trữ.\n\n"
                    f"Bạn có thể thử:\n"
                    f"1️⃣ Dùng `/unbanall` hoặc `/unmuteall` để mở khóa tất cả\n"
                    f"2️⃣ Reply tin nhắn của người đó và gõ `/unmute`\n"
                    f"3️⃣ Dùng User ID: `/unmute <user_id>`"
                )
                return
    else:
        await update.message.reply_text(
            "❌ *Cách sử dụng:*\n\n"
            "1️⃣ Reply tin nhắn của người cần mở khóa và gõ `/unmute`\n"
            "2️⃣ Gõ `/unmute @username` hoặc `/unmute tên_người_dùng`\n"
            "3️⃣ Gõ `/unmute user_id`\n\n"
            "💡 Dùng `/mutedlist` để xem danh sách người bị mute.\n"
            "💡 Dùng `/unmuteall` để mở khóa tất cả.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Mở khóa người dùng (cho phép gửi tin nhắn)
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
        )
        
        # Xóa khỏi danh sách muted
        remove_muted_user(target_user_id)
        
        await update.message.reply_text(
            f"✅ Đã mở khóa cho người dùng (ID: `{target_user_id}`)\n\n"
            f"Người dùng này có thể gửi tin nhắn trở lại.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Admin đã mở khóa cho user: {target_user_id}")
        
    except Exception as e:
        logger.error(f"Lỗi khi mở khóa người dùng: {e}")
        await update.message.reply_text(f"❌ Lỗi khi mở khóa: {str(e)}")

# Alias cho unmute
unmute_user = unban_user

async def unban_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mở khóa cho tất cả người dùng bị mute"""
    user_id = update.effective_user.id
    chat = update.message.chat
    
    # Kiểm tra quyền admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Chỉ admin mới có thể sử dụng lệnh này!")
        return
    
    # Chỉ hoạt động trong group được chỉ định
    if chat.id != GROUP_ID:
        await update.message.reply_text("❌ Lệnh này chỉ hoạt động trong group được cấu hình!")
        return
    
    if not muted_users:
        await update.message.reply_text("📝 Không có ai trong danh sách bị mute!")
        return
    
    success_count = 0
    fail_count = 0
    
    await update.message.reply_text("🔄 Đang mở khóa tất cả người dùng...")
    
    for uid in list(muted_users.keys()):
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=uid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_add_web_page_previews=True,
                    can_change_info=False,
                    can_invite_users=True,
                    can_pin_messages=False
                )
            )
            remove_muted_user(uid)
            success_count += 1
        except Exception as e:
            logger.error(f"Lỗi khi mở khóa user {uid}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"✅ *Hoàn tất!*\n\n"
        f"✔️ Đã mở khóa: {success_count} người\n"
        f"❌ Thất bại: {fail_count} người",
        parse_mode='Markdown'
    )

# Alias cho unmute all
unmute_all = unban_all

async def muted_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách người dùng bị mute"""
    user_id = update.effective_user.id
    
    # Kiểm tra quyền admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Chỉ admin mới có thể sử dụng lệnh này!")
        return
    
    if not muted_users:
        await update.message.reply_text("📝 Danh sách người bị mute đang trống!")
        return
    
    message_text = "🔇 *Danh sách người dùng bị mute:*\n\n"
    
    for idx, (uid, info) in enumerate(muted_users.items(), 1):
        username = info.get('username', '')
        first_name = info.get('first_name', '')
        last_name = info.get('last_name', '')
        
        # Hiển thị thông tin an toàn (không hiển thị tên đầy đủ có spam)
        display_info = f"User {idx}"
        if username:
            display_info = f"@{username}"
        
        message_text += f"{idx}. {display_info}\n"
        message_text += f"   ID: `{uid}`\n"
        if first_name or last_name:
            message_text += f"   Tên: {first_name} {last_name}\n"
        message_text += "\n"
    
    message_text += f"📊 *Tổng số:* {len(muted_users)} người\n\n"
    message_text += "💡 Dùng `/unmute @username` hoặc `/unmute <user_id>` để mở khóa"
    
    await update.message.reply_text(message_text, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn và kiểm tra username"""
    try:
        message = update.message
        user = message.from_user
        chat = message.chat
        
        # Chỉ xử lý trong group được chỉ định
        if chat.id != GROUP_ID:
            return
        
        # Bỏ qua tin nhắn từ admin
        if user.id == ADMIN_ID:
            return
        
        username = user.username or ""
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        
        # Kiểm tra username, first name và last name
        if check_username(username, first_name, last_name):
            try:
                # Xóa tin nhắn
                await message.delete()
                
                # Tắt tiếng người dùng
                await context.bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_audios=False,
                        can_send_documents=False,
                        can_send_photos=False,
                        can_send_videos=False,
                        can_send_video_notes=False,
                        can_send_voice_notes=False,
                        can_send_polls=False
                    )
                )
                
                # Lưu vào danh sách muted
                add_muted_user(user.id, username, first_name, last_name)
                
                # Gửi thông báo - KHÔNG hiển thị tên để tránh quảng cáo trá hình
                warning_message = (
                    f"⚠️ *Cảnh báo!*\n\n"
                    f"Một người dùng đã bị tắt tiếng và tin nhắn đã bị xóa.\n\n"
                    f"*Lý do:* Tên người dùng chứa từ khóa bị cấm.\n\n"
                    f"📝 *Để được mở khóa:*\n"
                    f"1. Đổi tên người dùng (username/họ tên)\n"
                    f"2. Liên hệ với admin để được mở khóa\n\n"
                    f"Admin: [Liên hệ](tg://user?id={ADMIN_ID})"
                )
                
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=warning_message,
                    parse_mode='Markdown'
                )
                
                logger.info(f"Đã xóa tin nhắn và tắt tiếng người dùng: {user.id} - {username} {first_name} {last_name}")
                
            except Exception as e:
                logger.error(f"Lỗi khi xử lý người dùng vi phạm: {e}")
                
    except Exception as e:
        logger.error(f"Lỗi trong handle_message: {e}")

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi có thành viên mới vào group"""
    try:
        message = update.message
        chat = message.chat
        
        # Chỉ xử lý trong group được chỉ định
        if chat.id != GROUP_ID:
            return
        
        for new_member in message.new_chat_members:
            # Bỏ qua admin
            if new_member.id == ADMIN_ID:
                continue
            
            username = new_member.username or ""
            first_name = new_member.first_name or ""
            last_name = new_member.last_name or ""
            
            # Kiểm tra username, first name và last name
            if check_username(username, first_name, last_name):
                try:
                    # Tắt tiếng người dùng ngay lập tức
                    await context.bot.restrict_chat_member(
                        chat_id=chat.id,
                        user_id=new_member.id,
                        permissions=ChatPermissions(
                            can_send_messages=False,
                            can_send_audios=False,
                            can_send_documents=False,
                            can_send_photos=False,
                            can_send_videos=False,
                            can_send_video_notes=False,
                            can_send_voice_notes=False,
                            can_send_polls=False
                        )
                    )
                    
                    # Lưu vào danh sách muted
                    add_muted_user(new_member.id, username, first_name, last_name)
                    
                    # Gửi thông báo - KHÔNG hiển thị tên để tránh quảng cáo trá hình
                    warning_message = (
                        f"⚠️ *Cảnh báo!*\n\n"
                        f"Một thành viên mới đã bị tắt tiếng.\n\n"
                        f"*Lý do:* Tên người dùng chứa từ khóa bị cấm.\n\n"
                        f"📝 *Để được mở khóa:*\n"
                        f"1. Đổi tên người dùng (username/họ tên)\n"
                        f"2. Liên hệ với admin để được mở khóa\n\n"
                        f"Admin: [Liên hệ](tg://user?id={ADMIN_ID})"
                    )
                    
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=warning_message,
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"Đã tắt tiếng thành viên mới: {new_member.id} - {username} {first_name} {last_name}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý thành viên mới vi phạm: {e}")
                    
    except Exception as e:
        logger.error(f"Lỗi trong handle_new_member: {e}")

def main():
    """Chạy bot"""
    # Tải danh sách từ khóa và muted users
    load_keywords()
    load_muted_users()
    
    # Tạo application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Thêm handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_keyword))
    application.add_handler(CommandHandler("remove", remove_keyword))
    application.add_handler(CommandHandler("list", list_keywords))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("unmute", unmute_user))  # Alias cho unban
    application.add_handler(CommandHandler("unbanall", unban_all))
    application.add_handler(CommandHandler("unmuteall", unmute_all))  # Alias cho unbanall
    application.add_handler(CommandHandler("mutedlist", muted_list))
    
    # Handler cho tin nhắn
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_message
    ))
    
    # Handler cho thành viên mới
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member
    ))
    
    # Chạy bot
    logger.info("Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
