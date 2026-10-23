import os
import sys
import json
import asyncio

# ضبط الترميز ليدعم اللغة العربية والرموز التعبيرية على ويندوز
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from aiohttp import web

# تحميل متغيرات البيئة من ملف .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# تحديد النوايا (Intents)
# ⚠️ تنبيه هام: يجب تفعيل خيار Message Content Intent من Discord Developer Portal
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

# إنشاء كائن البوت مع البادئة "_"
bot = commands.Bot(command_prefix="_", intents=intents, help_command=None)

# مسار ملف حفظ الردود والأوامر المخصصة
DATA_FILE = os.path.join(os.path.dirname(__file__), "custom_data.json")


def load_data():
    """تحميل البيانات المخزنة من ملف JSON"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"خطأ في قراءة ملف البيانات: {e}")
    return {"responses": {}, "commands": {}}


def save_data(data):
    """حفظ البيانات في ملف JSON"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطأ في حفظ البيانات: {e}")


# تحميل البيانات عند بدء التشغيل
bot_data = load_data()


# آيدي مالك البوت الأساسي
DEFAULT_OWNER_ID = 768955375537750090


def check_is_owner(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم هو مالك البوت"""
    # 1. مطابقة آيدي المالك الثابت
    if user_id == DEFAULT_OWNER_ID:
        return True

    # 2. التحقق من الآيدي المحدد يدوياً في ملف .env
    env_owner = os.getenv("OWNER_ID")
    if env_owner and env_owner.strip():
        try:
            if user_id == int(env_owner.strip()):
                return True
        except ValueError:
            pass

    # 3. التحقق من مالك التطبيق التلقائي من دسكورد
    if getattr(bot, "owner_id", None) and user_id == bot.owner_id:
        return True

    if getattr(bot, "owner_ids", None) and user_id in bot.owner_ids:
        return True

    return False


def can_write(message) -> bool:
    """السماح بأمر الكتابة للمالك أو مالك السيرفر أو من يملك صلاحية إدارة الرسائل"""
    if check_is_owner(message.author.id):
        return True
    guild = getattr(message, "guild", None)
    if guild is not None:
        try:
            if guild.owner_id == message.author.id:
                return True
        except Exception:
            pass
        try:
            perms = message.channel.permissions_for(message.author)
            if perms.administrator or perms.manage_messages:
                return True
        except Exception:
            pass
    return False


def owner_only():
    """شرط للأوامر: السماح لمالك البوت فقط بتنفيذ الأمر"""
    async def predicate(ctx):
        return check_is_owner(ctx.author.id)
    return commands.check(predicate)


# -------------------------------------------------------------
# ألوان عصرية وحديثة لرسائل الإمبد (دسكورد الحديث)
# -------------------------------------------------------------
MODERN_COLORS = {
    "ازرق": 0x5865F2, "blue": 0x5865F2, "بلوربل": 0x5865F2,
    "احمر": 0xED4245, "red": 0xED4245, "قرمزي": 0x992D22,
    "اخضر": 0x57F287, "green": 0x57F287, "نيون": 0x2ECC71,
    "اصفر": 0xFEE75C, "yellow": 0xFEE75C,
    "ذهبي": 0xD4AF37, "gold": 0xD4AF37, "ملكي": 0xD4AF37,
    "بنفسجي": 0x9B59B6, "purple": 0x9B59B6,
    "سماوي": 0x00D2D3, "cyan": 0x00D2D3,
    "وردي": 0xEB459E, "pink": 0xEB459E,
    "برتقالي": 0xE67E22, "orange": 0xE67E22,
    "اسود": 0x2B2D31, "black": 0x2B2D31, "داكن": 0x1E1F22,
    "ابيض": 0xF2F3F5, "white": 0xF2F3F5,
}


def resolve_color(value: str) -> int:
    """تحديد لون الإمبد من الاسم أو كود Hex"""
    if not value:
        return 0x5865F2
    clean = str(value).strip().lower().lstrip("#")
    if clean in MODERN_COLORS:
        return MODERN_COLORS[clean]
    try:
        return int(clean, 16)
    except ValueError:
        return 0x5865F2


def make_activity(act_type: str, text: str):
    """إنشاء كائن النشاط حسب النوع والنص"""
    t = act_type.lower()
    if t in ["استماع", "listening", "listen"]:
        return discord.Activity(type=discord.ActivityType.listening, name=text)
    elif t in ["لعب", "playing", "play"]:
        return discord.Game(name=text)
    elif t in ["مشاهدة", "watching", "watch"]:
        return discord.Activity(type=discord.ActivityType.watching, name=text)
    elif t in ["بث", "streaming", "stream"]:
        return discord.Streaming(name=text, url="https://twitch.tv/discord")
    else:
        # الحالة المخصصة (Custom Status): تظهر كنص فقط دون كلمات مسبقة
        return discord.CustomActivity(name=text)


@bot.event
async def on_ready():
    """الحدث الذي يعمل عند تسجيل دخول البوت بنجاح"""
    # جلب معلومات المالك تلقائياً من تطبيق دسكورد
    try:
        app_info = await bot.application_info()
        if app_info.team:
            bot.owner_ids = {m.id for m in app_info.team.members}
            print(f" 👑 تم التعرف على مالكي البوت (فريق): {bot.owner_ids}")
        else:
            bot.owner_id = app_info.owner.id
            print(f" 👑 تم التعرف على مالك البوت تلقائياً: {app_info.owner.name} (ID: {app_info.owner.id})")
    except Exception as e:
        print(f" ⚠️ تعذر جلب معلومات المالك تلقائياً: {e}")

    manual_owner = os.getenv("OWNER_ID")
    if manual_owner and manual_owner.strip():
        print(f" 📌 تم تفعيل مالك يدوي من .env: {manual_owner.strip()}")

    print("=" * 55)
    print(f" ✅ تم تسجيل الدخول بنجاح كـ: {bot.user.name} ({bot.user.id})")
    print(f" 📌 البادئة المستخدمة: _")
    print(f" 👑 آيدي المالك المعتمد: {DEFAULT_OWNER_ID}")
    print(" 🔒 وضع الحماية: البوت مخصص لمالك البوت فقط!")
    print(" 🚀 البوت جاهز لاستقبال الأوامر!")
    print("=" * 55)

    # مزامنة أوامر السلاش الحديثة (/embed)
    try:
        synced = await bot.tree.sync()
        print(f" ⚡ تم مزامنة {len(synced)} أمر سلاش مع دسكورد بنجاح!")
    except Exception as e:
        print(f" ⚠️ تعذر مزامنة أوامر السلاش: {e}")

    # تعيين حالة البوت إلى awhara (أو الحالة المخزنة سابقاً)
    saved_status = bot_data.get("status", {"type": "custom", "text": "awhara"})
    act_type = saved_status.get("type", "custom")
    act_text = saved_status.get("text", "awhara")
    activity = make_activity(act_type, act_text)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f" 🎮 تم ضبط حالة البوت على: {act_text} ({act_type})")


@bot.event
async def on_message(message):
    """معالجة جميع الرسائل الواردة"""
    # تجاهل رسائل البوتات
    if message.author.bot:
        return

    content = message.content.strip()

    # ---------------------------------------------------------
    # 1. أمر _اكتب الأساسي (يكتب النص ويحذف رسالة المستخدم فوراً)
    # ---------------------------------------------------------
    # قائمة المشغلات للكتابة (تقبل أي نص بعد الأمر، مع أو بدون مسافة)
    write_triggers = ["_اكتب", "_قول", "_say", "_echo"]
    matched_trigger = None
    for trg in write_triggers:
        if content.lower().startswith(trg):
            # استخراج النص المتبقي بعد اسم الأمر مباشرةً
            matched_trigger = trg
            break

    if matched_trigger:
        # حصر أمر _اكتب على مالك البوت فقط (تجاهل تام لأي شخص آخر)
        if not can_write(message):
            return

        text = content[len(matched_trigger):].strip()

        # 1. محاولة حذف رسالة المرسل فوراً
        try:
            await message.delete()
        except discord.Forbidden:
            print("⚠️ تنبيه: البوت لا يمتلك صلاحية Manage Messages في هذه القناة لحذف رسالة المستخدم.")
        except Exception:
            pass

        # 2. إذا لم يكتب المستخدم نصاً بعد الأمر
        if not text:
            try:
                temp = await message.channel.send(
                    f"❌ **يرجى كتابة النص بعد الأمر!**\nمثال: `{matched_trigger} مرحباً بكم جميعاً!`"
                )
                await asyncio.sleep(4)
                await temp.delete()
            except Exception:
                pass
            return

        # 3. إرسال النص
        try:
            await message.channel.send(text)
        except Exception as e:
            print(f"❌ خطأ أثناء إرسال الرسالة: {e}")
        return

    # ---------------------------------------------------------
    # 2. فحص الردود التلقائية المبرمجة
    # ---------------------------------------------------------
    content_lower = content.lower()
    responses = bot_data.get("responses", {})
    if content_lower in responses:
        await message.channel.send(responses[content_lower])
        return

    # ---------------------------------------------------------
    # 3. فحص الأوامر المخصصة المبرمجة مع البادئة "_"
    # ---------------------------------------------------------
    if content.startswith("_"):
        parts = content[1:].strip().split(maxsplit=1)
        if parts:
            cmd_name = parts[0].lower()
            custom_cmds = bot_data.get("commands", {})
            if cmd_name in custom_cmds:
                await message.channel.send(custom_cmds[cmd_name])
                return

    # ---------------------------------------------------------
    # 4. معالجة باقي أوامر البوت القياسية
    # ---------------------------------------------------------
    await bot.process_commands(message)


# -------------------------------------------------------------
# أوامر برمجة وإدارة البوت (مخصصة لمالك البوت فقط)
# -------------------------------------------------------------
@bot.command(name="المالك", aliases=["owner"])
@owner_only()
async def owner_command(ctx):
    """التحقق من هوية مالك البوت المعترف به"""
    await ctx.send(f"👑 مرحباً يا مالك البوت! معترف بك رسمياً: **{ctx.author.name}** (ID: `{ctx.author.id}`)")


@bot.command(name="حالة", aliases=["تغيير_الحالة", "status"])
@owner_only()
async def change_status(ctx, *, args: str = None):
    """
    تغيير حالة البوت من الشات (خاص بالمالك فقط).
    الاستخدام:
    • _حالة awhara                  -> تجعل الحالة مخصصة: awhara
    • _حالة استماع awhara          -> تجعل الحالة: يستمع إلى awhara
    • _حالة لعب awhara             -> تجعل الحالة: يلعب awhara
    • _حالة مشاهدة awhara          -> تجعل الحالة: يشاهد awhara
    """
    if not args or not args.strip():
        curr = bot_data.get("status", {"type": "custom", "text": "awhara"})
        await ctx.send(
            f"ℹ️ الحالة الحالية للبوت: **{curr.get('text')}** (`{curr.get('type')}`)\n\n"
            "لتغيير الحالة يمكنك استخدام:\n"
            "• `_حالة awhara` (حالة مخصصة)\n"
            "• `_حالة استماع awhara` (Listening)\n"
            "• `_حالة لعب awhara` (Playing)\n"
            "• `_حالة مشاهدة awhara` (Watching)"
        )
        return

    parts = args.strip().split(maxsplit=1)
    first_word = parts[0].lower()
    known_types = {
        "استماع": "listening", "listening": "listening",
        "لعب": "playing", "playing": "playing",
        "مشاهدة": "watching", "watching": "watching",
        "بث": "streaming", "streaming": "streaming",
        "مخصص": "custom", "custom": "custom"
    }

    if first_word in known_types and len(parts) > 1:
        act_type = known_types[first_word]
        act_text = parts[1].strip()
    else:
        act_type = "custom"
        act_text = args.strip()

    activity = make_activity(act_type, act_text)
    await bot.change_presence(status=discord.Status.online, activity=activity)

    bot_data["status"] = {"type": act_type, "text": act_text}
    save_data(bot_data)

    type_arabic = {
        "custom": "حالة مخصصة",
        "listening": "يستمع إلى",
        "playing": "يلعب",
        "watching": "يشاهد",
        "streaming": "بث مباشر"
    }.get(act_type, act_type)

    await ctx.send(f"✅ تم تغيير حالة البوت بنجاح إلى: **{act_text}** ({type_arabic})")


@bot.command(name="اضف_رد", aliases=["تعلم", "add_response"])
@owner_only()
async def add_response(ctx, *, args: str = None):
    """
    برمجة رد تلقائي للبوت من الشات (للمالك فقط).
    الاستخدام: _اضف_رد الكلمة = الرد
    مثال: _اضف_رد السلام عليكم = وعليكم السلام ورحمة الله وبركاته!
    """
    if not args or "=" not in args:
        await ctx.send("❌ الصيغة غير صحيحة. الاستخدام:\n`_اضف_رد الكلمة = الرد المطلوب`\nمثال: `_اضف_رد هلو = أهلاً وسهلاً بك!`")
        return

    trigger, response = args.split("=", 1)
    trigger = trigger.strip().lower()
    response = response.strip()

    if not trigger or not response:
        await ctx.send("❌ الكلمة أو الرد لا يمكن أن يكون فارغاً.")
        return

    bot_data.setdefault("responses", {})[trigger] = response
    save_data(bot_data)
    await ctx.send(f"✅ تم بنجاح! الآن عندما يكتب أحد `{trigger}` سيرد البوت:\n> {response}")


@bot.command(name="حذف_رد", aliases=["delete_response"])
@owner_only()
async def delete_response(ctx, *, trigger: str = None):
    """
    حذف رد تلقائي مبرمج (للمالك فقط).
    الاستخدام: _حذف_رد الكلمة
    """
    if not trigger:
        await ctx.send("❌ يرجى تحديد الكلمة المراد حذف ردها: `_حذف_رد الكلمة`")
        return

    trigger = trigger.strip().lower()
    responses = bot_data.get("responses", {})
    if trigger in responses:
        del responses[trigger]
        save_data(bot_data)
        await ctx.send(f"🗑️ تم حذف الرد التلقائي للكلمة: `{trigger}`")
    else:
        await ctx.send(f"⚠️ لم يتم العثور على رد مسجل للكلمة: `{trigger}`")


@bot.command(name="الردود", aliases=["قائمة_الردود", "list_responses"])
@owner_only()
async def list_responses(ctx):
    """عرض جميع الردود التلقائية المبرمجة حالياً (للمالك فقط)"""
    responses = bot_data.get("responses", {})
    if not responses:
        await ctx.send("ℹ️ لا توجد ردود تلقائية مبرمجة حالياً.\nيمكنك إضافة رد عبر: `_اضف_رد الكلمة = الرد`")
        return

    lines = [f"• `{trig}` ⬅️ {resp}" for trig, resp in responses.items()]
    text = "📋 **قائمة الردود التلقائية المبرمجة:**\n" + "\n".join(lines)
    await ctx.send(text[:2000])


@bot.command(name="اضف_امر", aliases=["add_command"])
@owner_only()
async def add_command(ctx, cmd_name: str = None, *, response: str = None):
    """
    برمجة أمر جديد خاص بالبادئة _ من خلال الشات (للمالك فقط).
    الاستخدام: _اضف_امر اسم_الامر الرد
    مثال: _اضف_امر قوانين الرجاء احترام الجميع وعدم السب!
    """
    if not cmd_name or not response:
        await ctx.send("❌ الاستخدام:\n`_اضف_امر <اسم_الامر> <الرد>`\nمثال: `_اضف_امر قوانين يمنع الإعلانات في السيرفر`")
        return

    cmd_name = cmd_name.strip().lstrip("_").lower()
    built_in = ["اكتب", "قول", "say", "echo", "امبد", "المالك", "حالة", "تغيير_الحالة", "status", "اضف_رد", "حذف_رد", "الردود", "اضف_امر", "حذف_امر", "الاوامر_المخصصة", "مساعدة", "اوامر"]
    if cmd_name in built_in:
        await ctx.send("⚠️ لا يمكنك استبدال هذا الأمر لأنه أمر نظام أساسي.")
        return

    bot_data.setdefault("commands", {})[cmd_name] = response.strip()
    save_data(bot_data)
    await ctx.send(f"✅ تم إنشاء الأمر بنجاح! الآن عند كتابة `_{cmd_name}` سيرد البوت بـ:\n> {response}")


@bot.command(name="حذف_امر", aliases=["delete_command"])
@owner_only()
async def delete_command(ctx, cmd_name: str = None):
    """
    حذف أمر مخصص تم برمجته (للمالك فقط).
    الاستخدام: _حذف_امر اسم_الامر
    """
    if not cmd_name:
        await ctx.send("❌ يرجى كتابة اسم الأمر المراد حذفه: `_حذف_امر اسم_الامر`")
        return

    cmd_name = cmd_name.strip().lstrip("_").lower()
    custom_cmds = bot_data.get("commands", {})
    if cmd_name in custom_cmds:
        del custom_cmds[cmd_name]
        save_data(bot_data)
        await ctx.send(f"🗑️ تم حذف الأمر `_{cmd_name}` بنجاح.")
    else:
        await ctx.send(f"⚠️ الأمر `_{cmd_name}` غير موجود.")


@bot.command(name="الاوامر_المخصصة", aliases=["custom_commands"])
@owner_only()
async def list_custom_commands(ctx):
    """عرض قائمة الأوامر المخصصة المبرمجة (للمالك فقط)"""
    custom_cmds = bot_data.get("commands", {})
    if not custom_cmds:
        await ctx.send("ℹ️ لا توجد أوامر مخصصة مسجلة حالياً.\nيمكنك إنشاء أمر جديد عبر: `_اضف_امر <اسم> <الرد>`")
        return

    lines = [f"• `_{cmd}` ⬅️ {resp}" for cmd, resp in custom_cmds.items()]
    text = "⚡ **قائمة الأوامر المخصصة المبرمجة:**\n" + "\n".join(lines)
    await ctx.send(text[:2000])


# -------------------------------------------------------------
# قائمة المساعدة (للمالك فقط)
# -------------------------------------------------------------
@bot.command(name="مساعدة", aliases=["اوامر", "help"])
@owner_only()
async def help_command(ctx):
    """عرض قائمة بجميع الأوامر وطريقة استخدامها"""
    help_text = (
        "🤖 **دليل أوامر البوت (خاص بالمالك):**\n\n"
        "👑 **التحقق من المالك:**\n"
        "• `_المالك`: للتأكد من أن البوت معترف بحسابك كمالك رسمي.\n\n"
        "🎮 **تغيير حالة البوت:**\n"
        "• `_حالة <النص>`: تعيين حالة مخصصة للبوت (مثال: `_حالة awhara`).\n"
        "• خيارات أخرى: `_حالة استماع <النص>` أو `_حالة لعب <النص>` أو `_حالة مشاهدة <النص>`.\n\n"
        "📝 **أمر الكتابة الأساسي:**\n"
        "• `_اكتب <النص>`: يكتب البوت النص المحدد ويحذف رسالتك فوراً ليبدو كأنه هو المتحدث.\n"
        "*(يمكنك أيضاً استخدام: `_قول` أو `_say`)*\n\n"
        "🎨 **بطاقات الإيمبد الحديثة:**\n"
        "• `_امبد <النص>`: إرسال النص داخل بطاقة Embed أنيقة.\n"
        "• `_امبد --title <العنوان> --color <اللون> <النص>`: بطاقة بعنوان ولون مخصصين.\n"
        "• `/embed`: أمر السلاش الحديث لنفس الغرض (عنوان + نص + لون + تذييل).\n"
        "**الألوان:** ازرق، احمر، اخضر، اصفر، ذهبي، بنفسجي، سماوي، وردي، برتقالي، اسود، ابيض أو كود hex.\n\n"
        "🛠️ **برمجة الردود التلقائية من الشات:**\n"
        "• `_اضف_رد <الكلمة> = <الرد>`: جعل البوت يرد تلقائياً عند كتابة كلمة معينة في الشات.\n"
        "• `_حذف_رد <الكلمة>`: حذف الرد التلقائي المحدد.\n"
        "• `_الردود`: استعراض قائمة الردود المبرمجة.\n\n"
        "⚡ **برمجة أوامر مخصصة من الشات:**\n"
        "• `_اضف_امر <اسم_الأمر> <الرد>`: إنشاء أمر جديد يبدأ بـ `_`.\n"
        "• `_حذف_امر <اسم_الأمر>`: حذف أمر مخصص.\n"
        "• `_الاوامر_المخصصة`: استعراض الأوامر المخصصة المبرمجة.\n\n"
        "📌 *البوت محمي ومخصص لمالك البوت فقط، ولن يستجيب لأي عضو آخر.*"
    )
    await ctx.send(help_text)


@bot.event
async def on_command_error(ctx, error):
    """معالجة الأخطاء وطباعتها للتصحيح"""
    # تجاهل بصمت إذا كان الأمر غير موجود أو إذا حاول عضو غير المالك استخدام الأمر
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    print(f"⚠️ خطأ أثناء تنفيذ الأمر: {error}")


# -------------------------------------------------------------
# خادم ويب خفيف لدعم الاستضافة على Render (Web Service)
# -------------------------------------------------------------
async def health_check(request):
    """فحص الصحة لخوادم Render السحابية (نص عادي)"""
    return web.Response(text="Discord Bot is Online! 🚀", content_type="text/plain")


async def start_web_server(port: int):
    """بدء خادم الويب للاستماع على المنفذ المطلوب بواسطة Render"""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f" 🌐 [Render] خادم الويب يعمل بنجاح على المنفذ: {port}")


async def main():
    # 1. التحقق من وجود التوكن
    if not TOKEN or TOKEN.strip() == "" or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("=" * 65)
        print("❌ خطأ: لم يتم وضع توكن البوت (DISCORD_TOKEN)!")
        print("يرجى وضع التوكن في ملف .env أو في إعدادات البيئة على Render.")
        print("=" * 65)
        sys.exit(1)

    # 2. تشغيل خادم الويب إذا كان البوت على Render
    port_env = os.environ.get("PORT")
    if port_env:
        try:
            port = int(port_env)
            await start_web_server(port)
        except Exception as e:
            print(f"⚠️ تحذير: فشل بدء خادم الويب: {e}")

    # 3. تشغيل البوت
    try:
        async with bot:
            await bot.start(TOKEN)
    except discord.errors.LoginFailure:
        print("=" * 65)
        print("❌ خطأ: التوكن غير صالح (Invalid Token)!")
        print("يرجى التأكد من نسخ التوكن الصحيح من Discord Developer Portal.")
        print("=" * 65)
        sys.exit(1)
    except Exception as e:
        print(f"❌ حدث خطأ أثناء تشغيل البوت: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nتم إيقاف البوت يدوياً.")
