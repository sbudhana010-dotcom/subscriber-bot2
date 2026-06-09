"""
Subscriber Bot - Fresh Build
"""
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from database import Database
from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
db = Database()


def pkr(amount):
    return f"Rs. {amount:,}"

def usd(amount):
    return f"${amount:.2f}"

def dual_price(pkg):
    return f"{pkr(pkg['price_pkr'])} (~{usd(pkg['price_usd'])})"

def main_menu_kb(user_id):
    is_admin = user_id in Config.ADMIN_IDS
    rows = [
        [InlineKeyboardButton("🆓 Free Subscribers", callback_data="free_menu"),
         InlineKeyboardButton("💎 Paid Subscribers", callback_data="paid_menu")],
        [InlineKeyboardButton("👥 Referral System",  callback_data="referral_menu"),
         InlineKeyboardButton("📊 My Account",       callback_data="my_account")],
        [InlineKeyboardButton("📋 Order History",    callback_data="orders"),
         InlineKeyboardButton("ℹ️ Help",             callback_data="help")],
        [InlineKeyboardButton("💱 Dollar Rate",      callback_data="dollar_rate")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_code = context.args[0] if context.args else None
    is_new = db.register_user(user.id, user.username or "", user.full_name, ref_code)

    if is_new and ref_code and ref_code.startswith("ref_"):
        try:
            referrer_id = int(ref_code.split("_")[1])
            if referrer_id != user.id:
                db.add_free_subscribers(referrer_id, Config.REFERRAL_REWARD)
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 *Mubarak!* Aapka referral join ho gaya!\n✅ *{Config.REFERRAL_REWARD} Free Subscribers* add ho gaye!",
                    parse_mode='Markdown'
                )
        except Exception:
            pass

    ud = db.get_user(user.id)
    text = (
        f"🌟 *Welcome, {user.first_name}!*\n\n"
        f"🤖 *Subscriber Bot* mein khush amdeed!\n\n"
        f"📊 *Aapka Account:*\n"
        f"├ 🆓 Free Subs: `{ud['free_subs']}`\n"
        f"├ 💎 Paid Subs: `{ud['paid_subs']}`\n"
        f"└ 👥 Referrals: `{ud['referrals']}`\n\n"
        f"👇 Option select karo:"
    )
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=main_menu_kb(user.id))


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = db.get_user(query.from_user.id)
    text = (
        f"🌟 *Main Menu*\n\n"
        f"├ 🆓 Free: `{ud['free_subs']}`\n"
        f"├ 💎 Paid: `{ud['paid_subs']}`\n"
        f"└ 👥 Referrals: `{ud['referrals']}`\n\n"
        f"👇 Option select karo:"
    )
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu_kb(query.from_user.id))


async def dollar_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        f"💱 *DOLLAR RATE*\n\n"
        f"🇺🇸 1 USD = `Rs. {Config.USD_TO_PKR}`\n\n"
        f"Tamam packages PKR aur USD dono mein hain.\n"
        f"USDT payment ke liye dollar amount bhejein."
    )
    await query.edit_message_text(text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))


async def free_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = db.get_user(query.from_user.id)
    channels = Config.TASK_CHANNELS
    task_btn_text = f"✅ {len(channels)} Channels Join → {Config.TASK_REWARD} Free Subs" if channels else "⏳ Channel Task Coming Soon"
    text = (
        f"🆓 *FREE SUBSCRIBER SYSTEM*\n\n"
        f"*Method 1 — Channel Task:*\n"
        f"├ {Config.TASK_REQUIRED} channels join karo\n"
        f"└ *{Config.TASK_REWARD} Free Subscribers* milenge!\n\n"
        f"*Method 2 — Referral:*\n"
        f"├ Apna link share karo\n"
        f"└ Har user = *{Config.REFERRAL_REWARD} Free Subs*\n\n"
        f"📊 Tumhare paas: `{ud['free_subs']}` free subs"
    )
    rows = [
        [InlineKeyboardButton(task_btn_text, callback_data="task_channels" if channels else "free_menu")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="get_referral")],
        [InlineKeyboardButton("📤 Free Subs Use Karo", callback_data="use_free_subs")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def task_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = Config.TASK_CHANNELS
    if not channels:
        await query.edit_message_text("⏳ Coming soon!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="free_menu")]]))
        return

    text = f"📋 *CHANNEL TASK*\n\n🎯 Yeh {len(channels)} channels join karo:\n\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. @{ch['username']} — *{ch['name']}*\n"
    text += f"\n✅ Sab join karo phir Check button dabao!"

    rows = [[InlineKeyboardButton(f"📢 {ch['name']}", url=f"https://t.me/{ch['username']}")] for ch in channels]
    rows.append([InlineKeyboardButton("✅ Check Kar Lo!", callback_data="check_channels")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="free_menu")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def check_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Check ho raha hai...")
    user_id = query.from_user.id
    not_joined = []

    for ch in Config.TASK_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch["id"], user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)

    if not_joined:
        missing = "\n".join([f"❌ @{ch['username']}" for ch in not_joined])
        text = f"⚠️ *Yeh channels join nahi kiye:*\n\n{missing}\n\nSab join karke dobara check karo!"
        await query.edit_message_text(text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="task_channels")]]))
        return

    task = db.get_task_status(user_id)
    if task.get("completed", 0) > 0:
        text = "✅ Aap yeh task pehle kar chuke hain!\n\nReferral se aur earn karo! 🔗"
    else:
        db.complete_task(user_id)
        text = f"🎉 *TASK COMPLETE!*\n\n✅ Sab channels join!\n🎁 *{Config.TASK_REWARD} Free Subscribers* add!"
    await query.edit_message_text(text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="free_menu")]]))


async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ud = db.get_user(user_id)
    ref_link = f"https://t.me/{Config.BOT_USERNAME}?start=ref_{user_id}"
    text = (
        f"🔗 *REFERRAL SYSTEM*\n\n"
        f"Har referral = *{Config.REFERRAL_REWARD} Free Subs*\n\n"
        f"📊 *Stats:*\n"
        f"├ 👥 Referrals: `{ud['referrals']}`\n"
        f"└ 🆓 Earned: `{ud['free_subs']}`\n\n"
        f"🔗 *Tumhara Link:*\n`{ref_link}`"
    )
    rows = [
        [InlineKeyboardButton("📤 WhatsApp", url=f"https://wa.me/?text=Free+subscribers+lo!+{ref_link}"),
         InlineKeyboardButton("📢 Telegram", url=f"https://t.me/share/url?url={ref_link}")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def get_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ref_link = f"https://t.me/{Config.BOT_USERNAME}?start=ref_{user_id}"
    text = (
        f"🔗 *TUMHARA REFERRAL LINK*\n\n"
        f"`{ref_link}`\n\n"
        f"💰 Har referral: *{Config.REFERRAL_REWARD} Free Subs*\n\n"
        f"Share karo aur earn karo! 🚀"
    )
    rows = [
        [InlineKeyboardButton("📤 WhatsApp", url=f"https://wa.me/?text=Free+subscribers!+{ref_link}"),
         InlineKeyboardButton("📢 Telegram", url=f"https://t.me/share/url?url={ref_link}")],
        [InlineKeyboardButton("🔙 Back", callback_data="free_menu")],
    ]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    top = db.get_leaderboard()
    medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣']
    text = "🏆 *TOP REFERRERS*\n\n"
    for i, u in enumerate(top):
        text += f"{medals[i]} *{(u['full_name'] or 'User')[:15]}* — `{u['referrals']}` referrals\n"
    text += "\n💪 Zyada refer karo, aage aao!"
    await query.edit_message_text(text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="referral_menu")]]))


async def use_free_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = db.get_user(query.from_user.id)
    text = (
        f"📤 *FREE SUBS USE KARO*\n\n"
        f"Tumhare paas: *{ud['free_subs']} free subs*\n\n"
        f"Admin se contact karo:\n"
        f"• Channel/group link bhejo\n"
        f"• Kitne subs chahiye batao\n\n"
        f"Admin: @{Config.ADMIN_USERNAME}"
    )
    rows = [
        [InlineKeyboardButton("💬 Admin", url=f"https://t.me/{Config.ADMIN_USERNAME}")],
        [InlineKeyboardButton("🔙 Back", callback_data="free_menu")],
    ]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def paid_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    packages = db.get_packages()
    text = (
        f"💎 *PAID PACKAGES*\n\n"
        f"✅ Real Subscribers\n✅ Fast Delivery\n"
        f"💱 Rate: 1 USD = Rs. {Config.USD_TO_PKR}\n\n"
    )
    rows = []
    for pkg in packages:
        text += (
            f"*{pkg['name']}*\n"
            f"├ 👥 {pkg['subs']:,} Subscribers\n"
            f"├ 💰 {dual_price(pkg)}\n"
            f"└ ⚡ {pkg['delivery']}\n\n"
        )
        rows.append([InlineKeyboardButton(
            f"🛒 {pkg['name']} — {pkr(pkg['price_pkr'])}",
            callback_data=f"buy_pkg_{pkg['id']}"
        )])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def buy_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pkg_id = int(query.data.split("_")[-1])
    pkg = db.get_package(pkg_id)
    text = (
        f"🛒 *ORDER CONFIRM*\n\n"
        f"📦 {pkg['name']}\n"
        f"👥 {pkg['subs']:,} Subscribers\n"
        f"💰 {dual_price(pkg)}\n"
        f"⚡ {pkg['delivery']}\n\n"
        f"💳 *Payment Method:*"
    )
    rows = [
        [InlineKeyboardButton("📱 EasyPaisa/JazzCash", callback_data=f"pay_pkr_{pkg_id}"),
         InlineKeyboardButton("🟡 USDT TRC20", callback_data=f"pay_usdt_{pkg_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="paid_menu")],
    ]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def pay_pkr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pkg_id = int(query.data.split("_")[-1])
    pkg = db.get_package(pkg_id)
    context.user_data['pending_pkg'] = pkg_id
    context.user_data['pending_method'] = 'easypaisa'
    text = (
        f"📱 *EASYPAISA / JAZZCASH*\n\n"
        f"💰 Amount: `{pkr(pkg['price_pkr'])}`\n\n"
        f"🟢 EasyPaisa: `{Config.EASYPAISA_NUM}`\n"
        f"   Name: *{Config.EASYPAISA_NAME}*\n\n"
        f"🔵 JazzCash: `{Config.JAZZCASH_NUM}`\n"
        f"   Name: *{Config.JAZZCASH_NAME}*\n\n"
        f"📸 Payment karo aur screenshot bhejo 👇"
    )
    await query.edit_message_text(text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="paid_menu")]]))


async def pay_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pkg_id = int(query.data.split("_")[-1])
    pkg = db.get_package(pkg_id)
    context.user_data['pending_pkg'] = pkg_id
    context.user_data['pending_method'] = 'usdt'
    text = (
        f"🟡 *USDT TRC20*\n\n"
        f"💰 Amount: `{usd(pkg['price_usd'])}` USDT\n\n"
        f"📍 Wallet:\n`{Config.USDT_TRC20}`\n\n"
        f"⚠️ *Sirf TRC20 network!*\n\n"
        f"📸 Transaction screenshot bhejo 👇"
    )
    await query.edit_message_text(text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="paid_menu")]]))


async def handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_pkg' not in context.user_data:
        return
    user = update.effective_user
    pkg_id = context.user_data['pending_pkg']
    pay_method = context.user_data.get('pending_method', 'easypaisa')
    pkg = db.get_package(pkg_id)
    order_id = db.create_order(user.id, pkg_id, pay_method)

    method_label = "USDT TRC20" if pay_method == 'usdt' else "EasyPaisa/JazzCash"
    price_label = usd(pkg['price_usd']) if pay_method == 'usdt' else pkr(pkg['price_pkr'])

    for admin_id in Config.ADMIN_IDS:
        try:
            await context.bot.forward_message(admin_id, update.effective_chat.id, update.message.message_id)
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💰 *NEW ORDER #{order_id}*\n\n"
                    f"👤 {user.full_name} (@{user.username or 'N/A'})\n"
                    f"📦 {pkg['name']} — {pkg['subs']:,} subs\n"
                    f"💳 {method_label}: {price_label}"
                ),
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_order_{order_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_order_{order_id}")
                ]])
            )
        except Exception as e:
            logger.error(f"Admin notify error: {e}")

    await update.message.reply_text(
        f"✅ *Screenshot mil gaya!*\n\nOrder `#{order_id}` process ho raha hai.\nApprove hone par notification aayega!",
        parse_mode='Markdown'
    )
    context.user_data.pop('pending_pkg', None)
    context.user_data.pop('pending_method', None)


async def my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
    else:
        user_id = update.effective_user.id

    ud = db.get_user(user_id)
    ref_link = f"https://t.me/{Config.BOT_USERNAME}?start=ref_{user_id}"
    text = (
        f"👤 *MY ACCOUNT*\n\n"
        f"📛 {ud['full_name']}\n"
        f"🆔 `{user_id}`\n"
        f"📅 Joined: {ud['joined_date']}\n\n"
        f"├ 🆓 Free Subs: `{ud['free_subs']}`\n"
        f"├ 💎 Paid Subs: `{ud['paid_subs']}`\n"
        f"├ 👥 Referrals: `{ud['referrals']}`\n"
        f"└ 🏆 Total: `{ud['total_earned']}`\n\n"
        f"🔗 `{ref_link}`"
    )
    rows = [
        [InlineKeyboardButton("📋 Orders", callback_data="orders")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    kb = InlineKeyboardMarkup(rows)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)


async def orders_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    orders = db.get_user_orders(query.from_user.id)
    if not orders:
        text = "📋 *ORDER HISTORY*\n\nKoi order nahi abhi tak!"
    else:
        text = "📋 *ORDER HISTORY*\n\n"
        for o in orders[-10:]:
            emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(o['status'], "❓")
            price = usd(o['price_usd']) if o['pay_method'] == 'usdt' else pkr(o['price_pkr'])
            text += f"{emoji} `#{o['id']}` — {o['pkg_name']} — {price}\n"
    await query.edit_message_text(text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="my_account")]]))


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        f"ℹ️ *HELP*\n\n"
        f"🆓 *Free Subs:*\n"
        f"• {Config.TASK_REQUIRED} channels join → {Config.TASK_REWARD} subs\n"
        f"• Referral → {Config.REFERRAL_REWARD} subs per user\n\n"
        f"💎 *Paid Subs:*\n"
        f"• EasyPaisa/JazzCash ya USDT\n\n"
        f"💱 Rate: 1 USD = Rs. {Config.USD_TO_PKR}\n\n"
        f"Admin: @{Config.ADMIN_USERNAME}"
    )
    await query.edit_message_text(text, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Admin", url=f"https://t.me/{Config.ADMIN_USERNAME}"),
             InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]))


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in Config.ADMIN_IDS:
        await query.answer("❌ Access Denied!", show_alert=True)
        return
    stats = db.get_stats()
    text = (
        f"⚙️ *ADMIN PANEL*\n\n"
        f"👥 Total Users: `{stats['total_users']}`\n"
        f"🆕 Aaj: `{stats['today_users']}`\n"
        f"💎 Orders: `{stats['total_orders']}`\n"
        f"⏳ Pending: `{stats['pending_orders']}`\n"
        f"💰 Revenue: `{pkr(stats['total_revenue'])}`"
    )
    rows = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("⏳ Pending Orders", callback_data="admin_pending")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows))


async def admin_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in Config.ADMIN_IDS:
        return
    orders = db.get_pending_orders()
    if not orders:
        await query.edit_message_text("✅ Koi pending orders nahi!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
        return
    await query.edit_message_text(f"⏳ *{len(orders)} Pending Orders:*", parse_mode='Markdown')
    for o in orders[:5]:
        price = usd(o['price_usd']) if o['pay_method'] == 'usdt' else pkr(o['price_pkr'])
        await query.message.reply_text(
            f"⏳ *Order #{o['id']}*\n👤 {o['full_name']}\n📦 {o['pkg_name']}\n💰 {price}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_order_{o['id']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_order_{o['id']}")
            ]])
        )


async def approve_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in Config.ADMIN_IDS:
        return
    order_id = int(query.data.split("_")[-1])
    order = db.approve_order(order_id)
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=f"🎉 *Order #{order_id} Approve!*\n\n📦 {order['pkg_name']}\n👥 {order['subs']:,} subscribers jald milenge!",
            parse_mode='Markdown'
        )
    except Exception:
        pass
    await query.edit_message_text(f"✅ Order #{order_id} Approved!")


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in Config.ADMIN_IDS:
        return
    order_id = int(query.data.split("_")[-1])
    order = db.get_order(order_id)
    db.reject_order(order_id)
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=f"❌ Order #{order_id} reject hua.\nAdmin: @{Config.ADMIN_USERNAME}",
            parse_mode='Markdown'
        )
    except Exception:
        pass
    await query.edit_message_text(f"❌ Order #{order_id} Rejected!")


async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in Config.ADMIN_IDS:
        return
    context.user_data['awaiting_broadcast'] = True
    await query.edit_message_text(
        "📢 *BROADCAST*\n\nJo message sab ko bhejna hai type karo:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]])
    )


async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_broadcast'):
        return
    if update.effective_user.id not in Config.ADMIN_IDS:
        return
    message = update.message.text
    users = db.get_all_users()
    sent = failed = 0
    status = await update.message.reply_text("📢 Broadcasting...")
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 *ANNOUNCEMENT*\n\n{message}",
                parse_mode='Markdown'
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await status.edit_text(f"✅ Done!\nSent: {sent} | Failed: {failed}")
    context.user_data['awaiting_broadcast'] = False


def main():
    app = Application.builder().token(Config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("account", my_account))

    callbacks = {
        "free_menu": free_menu, "paid_menu": paid_menu,
        "referral_menu": referral_menu, "my_account": my_account,
        "orders": orders_history, "help": help_menu,
        "main_menu": main_menu, "task_channels": task_channels,
        "check_channels": check_channels, "get_referral": get_referral,
        "use_free_subs": use_free_subs, "leaderboard": leaderboard,
        "admin_panel": admin_panel, "admin_pending": admin_pending_orders,
        "admin_broadcast": admin_broadcast_start, "dollar_rate": dollar_rate,
    }
    for data, fn in callbacks.items():
        app.add_handler(CallbackQueryHandler(fn, pattern=f"^{data}$"))

    app.add_handler(CallbackQueryHandler(buy_package,   pattern=r"^buy_pkg_\d+$"))
    app.add_handler(CallbackQueryHandler(pay_pkr,       pattern=r"^pay_pkr_\d+$"))
    app.add_handler(CallbackQueryHandler(pay_usdt,      pattern=r"^pay_usdt_\d+$"))
    app.add_handler(CallbackQueryHandler(approve_order, pattern=r"^approve_order_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_order,  pattern=r"^reject_order_\d+$"))

    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_payment_photo))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, send_broadcast))

    logger.info("Bot is running!")
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
