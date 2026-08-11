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


bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# ==========================
# TEMP STORAGE
# ==========================

user_packages = {}

user_proofs = {}

# Menyimpan referral berdasarkan Telegram ID user
#
# Contoh:
# {
#     123456789: "BUDI",
#     987654321: "ANDI"
# }

user_referrals = {}


# ==========================
# HELPER
# ==========================

def get_referral_group(referral):
    """
    Mengambil GROUP_ID berdasarkan referral.

    Jika referral tidak ada atau tidak ditemukan
    di config, gunakan PAYMENT_GROUP_ID.
    """

    if not referral:
        return PAYMENT_GROUP_ID

    referral = referral.strip().upper()

    return REFERRAL_GROUPS.get(
        referral,
        PAYMENT_GROUP_ID
    )


def normalize_referral(referral):
    """
    Membersihkan referral dari website / Telegram.
    """

    if not referral:
        return None

    referral = referral.strip().upper()

    if not referral:
        return None

    return referral


# ==========================
# START WELCOME
# ==========================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id

    # ======================================
    # AMBIL REFERRAL DARI /start
    # ======================================

    referral = None

    if message.text:

        parts = message.text.split(
            maxsplit=1
        )

        if len(parts) == 2:

            referral = normalize_referral(
                parts[1]
            )

    # ======================================
    # SIMPAN REFERRAL
    # ======================================

    if referral:

        user_referrals[user_id] = referral

        print(
            f"[REFERRAL] "
            f"User {user_id} -> {referral}"
        )

    else:

        user_referrals.setdefault(
            user_id,
            None
        )

        print(
            f"[REFERRAL] "
            f"User {user_id} -> NONE"
        )

    # ======================================
    # WELCOME BUTTON
    # ======================================

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(
                    text="🤖 AKTIFKAN AI ASSISTANT",
                    callback_data="activate"
                )

            ]

        ]

    )

    photo = FSInputFile(
        "assets/ai_example.jpg"
    )

    text = f"""

🤖 <b>XAU AI ASSISTANT PREMIUM</b>


👋 Halo <b>{message.from_user.first_name}</b>


Selamat datang di layanan
<b>XAU AI Assistant Premium</b>.


<blockquote>
"Partner AI pribadi untuk membantu Anda
membaca market Gold lebih cepat,
lebih terstruktur, dan tanpa noise."
</blockquote>


━━━━━━━━━━━━━━━━━━


🚀 <b>FITUR PREMIUM</b>


📈 <b>Analisa XAUUSD Premium</b>

🧠 <b>Smart Money Concept Analysis</b>

⚡ <b>Update Market Gold Terbaru</b>

🤖 <b>AI Assistant Telegram Pribadi</b>


━━━━━━━━━━━━━━━━━━


💎 <b>KENAPA BERBEDA?</b>


Anda tidak perlu lagi:


❌ Membaca ratusan chat signal

❌ Mencari informasi penting

❌ Takut kehilangan momentum

❌ Pamer Profit yang membuat ada FOMO


Semua informasi akan dirangkum
langsung oleh AI Assistant Anda.


━━━━━━━━━━━━━━━━━━


🔐 <b>AKTIFKAN AKSES SEKARANG</b>


Dapatkan akses premium untuk membantu
analisa Gold secara lebih cepat
dan profesional.


Klik tombol di bawah untuk memulai.


"""

    await message.answer_photo(

        photo=photo,

        caption=text,

        reply_markup=keyboard,

        parse_mode="HTML"

    )


# ==========================
# PILIH PACKAGE
# ==========================

@dp.callback_query(
    F.data == "activate"
)

async def choose_package(
    callback: CallbackQuery
):

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(
                    text="🥇 STARTER • 1 Bulan | Rp250.000",
                    callback_data="pkg_1month"
                )

            ],

            [

                InlineKeyboardButton(
                    text="🥈 PRO • 6 Bulan | Rp500.000",
                    callback_data="pkg_6month"
                )

            ],

            [

                InlineKeyboardButton(
                    text="🥉 ELITE • 12 Bulan | Rp850.000",
                    callback_data="pkg_12month"
                )

            ],

            [

                InlineKeyboardButton(
                    text="👑 LIFETIME ACCESS | Rp1.500.000",
                    callback_data="pkg_permanent"
                )

            ]

        ]

    )

    text = """

💎 <b>PILIH MEMBERSHIP PLAN</b>


<blockquote>
"Pilih paket akses yang sesuai kebutuhan
trading Anda."
</blockquote>


━━━━━━━━━━━━━━━━━━


🥇 <b>STARTER PLAN</b>

📅 1 Bulan

💰 Rp250.000


━━━━━━━━━━━━━━━━━━


🥈 <b>PRO PLAN</b>

📅 6 Bulan

💰 Rp500.000


━━━━━━━━━━━━━━━━━━


🥉 <b>ELITE PLAN</b>

📅 12 Bulan

💰 Rp850.000


━━━━━━━━━━━━━━━━━━


👑 <b>LIFETIME ACCESS</b>

♾️ Permanent

💰 Rp1.500.000


━━━━━━━━━━━━━━━━━━


✨ Semua paket mendapatkan:

✅ AI Assistant Telegram

✅ Analisa XAUUSD

✅ Smart Money Analysis


Silakan pilih paket untuk melanjutkan.


"""

    await callback.message.answer(

        text,

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    await callback.answer(
        "Silakan pilih paket membership"
    )


# ==========================
# QRIS PAYMENT
# ==========================

@dp.callback_query(
    F.data.startswith("pkg_")
)

async def show_payment(
    callback: CallbackQuery
):

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    package_key = callback.data.replace(
        "pkg_",
        ""
    )

    user_packages[
        callback.from_user.id
    ] = package_key

    data = PACKAGE_MAP[package_key]

    payment_text = f"""

💳 <b>AKTIVASI MEMBERSHIP</b>


<blockquote>
"Selangkah lagi menuju akses
AI Assistant Premium Anda."
</blockquote>


━━━━━━━━━━━━━━━━━━


📦 <b>Paket Dipilih</b>

{data['label']}


💰 <b>Total Pembayaran</b>

Rp {data['price']:,}


━━━━━━━━━━━━━━━━━━


📌 <b>Instruksi Pembayaran</b>


1️⃣ Scan QRIS di atas

2️⃣ Lakukan pembayaran

3️⃣ Kirim bukti pembayaran


📸 Screenshot bukti pembayaran
ke chat ini.


━━━━━━━━━━━━━━━━━━


⏳ Admin akan melakukan verifikasi
dan mengaktifkan akses Anda.


Terima kasih telah bergabung
bersama <b>XAU AI Assistant</b>.


"""

    await callback.message.answer_photo(

        photo=FSInputFile(
            "assets/qris.jpg"
        ),

        caption=payment_text,

        parse_mode="HTML"

    )

    await callback.answer(
        "Paket berhasil dipilih"
    )


# ==========================
# TERIMA BUKTI PEMBAYARAN
# ==========================

@dp.message(
    F.photo
)

async def receive_payment(
    message: Message
):

    user_id = message.from_user.id

    user_proofs[
        user_id
    ] = message.photo[-1].file_id

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="✅ KIRIM KE ADMIN",

                    callback_data="verify"

                )

            ]

        ]

    )

    await message.answer(

        """

✅ <b>BUKTI PEMBAYARAN DITERIMA</b>


<blockquote>
"Data pembayaran Anda sudah siap
untuk dikirim ke Admin."
</blockquote>


━━━━━━━━━━━━━━━━━━


Status:

🟡 Menunggu verifikasi Admin


Klik tombol berikut untuk mengirim
permintaan pengecekan.


""",

        reply_markup=keyboard,

        parse_mode="HTML"

    )


# ==========================
# KIRIM VERIFIKASI ADMIN
# ==========================

@dp.callback_query(
    F.data == "verify"
)

async def verify(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    package_key = user_packages.get(
        user_id
    )

    proof = user_proofs.get(
        user_id
    )

    if not package_key or not proof:

        await callback.answer(

            "⚠️ Data belum lengkap",

            show_alert=True

        )

        return

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    data = PACKAGE_MAP[package_key]

    referral = user_referrals.get(
        user_id
    )

    if referral:

        referral_display = referral

    else:

        referral_display = "-"

    admin_keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="✅ APPROVE",

                    callback_data=f"approve_{user_id}"

                ),

                InlineKeyboardButton(

                    text="❌ REJECT",

                    callback_data=f"reject_{user_id}"

                )

            ]

        ]

    )

    username = (

        f"@{callback.from_user.username}"

        if callback.from_user.username

        else "-"

    )

    admin_text = f"""

📥 <b>PAYMENT VERIFICATION</b>


<blockquote>
"Member baru menunggu pengecekan
aktivasi membership."
</blockquote>


━━━━━━━━━━━━━━━━━━


👤 <b>Nama</b>

{callback.from_user.full_name}


🔹 <b>Username</b>

{username}


🆔 <b>Telegram ID</b>

<code>{user_id}</code>


━━━━━━━━━━━━━━━━━━


📦 <b>Paket</b>

{data['label']}


💰 <b>Total</b>

Rp {data['price']:,}


🔗 <b>Referral</b>

<code>{referral_display}</code>


━━━━━━━━━━━━━━━━━━


⚡ Silakan lakukan verifikasi.


"""

    # ======================================
    # KIRIM LANGSUNG KE ADMIN PRIBADI
    # ======================================

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

            print(
                f"Gagal kirim ke admin "
                f"{admin_id}: {e}"
            )

    await callback.message.answer(

        """

⏳ <b>VERIFIKASI BERHASIL DIKIRIM</b>


<blockquote>
"Admin sedang melakukan pengecekan
pembayaran Anda."
</blockquote>


━━━━━━━━━━━━━━━━━━


Status:

🟡 Menunggu approval


Anda akan menerima notifikasi
setelah membership aktif.


""",

        parse_mode="HTML"

    )

    await callback.answer(
        "Dikirim ke Admin"
    )


# ==========================
# APPROVE MEMBER
# ==========================

@dp.callback_query(
    F.data.startswith("approve_")
)

async def approve(
    callback: CallbackQuery
):

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    user_id = int(
        callback.data.split("_")[1]
    )

    user = await bot.get_chat(
        user_id
    )

    package_key = user_packages.get(
        user_id
    )

    if not package_key:

        await callback.answer(

            "Data paket tidak ditemukan",

            show_alert=True

        )

        return

    data = PACKAGE_MAP[package_key]

    # ======================================
    # HITUNG EXPIRED
    # ======================================

    if data["days"] == 9999:

        expired = "PERMANENT ACCESS"

    else:

        expired = (

            datetime.now()

            + timedelta(
                days=data["days"]
            )

        ).strftime(
            "%d-%m-%Y"
        )

    # ======================================
    # AMBIL REFERRAL
    # ======================================

    referral = user_referrals.get(
        user_id
    )

    # ======================================
    # TENTUKAN GRUP TUJUAN
    # ======================================

    target_group = get_referral_group(
        referral
    )

    # ======================================
    # TANGGAL REGISTER
    # ======================================

    register_date = datetime.now().strftime(
        "%d-%m-%Y"
    )

    # ======================================
    # SIMPAN KE GOOGLE SHEET
    # ======================================

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

    # ======================================
    # KIRIM AKSES KE USER
    # ======================================

    button = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="🤖 MASUK AI ASSISTANT",

                    url=SIGNAL_BOT

                )

            ]

        ]

    )

    member_text = f"""

🎉 <b>MEMBERSHIP AKTIF</b>


<blockquote>
"Selamat! Anda sekarang resmi menjadi
bagian dari XAU AI Assistant Premium."
</blockquote>


━━━━━━━━━━━━━━━━━━


📦 <b>Paket Anda</b>

{data['label']}


⏳ <b>Masa Aktif</b>

{expired}


━━━━━━━━━━━━━━━━━━


🚀 <b>Akses Premium Anda:</b>


✅ AI Assistant Telegram

✅ Analisa XAUUSD

✅ Smart Money Concept

✅ Market Intelligence Update


━━━━━━━━━━━━━━━━━━


Klik tombol di bawah untuk mulai
menggunakan AI Assistant.


Selamat trading bersama
<b>XAU AI Assistant</b> 🤖


"""

    await bot.send_message(

        chat_id=user_id,

        text=member_text,

        reply_markup=button,

        parse_mode="HTML"

    )

    # ======================================
    # INFO UNTUK GRUP REFERRAL / PAYMENT
    # ======================================
    #
    # HANYA:
    # - Paket
    # - Harga
    # - Referral
    # - Register
    # - Expired
    #
    # TANPA FOTO
    # TANPA NAMA
    # TANPA USERNAME
    # TANPA TELEGRAM ID
    # TANPA STATUS
    #

    referral_display = (
        referral
        if referral
        else "TANPA REFERRAL"
    )

    group_text = f"""

📦 <b>Paket:</b> {data['label']}
💰 <b>Harga:</b> Rp {data['price']:,}

🔗 <b>Referral:</b> <code>{referral_display}</code>

📅 <b>Register:</b> {register_date}
⏳ <b>Expired:</b> {expired}

"""

    # ======================================
    # KIRIM KE GROUP TUJUAN
    # ======================================

    try:

        await bot.send_message(

            chat_id=target_group,

            text=group_text,

            parse_mode="HTML"

        )

        group_status = "SUCCESS"

    except Exception as e:

        group_status = f"FAILED: {e}"

        print(
            f"Gagal kirim ke group "
            f"{target_group}: {e}"
        )

    # ======================================
    # INFO KE ADMIN
    # ======================================

    await callback.message.answer(

        f"""

✅ <b>MEMBER BERHASIL DIAKTIFKAN</b>


Data membership telah tersimpan
dan user sudah menerima akses.


🔗 Referral:
<code>{referral_display}</code>


📢 Group tujuan:
<code>{target_group}</code>


📡 Status pengiriman:
<code>{group_status}</code>


""",

        parse_mode="HTML"

    )

    await callback.answer(
        "Member aktif"
    )


# ==========================
# REJECT MEMBER
# ==========================

@dp.callback_query(
    F.data.startswith("reject_")
)

async def reject(
    callback: CallbackQuery
):

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    user_id = int(
        callback.data.split("_")[1]
    )

    reject_text = """

❌ <b>PEMBAYARAN BELUM DIVERIFIKASI</b>


<blockquote>
"Terjadi kendala saat melakukan
pengecekan pembayaran Anda."
</blockquote>


━━━━━━━━━━━━━━━━━━


Mohon:


📌 Periksa kembali bukti pembayaran

📌 Pastikan nominal sesuai

📌 Hubungi Admin untuk bantuan


Admin siap membantu proses
aktivasi Anda.


"""

    await bot.send_message(

        chat_id=user_id,

        text=reject_text,

        parse_mode="HTML"

    )

    await callback.message.answer(

        """

❌ <b>PAYMENT DITOLAK</b>


User telah menerima notifikasi
bahwa pembayaran belum dapat
diverifikasi.


""",

        parse_mode="HTML"

    )

    await callback.answer(
        "Payment rejected"
    )


# ==========================
# ADMIN: KIRIM PESAN KE USER
# ==========================

@dp.message(
    F.text.startswith("/sent")
)

async def sent_to_user(
    message: Message
):

    if message.from_user.id not in ADMIN_IDS:

        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.answer(

            "⚠️ Format salah.\n\n"

            "Gunakan:\n"

            "<code>/sent [telegram_id] [pesan]</code>",

            parse_mode="HTML"

        )

        return

    target_id_str = parts[1]

    text_to_send = parts[2]

    if not target_id_str.isdigit():

        await message.answer(
            "⚠️ Telegram ID harus berupa angka."
        )

        return

    target_id = int(
        target_id_str
    )

    try:

        await bot.send_message(

            chat_id=target_id,

            text=text_to_send

        )

        await message.answer(

            f"✅ <b>Pesan berhasil dikirim</b>\n\n"

            f"🆔 Target: <code>{target_id}</code>\n"

            f"💬 Isi: {text_to_send}",

            parse_mode="HTML"

        )

    except Exception as e:

        await message.answer(

            f"❌ <b>Pesan gagal dikirim</b>\n\n"

            f"🆔 Target: <code>{target_id}</code>\n"

            f"⚠️ Error: <code>{e}</code>",

            parse_mode="HTML"

        )


# ==========================
# RUN BOT
# ==========================

async def main():

    print(
        "🤖 XAU AI Assistant Bot Running..."
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    asyncio.run(main())

