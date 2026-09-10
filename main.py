import asyncio

from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F

from aiogram.filters import CommandStart

from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import (
    BOT_TOKEN,
    PAYMENT_GROUP_ID,
    SIGNAL_BOT,
    ADMIN_IDS,
    REFERRAL_GROUPS
)

from packages import PACKAGE_MAP

from spreadsheet import save_member


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==========================
# TEMP STORAGE
# ==========================

user_packages = {}
user_proofs = {}
user_referrals = {}


# ==========================
# HELPER
# ==========================

def get_referral_group(referral):
    """Ambil GROUP_ID dari referral, fallback ke PAYMENT_GROUP_ID."""
    if not referral:
        return PAYMENT_GROUP_ID
    return REFERRAL_GROUPS.get(referral.strip().upper(), PAYMENT_GROUP_ID)


def normalize_referral(referral):
    if not referral:
        return None
    referral = referral.strip().upper()
    return referral or None


def parse_start_payload(payload):
    """
    Mem-parse payload dari deep link /start.

    Format yang didukung:
    - JOIN_<CODE>            -> paket dipilih langsung dari web, tanpa referral
    - JOIN_<CODE>_ref_<REF>  -> paket dipilih langsung dari web + referral
    - ref_<REF>              -> hanya referral (format lama)
    - <REF>                  -> referral polos (format lama)

    Return: (package_key atau None, referral atau None)
    """
    if not payload:
        return None, None

    payload = payload.strip()
    upper = payload.upper()

    if upper.startswith("JOIN_"):
        rest = payload[5:]
        if "_ref_" in rest.lower():
            idx = rest.lower().index("_ref_")
            code, ref = rest[:idx], rest[idx + 5:]
        else:
            code, ref = rest, None

        code = code.strip().upper()
        if code not in PACKAGE_MAP:
            code = None

        return code, normalize_referral(ref)

    if upper.startswith("REF_"):
        return None, normalize_referral(payload[4:])

    return None, normalize_referral(payload)


def package_button_label(key):
    data = PACKAGE_MAP[key]
    return f"{data['label']} | Rp{data['price']:,}"


async def send_qris(message: Message, package_key: str):
    """Kirim QRIS + instruksi pembayaran untuk paket yang sudah dipilih."""

    data = PACKAGE_MAP[package_key]

    text = f"""💳 <b>AKTIVASI MEMBERSHIP</b>

📦 Paket: <b>{data['label']}</b>
💰 Total: <b>Rp {data['price']:,}</b>

📌 Cara bayar:
1️⃣ Scan QRIS di atas
2️⃣ Transfer sesuai nominal
3️⃣ Kirim bukti pembayaran ke chat ini

⏳ Admin akan verifikasi & aktifkan akses kamu."""

    await message.answer_photo(
        photo=FSInputFile("assets/qris.jpg"),
        caption=text,
        parse_mode="HTML"
    )


# ==========================
# START WELCOME
# ==========================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    payload = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2:
            payload = parts[1]

    package_key, referral = parse_start_payload(payload)

    if referral:
        user_referrals[user_id] = referral
        print(f"[REFERRAL] User {user_id} -> {referral}")
    else:
        user_referrals.setdefault(user_id, None)

    if package_key:
        user_packages[user_id] = package_key
        print(f"[PACKAGE] User {user_id} -> {package_key}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AKTIFKAN AI ASSISTANT", callback_data="activate")]
    ])

    text = f"""🤖 <b>XAU AI ASSISTANT PREMIUM</b>

👋 Halo <b>{message.from_user.first_name}</b>, selamat datang di <b>XAU AI Assistant Premium</b> — partner AI pribadi untuk membaca market Gold lebih cepat dan terstruktur.

🚀 <b>Fitur:</b>
📈 Analisa XAUUSD Premium
🧠 Smart Money Concept Analysis
⚡ Update Market Gold Real-Time
🤖 AI Assistant Telegram Pribadi

Klik tombol di bawah untuk mengaktifkan akses."""

    await message.answer_photo(
        photo=FSInputFile("assets/ai_example.jpg"),
        caption=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ==========================
# AKTIFKAN — langsung QRIS jika paket sudah diketahui dari link
# ==========================

@dp.callback_query(F.data == "activate")
async def choose_package(callback: CallbackQuery):

    await callback.message.edit_reply_markup(reply_markup=None)

    user_id = callback.from_user.id
    package_key = user_packages.get(user_id)

    if package_key and package_key in PACKAGE_MAP:
        await send_qris(callback.message, package_key)
        await callback.answer("Paket sudah dipilih dari link")
        return

    # Fallback: user masuk tanpa link paket -> tampilkan menu manual
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎁 {package_button_label('TRIAL7')}", callback_data="pkg_TRIAL7")],
        [InlineKeyboardButton(text=f"🥇 {package_button_label('1BLN')}", callback_data="pkg_1BLN")],
        [InlineKeyboardButton(text=f"🥈 {package_button_label('6BLN')}", callback_data="pkg_6BLN")],
        [InlineKeyboardButton(text=f"🥉 {package_button_label('12BLN')}", callback_data="pkg_12BLN")],
        [InlineKeyboardButton(text=f"👑 {package_button_label('3THN')}", callback_data="pkg_3THN")],
    ])

    text = """💎 <b>PILIH MEMBERSHIP PLAN</b>

Semua paket dapat: AI Assistant Telegram, Analisa XAUUSD, Smart Money Analysis.

Silakan pilih paket untuk melanjutkan."""

    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("Silakan pilih paket")


# ==========================
# PILIH PACKAGE MANUAL -> QRIS
# ==========================

@dp.callback_query(F.data.startswith("pkg_"))
async def show_payment(callback: CallbackQuery):

    await callback.message.edit_reply_markup(reply_markup=None)

    package_key = callback.data.replace("pkg_", "")
    user_packages[callback.from_user.id] = package_key

    await send_qris(callback.message, package_key)
    await callback.answer("Paket berhasil dipilih")


# ==========================
# TERIMA BUKTI PEMBAYARAN
# ==========================

@dp.message(F.photo)
async def receive_payment(message: Message):

    user_id = message.from_user.id
    user_proofs[user_id] = message.photo[-1].file_id

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ KIRIM KE ADMIN", callback_data="verify")]
    ])

    text = """✅ <b>BUKTI PEMBAYARAN DITERIMA</b>

Status: 🟡 Menunggu verifikasi Admin

Klik tombol di bawah untuk mengirim permintaan pengecekan."""

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ==========================
# KIRIM VERIFIKASI ADMIN
# ==========================

@dp.callback_query(F.data == "verify")
async def verify(callback: CallbackQuery):

    user_id = callback.from_user.id
    package_key = user_packages.get(user_id)
    proof = user_proofs.get(user_id)

    if not package_key or not proof:
        await callback.answer("⚠️ Data belum lengkap", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)

    data = PACKAGE_MAP[package_key]
    referral = user_referrals.get(user_id)
    referral_display = referral if referral else "-"

    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ REJECT", callback_data=f"reject_{user_id}")
        ]
    ])

    username = f"@{callback.from_user.username}" if callback.from_user.username else "-"

    admin_text = f"""📥 <b>PAYMENT VERIFICATION</b>

👤 Nama: {callback.from_user.full_name}
🔹 Username: {username}
🆔 Telegram ID: <code>{user_id}</code>

📦 Paket: {data['label']}
💰 Total: Rp {data['price']:,}
🔗 Referral: <code>{referral_display}</code>

⚡ Silakan lakukan verifikasi."""

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=proof,
                caption=admin_text,
                reply_markup=admin_keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Gagal kirim ke admin {admin_id}: {e}")

    await callback.message.answer(
        "⏳ <b>VERIFIKASI DIKIRIM</b>\n\nStatus: 🟡 Menunggu approval Admin.",
        parse_mode="HTML"
    )
    await callback.answer("Dikirim ke Admin")


# ==========================
# APPROVE MEMBER
# ==========================

@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: CallbackQuery):

    await callback.message.edit_reply_markup(reply_markup=None)

    user_id = int(callback.data.split("_")[1])
    user = await bot.get_chat(user_id)
    package_key = user_packages.get(user_id)

    if not package_key:
        await callback.answer("Data paket tidak ditemukan", show_alert=True)
        return

    data = PACKAGE_MAP[package_key]

    expired = (
        "PERMANENT ACCESS" if data["days"] == 9999
        else (datetime.now() + timedelta(days=data["days"])).strftime("%d-%m-%Y")
    )

    referral = user_referrals.get(user_id)
    target_group = get_referral_group(referral)
    register_date = datetime.now().strftime("%d-%m-%Y")

    save_member({
        "telegram_id": user_id,
        "username": user.username or "",
        "nama": user.full_name,
        "paket": data["label"],
        "harga": data["price"],
        "register": register_date,
        "expired": expired,
        "status": "ACTIVE",
        "referral": referral or ""
    })

    button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 MASUK AI ASSISTANT", url=SIGNAL_BOT)]
    ])

    member_text = f"""🎉 <b>MEMBERSHIP AKTIF</b>

📦 Paket: {data['label']}
⏳ Masa Aktif: {expired}

✅ AI Assistant Telegram
✅ Analisa XAUUSD
✅ Smart Money Concept

Selamat trading bersama <b>XAU AI Assistant</b> 🤖"""

    await bot.send_message(chat_id=user_id, text=member_text, reply_markup=button, parse_mode="HTML")

    referral_display = referral if referral else "TANPA REFERRAL"

    group_text = f"""📦 <b>Paket:</b> {data['label']}
💰 <b>Harga:</b> Rp {data['price']:,}
🔗 <b>Referral:</b> <code>{referral_display}</code>
📅 <b>Register:</b> {register_date}
⏳ <b>Expired:</b> {expired}"""

    try:
        await bot.send_message(chat_id=target_group, text=group_text, parse_mode="HTML")
        group_status = "SUCCESS"
    except Exception as e:
        group_status = f"FAILED: {e}"
        print(f"Gagal kirim ke group {target_group}: {e}")

    await callback.message.answer(
        f"✅ <b>MEMBER AKTIF</b>\n\n"
        f"🔗 Referral: <code>{referral_display}</code>\n"
        f"📢 Group: <code>{target_group}</code>\n"
        f"📡 Status: <code>{group_status}</code>",
        parse_mode="HTML"
    )
    await callback.answer("Member aktif")


# ==========================
# REJECT MEMBER
# ==========================

@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery):

    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = int(callback.data.split("_")[1])

    reject_text = """❌ <b>PEMBAYARAN BELUM DIVERIFIKASI</b>

Mohon periksa kembali bukti pembayaran & nominal, lalu hubungi Admin untuk bantuan."""

    await bot.send_message(chat_id=user_id, text=reject_text, parse_mode="HTML")
    await callback.message.answer("❌ User telah diberi tahu payment belum bisa diverifikasi.", parse_mode="HTML")
    await callback.answer("Payment rejected")


# ==========================
# ADMIN: KIRIM PESAN KE USER
# ==========================

@dp.message(F.text.startswith("/sent"))
async def sent_to_user(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "⚠️ Format salah.\nGunakan: <code>/sent [telegram_id] [pesan]</code>",
            parse_mode="HTML"
        )
        return

    target_id_str, text_to_send = parts[1], parts[2]

    if not target_id_str.isdigit():
        await message.answer("⚠️ Telegram ID harus berupa angka.")
        return

    target_id = int(target_id_str)

    try:
        await bot.send_message(chat_id=target_id, text=text_to_send)
        await message.answer(
            f"✅ Pesan terkirim ke <code>{target_id}</code>\n💬 {text_to_send}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"❌ Gagal kirim ke <code>{target_id}</code>\n⚠️ {e}",
            parse_mode="HTML"
        )


# ==========================
# RUN BOT
# ==========================

async def main():
    print("🤖 XAU AI Assistant Bot Running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
