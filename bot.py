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
from discord.ext import commands
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# تحديد النوايا (Intents)
# يجب تفعيل Message Content Intent من بوابة المطورين (Discord Developer Portal)
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


@bot.event
async def on_ready():
    """الحدث الذي يعمل عند تسجيل دخول البوت بنجاح"""
    print("=" * 50)
    print(f" تم تسجيل الدخول بنجاح كـ: {bot.user.name} ({bot.user.id})")
    print(f" البادئة المستخدمة: _")
    print(" البوت جاهز لاستقبال الأوامر!")
    print("=" * 50)
    # تعيين نشاط للبوت
    activity = discord.Activity(type=discord.ActivityType.listening, name="أمر _اكتب | _مساعدة")
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_message(message):
    """الاستماع لجميع الرسائل للردود التلقائية والأوامر"""
    # تجاهل رسائل البوتات نفسها
    if message.author.bot:
        return

    # 1. فحص الردود التلقائية المبرمجة
    content_lower = message.content.strip().lower()
    responses = bot_data.get("responses", {})
    if content_lower in responses:
        await message.channel.send(responses[content_lower])

    # 2. فحص الأوامر المخصصة المبرمجة مع البادئة "_"
    if message.content.startswith("_"):
        parts = message.content[1:].strip().split(maxsplit=1)
        if parts:
            cmd_name = parts[0].lower()
            custom_cmds = bot_data.get("commands", {})
            if cmd_name in custom_cmds:
                await message.channel.send(custom_cmds[cmd_name])

    # 3. معالجة الأوامر القياسية للبوت
    await bot.process_commands(message)


# -------------------------------------------------------------
# الأمر الأساسي: _اكتب (يكتب النص ويحذف رسالة المستخدم فوراً)
# -------------------------------------------------------------
@bot.command(name="اكتب", aliases=["قول", "say", "echo"])
async def write_command(ctx, *, text: str = None):
    """
    أمر _اكتب: يرسل النص المحمول ثم يحذف رسالة المستخدم.
    الاستخدام: _اكتب <النص المراد كتابته>
    """
    # 1. محاولة حذف رسالة المستخدم
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        # إذا لم يكن لدى البوت صلاحية Manage Messages
        warning = await ctx.send(
            "⚠️ **تنبيه:** البوت لا يمتلك صلاحية `Manage Messages` (إدارة الرسائل) في هذه القناة لحذف رسالتك الأصلية.\n"
            "يرجى إعطاء البوت رتبة تمتلك صلاحية إدارة الرسائل.",
            delete_after=7
        )
    except discord.HTTPException:
        pass

    # 2. التحقق من وجود نص
    if not text or not text.strip():
        temp_msg = await ctx.send("❌ **يرجى إدخال النص بعد الأمر!**\nمثال: `_اكتب مرحباً بكم جميعاً!`")
        await asyncio.sleep(5)
        try:
            await temp_msg.delete()
        except Exception:
            pass
        return

    # 3. إرسال النص كما هو
    await ctx.send(text)


# -------------------------------------------------------------
# أمر إضافي: _اكتب_امبد (يكتب النص داخل بطاقة Embed أنيقة ويحذف رسالة المستخدم)
# -------------------------------------------------------------
@bot.command(name="اكتب_امبد", aliases=["قول_امبد", "embed"])
async def write_embed_command(ctx, *, text: str = None):
    """
    أمر _اكتب_امبد: يرسل النص داخل بطاقة Embed ملونة ويحذف رسالتك الأصلية.
    الاستخدام: _اكتب_امبد <النص>
    """
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if not text or not text.strip():
        temp = await ctx.send("❌ يرجى إدخال نص بعد الأمر: `_اكتب_امبد مرحباً`", delete_after=5)
        return

    embed = discord.Embed(
        description=text,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


# -------------------------------------------------------------
# أوامر برمجة البوت من الشات (إضافة ردود وأوامر مخصصة)
# -------------------------------------------------------------
@bot.command(name="اضف_رد", aliases=["تعلم", "add_response"])
async def add_response(ctx, *, args: str = None):
    """
    برمجة رد تلقائي للبوت من الشات.
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
async def delete_response(ctx, *, trigger: str = None):
    """
    حذف رد تلقائي مبرمج.
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
async def list_responses(ctx):
    """عرض جميع الردود التلقائية المبرمجة حالياً"""
    responses = bot_data.get("responses", {})
    if not responses:
        await ctx.send("ℹ️ لا توجد ردود تلقائية مبرمجة حالياً. يمكنك إضافة رد عبر: `_اضف_رد الكلمة = الرد`")
        return

    lines = [f"• `{trig}` ⬅️ `{resp}`" for trig, resp in responses.items()]
    text = "\n".join(lines)
    embed = discord.Embed(
        title="📋 الردود التلقائية المبرمجة",
        description=text[:4000],
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="اضف_امر", aliases=["add_command"])
async def add_command(ctx, cmd_name: str = None, *, response: str = None):
    """
    برمجة أمر جديد خاص بالبادئة _ من خلال الشات.
    الاستخدام: _اضف_امر اسم_الامر الرد
    مثال: _اضف_امر قوانين الرجاء احترام الجميع وعدم السب!
    """
    if not cmd_name or not response:
        await ctx.send("❌ الاستخدام:\n`_اضف_امر <اسم_الامر> <الرد>`\nمثال: `_اضف_امر قوانين يمنع الإعلانات في السيرفر`")
        return

    cmd_name = cmd_name.strip().lstrip("_").lower()
    # التحقق من عدم التعارض مع الأوامر الأساسية
    built_in = ["اكتب", "اكتب_امبد", "اضف_رد", "حذف_رد", "الردود", "اضف_امر", "حذف_امر", "الاوامر_المخصصة", "مساعدة", "اوامر"]
    if cmd_name in built_in:
        await ctx.send("⚠️ لا يمكنك استبدال هذا الأمر لأنه أمر نظام أساسي.")
        return

    bot_data.setdefault("commands", {})[cmd_name] = response.strip()
    save_data(bot_data)
    await ctx.send(f"✅ تم إنشاء الأمر بنجاح! الآن عند كتابة `_{cmd_name}` سيرد البوت بـ:\n> {response}")


@bot.command(name="حذف_امر", aliases=["delete_command"])
async def delete_command(ctx, cmd_name: str = None):
    """
    حذف أمر مخصص تم برمجته.
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
async def list_custom_commands(ctx):
    """عرض قائمة الأوامر المخصصة التي تم برمجتها"""
    custom_cmds = bot_data.get("commands", {})
    if not custom_cmds:
        await ctx.send("ℹ️ لا توجد أوامر مخصصة مسجلة حالياً. يمكنك إنشاء أمر جديد عبر: `_اضف_امر <اسم> <الرد>`")
        return

    lines = [f"• `_{cmd}` ⬅️ `{resp}`" for cmd, resp in custom_cmds.items()]
    text = "\n".join(lines)
    embed = discord.Embed(
        title="⚡ الأوامر المخصصة المبرمجة",
        description=text[:4000],
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)


# -------------------------------------------------------------
# قائمة المساعدة
# -------------------------------------------------------------
@bot.command(name="مساعدة", aliases=["اوامر", "help"])
async def help_command(ctx):
    """عرض قائمة بجميع الأوامر وطريقة استخدامها"""
    embed = discord.Embed(
        title="🤖 دليل أوامر البوت",
        description="هنا تجد جميع الأوامر المتاحة في البوت وكيفية استخدامها:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="📝 أمر الكتابة الأساسي",
        value=(
            "• `_اكتب <النص>`: يكتب البوت النص المدخل ويحذف رسالتك فوراً.\n"
            "• `_اكتب_امبد <النص>`: يكتب النص داخل بطاقة ملونة ويحذف رسالتك."
        ),
        inline=False
    )
    embed.add_field(
        name="🛠️ برمجة الردود التلقائية من الشات",
        value=(
            "• `_اضف_رد <الكلمة> = <الرد>`: جعل البوت يرد تلقائياً عند كتابة كلمة معينة.\n"
            "• `_حذف_رد <الكلمة>`: حذف الرد التلقائي المحدد.\n"
            "• `_الردود`: عرض جميع الردود التلقائية المبرمجة."
        ),
        inline=False
    )
    embed.add_field(
        name="⚡ برمجة أوامر مخصصة من الشات",
        value=(
            "• `_اضف_امر <اسم_الأمر> <الرد>`: إنشاء أمر جديد يبدأ بـ `_`.\n"
            "• `_حذف_امر <اسم_الأمر>`: حذف أمر مخصص.\n"
            "• `_الاوامر_المخصصة`: عرض قائمة الأوامر المخصصة."
        ),
        inline=False
    )
    embed.set_footer(text="بادئة البوت هي _")
    await ctx.send(embed=embed)


def main():
    if not TOKEN or TOKEN.strip() == "" or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("=" * 60)
        print("❌ خطأ: لم يتم وضع توكن البوت (DISCORD_TOKEN)!")
        print("يرجى فتح ملف .env ووضع التوكن الخاص ببوتك.")
        print("مثال داخل ملف .env:")
        print("DISCORD_TOKEN=MTE5ODc2NTQzMjE...")
        print("=" * 60)
        return

    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("❌ خطأ: التوكن غير صالح! يرجى التأكد من نسخ التوكن الصحيح من Discord Developer Portal.")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء تشغيل البوت: {e}")


if __name__ == "__main__":
    main()
