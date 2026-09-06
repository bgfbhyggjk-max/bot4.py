import asyncio
import logging
import os
from pyrogram import Client, filters
from pyrogram.types import Message
import aiosqlite

# إعدادات البوت (التوكن الجديد مدمج هنا)
API_ID = 2040  
API_HASH = "b18441a1ff607e10a989891a5462e627"  
B
BOT_TOKEN = os.getenv("BOT_TOKEN", "1000915223:AAGYrepDPCxDSe2QuzF5wz9G2iQhzZyahWU")

ADMIN_ID = 342845021  # استبدل هذا برقم الآي دي الخاص بك (Telegram ID) لتكون مديراً للبوت

logging.basicConfig(level=logging.INFO)

app = Client("media_bot_2", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
BOT_TOKEN = os.getenv("BOT_TOKEN", "1000915223:AAGYrepDPCxDSe2QuzF5wz9G2iQhzZyahWU")
DB_NAME = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_code TEXT,
                file_id TEXT,
                file_type TEXT,
                caption TEXT,
                FOREIGN KEY(link_code) REFERENCES links(code) ON DELETE CASCADE
            )
        """)
        await db.commit()

admin_states = {}

def is_admin(user_id):
    return user_id == ADMIN_ID

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    text = message.text.split()
    
    if len(text) > 1:
        link_code = text[1]
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT file_id, file_type, caption FROM media WHERE link_code = ?", (link_code,)) as cursor:
                medias = await cursor.fetchall()
        
        if not medias:
            await message.reply("❌ هذا الرابط غير صالح أو تم حذفه.")
            return

        sent_messages = []
        for file_id, file_type, caption in medias:
            try:
                if file_type == "video":
                    m = await message.reply_video(file_id, caption=caption or "")
                elif file_type == "photo":
                    m = await message.reply_photo(file_id, caption=caption or "")
                elif file_type == "document":
                    m = await message.reply_document(file_id, caption=caption or "")
                elif file_type == "audio":
                    m = await message.reply_audio(file_id, caption=caption or "")
                else:
                    m = await message.reply_text(caption or "محتوى الرابط")
                sent_messages.append(m)
            except Exception as e:
                logging.error(f"Error sending media: {e}")

        if sent_messages:
            await asyncio.sleep(60)
            for m in sent_messages:
                try:
                    await m.delete()
                except:
                    pass
    else:
        if is_admin(message.from_user.id):
            await message.reply(
                "أهلاً بك يا مدير النظام.\n\n"
                "الأوامر المتاحة لك:\n"
                "🔹 `/addlink [اسم_الرابط]` - لإضافة مقاطع لرابط جديد (من 1 إلى 6 مقاطع).\n"
                "🔹 `/dellink [اسم_الرابط]` - لحذف رابط بشكل كامل.\n"
                "🔹 `/listlinks` - لعرض كافة الروابط الموجودة.\n"
            )
        else:
            await message.reply("أهلاً بك. هذا بوت مخصص لعرض المحتوى عبر روابط خاصة.")

@app.on_message(filters.command("addlink") & filters.private)
async def add_link_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("⚠️ الاستخدام الصحيح:\n`/addlink اسم_الرابط`")
        return
    
    link_code = args[1].strip()
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT code FROM links WHERE code = ?", (link_code,)) as cursor:
            exists = await cursor.fetchone()
        if exists:
            await message.reply(f"⚠️ الرابط `{link_code}` موجود مسبقاً.")
            return
        
        await db.execute("INSERT INTO links (code) VALUES (?)", (link_code,))
        await db.commit()
    
    admin_states[message.from_user.id] = {"action": "adding", "code": link_code, "count": 0}
    await message.reply(
        f"✅ تم إنشاء الرابط: `{link_code}`\n\n"
        "الآن أرسل المقاطع أو الصور (من 1 إلى 6 مقاطع).\n"
        "عند الانتهاء أرسل الأمر: `/done`"
    )

@app.on_message(filters.private & ~filters.command(["addlink", "dellink", "listlinks", "done", "start"]))
async def handle_media_upload(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    
    user_id = message.from_user.id
    if user_id not in admin_states or admin_states[user_id]["action"] != "adding":
        return
    
    state = admin_states[user_id]
    if state["count"] >= 6:
        await message.reply("⚠️ وصلت للحد الأقصى (6 مقاطع). أرسل `/done` للحفظ.")
        return
    
    file_id = None
    file_type = "text"
    caption = message.caption or message.text or ""
    
    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    
    link_code = state["code"]
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO media (link_code, file_id, file_type, caption) VALUES (?, ?, ?, ?)",
            (link_code, file_id, file_type, caption)
        )
        await db.commit()
    
    state["count"] += 1
    await message.reply(f"📌 تم حفظ العنصر ({state['count']}/6).\nأرسل عنصراً آخر أو `/done` للإنهاء.")

@app.on_message(filters.command("done") & filters.private)
async def done_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    
    user_id = message.from_user.id
    if user_id in admin_states:
        link_code = admin_states[user_id]["code"]
        del admin_states[user_id]
        bot_username = (await client.get_me()).username
        full_link = f"https://t.me/{bot_username}?start={link_code}"
        await message.reply(
            f"🎉 **تم حفظ الرابط بنجاح!**\n\n"
            f"🔗 رابط المشاركة:\n`{full_link}`"
        )
    else:
        await message.reply("⚠️ ليس لديك عملية إضافة نشطة.")

@app.on_message(filters.command("dellink") & filters.private)
async def delete_link_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("⚠️ الاستخدام الصحيح:\n`/dellink اسم_الرابط`")
        return
    
    link_code = args[1].strip()
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT code FROM links WHERE code = ?", (link_code,)) as cursor:
            exists = await cursor.fetchone()
        if not exists:
            await message.reply("❌ هذا الرابط غير موجود.")
            return
        
        await db.execute("DELETE FROM media WHERE link_code = ?", (link_code,))
        await db.execute("DELETE FROM links WHERE code = ?", (link_code,))
        await db.commit()
    
    await message.reply(f"🗑️ تم حذف الرابط `{link_code}`.")

@app.on_message(filters.command("listlinks") & filters.private)
async def list_links_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT code FROM links") as cursor:
            links = await cursor.fetchall()
            
    if not links:
        await message.reply("📁 لا توجد أي روابط مخزنة.")
        return
    
    bot_username = (await client.get_me()).username
    text = "📋 **قائمة الروابط الخاصة بك:**\n\n"
    for idx, (code,) in enumerate(links, 1):
        text += f"{idx}. `https://t.me/{bot_username}?start={code}`\n"
    
    await message.reply(text)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    print("Bot is running...")
    app.run()
