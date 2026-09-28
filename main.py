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


# ============================================================
# BOT
# ============================================================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


# ============================================================
# TEMP STORAGE
# ============================================================

user_packages = {}

user_proofs = {}

user_referrals = {}


# ============================================================
# PACKAGE GROUP ACCESS
# ============================================================

def package_has_group_access(package_key: str) -> bool:
    """
    Paket yang mendapatkan akses Grup Diskusi & Sharing.

    1 Bulan = AI saja
    2 Bulan = AI + Group
    3 Bulan = AI + Group
    """

    return package_key in (
        "2BLN",
        "3BLN"
    )


# ============================================================
# REFERRAL GROUP
# ============================================================

def get_referral_group(referral):
    """
    Menentukan GROUP_ID berdasarkan referral.

    Contoh yang didukung:

    AKMAL
    REF_AKMAL
    JOIN_2BLN_REF_AKMAL
    JOIN_3BLN_REF_AKMAL

    OM
    REF_OM
    JOIN_2BLN_REF_OM

    IKO
    REF_IKO

    Dan referral lain yang
    ditambahkan ke REFERRAL_GROUPS.
    """

    # --------------------------------------------------------
    # TIDAK ADA REFERRAL
    # --------------------------------------------------------

    if not referral:

        print(
            f"[REFERRAL GROUP] "
            f"NONE -> FALLBACK -> {PAYMENT_GROUP_ID}"
        )

        return PAYMENT_GROUP_ID


    referral = referral.strip().upper()


    # --------------------------------------------------------
    # CEK SEMUA REFERRAL
    # --------------------------------------------------------

    for referral_code, group_id in REFERRAL_GROUPS.items():

        referral_code = referral_code.strip().upper()


        # Contoh:
        # REF_AKMAL -> AKMAL

        clean_code = referral_code

        if clean_code.startswith("REF_"):

            clean_code = clean_code[4:]


        # ----------------------------------------------------
        # FORMAT 1
        # AKMAL
        # ----------------------------------------------------

        if referral == clean_code:

            print(
                f"[REFERRAL GROUP] "
                f"{referral} -> {referral_code} -> {group_id}"
            )

            return group_id


        # ----------------------------------------------------
        # FORMAT 2
        # REF_AKMAL
        # ----------------------------------------------------

        if referral == referral_code:

            print(
                f"[REFERRAL GROUP] "
                f"{referral} -> {referral_code} -> {group_id}"
            )

            return group_id


        # ----------------------------------------------------
        # FORMAT 3
        # JOIN_2BLN_REF_AKMAL
        # JOIN_3BLN_REF_AKMAL
        # JOIN_TRIAL7_REF_AKMAL
        # ----------------------------------------------------

        if referral.endswith(
            "_" + referral_code
        ):

            print(
                f"[REFERRAL GROUP] "
                f"{referral} -> {referral_code} -> {group_id}"
            )

            return group_id


        # ----------------------------------------------------
        # FORMAT 4
        # JOIN_2BLN_AKMAL
        # JOIN_3BLN_AKMAL
        # ----------------------------------------------------

        if referral.endswith(
            "_" + clean_code
        ):

            print(
                f"[REFERRAL GROUP] "
                f"{referral} -> {referral_code} -> {group_id}"
            )

            return group_id


    # --------------------------------------------------------
    # REFERRAL TIDAK DITEMUKAN
    # --------------------------------------------------------

    print(
        f"[REFERRAL GROUP] "
        f"{referral} -> FALLBACK -> {PAYMENT_GROUP_ID}"
    )

    return PAYMENT_GROUP_ID


# ============================================================
# NORMALIZE REFERRAL
# ============================================================

def normalize_referral(referral):

    if not referral:

        return None


    referral = referral.strip().upper()


    return referral or None


# ============================================================
# PARSE START PAYLOAD
# ============================================================

def parse_start_payload(payload):
    """
    Format:

    JOIN_1BLN
    JOIN_2BLN
    JOIN_3BLN

    JOIN_1BLN_ref_AKMAL
    JOIN_2BLN_ref_AKMAL
    JOIN_3BLN_ref_AKMAL

    ref_AKMAL

    AKMAL
    """

    if not payload:

        return None, None


    payload = payload.strip()

    upper = payload.upper()


    # ========================================================
    # JOIN FORMAT
    # ========================================================

    if upper.startswith("JOIN_"):

        rest = payload[5:]


        # ----------------------------------------------------
        # JOIN_<CODE>_ref_<REF>
        # ----------------------------------------------------

        if "_ref_" in rest.lower():

            idx = rest.lower().index("_ref_")


            code = rest[:idx]

            ref = rest[idx + 5:]


        else:

            code = rest

            ref = None


        code = code.strip().upper()


        # ----------------------------------------------------
        # VALIDASI PACKAGE
        # ----------------------------------------------------

        if code not in PACKAGE_MAP:

            code = None


        return (
            code,
            normalize_referral(ref)
        )


    # ========================================================
    # REF_AKMAL
    # ========================================================

    if upper.startswith("REF_"):

        return (
            None,
            normalize_referral(
                payload[4:]
            )
        )


    # ========================================================
    # REFERRAL POLOS
    # ========================================================

    return (
        None,
        normalize_referral(payload)
    )


# ============================================================
# PACKAGE BUTTON LABEL
# ============================================================

def package_button_label(key):

    data = PACKAGE_MAP[key]


    return (
        f"{data['label']} | "
        f"Rp{data['price']:,}"
    )


# ============================================================
# SEND QRIS
# ============================================================

async def send_qris(
    message: Message,
    package_key: str
):

    """
    Kirim QRIS + instruksi pembayaran.
    """

    if package_key not in PACKAGE_MAP:

        await message.answer(
            "⚠️ Paket tidak ditemukan."
        )

        return


    data = PACKAGE_MAP[package_key]


    # ========================================================
    # GROUP INFO
    # ========================================================

    if package_has_group_access(
        package_key
    ):

        group_info = (
            "\n\n"
            "👥 <b>Termasuk akses Grup Diskusi & Sharing</b>"
        )

    else:

        group_info = (
            "\n\n"
            "🤖 <b>Akses AI Assistant pribadi</b>"
        )


    text = f"""💳 <b>AKTIVASI MEMBERSHIP</b>

📦 Paket: <b>{data['label']}</b>
💰 Total: <b>Rp {data['price']:,}</b>{group_info}

📌 Cara bayar:

1️⃣ Scan QRIS di atas
2️⃣ Transfer sesuai nominal
3️⃣ Kirim bukti pembayaran ke chat ini

⏳ Setelah itu Admin akan melakukan verifikasi pembayaran."""


    await message.answer_photo(
        photo=FSInputFile(
            "assets/qris.jpg"
        ),
        caption=text,
        parse_mode="HTML"
    )


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id


    payload = None


    if message.text:

        parts = message.text.split(
            maxsplit=1
        )


        if len(parts) == 2:

            payload = parts[1]


    # ========================================================
    # PARSE PAYLOAD
    # ========================================================

    package_key, referral = parse_start_payload(
        payload
    )


    # ========================================================
    # SIMPAN REFERRAL
    # ========================================================

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


    # ========================================================
    # SIMPAN PACKAGE
    # ========================================================

    if package_key:

        user_packages[user_id] = package_key


        print(
            f"[PACKAGE] "
            f"User {user_id} -> {package_key}"
        )


    # ========================================================
    # MENU PACKAGE
    # ========================================================

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=(
                        f"🥇 "
                        f"{package_button_label('1BLN')}"
                    ),
                    callback_data="pkg_1BLN"
                )
            ],

            [
                InlineKeyboardButton(
                    text=(
                        f"🥈 "
                        f"{package_button_label('2BLN')}"
                    ),
                    callback_data="pkg_2BLN"
                )
            ],

            [
                InlineKeyboardButton(
                    text=(
                        f"🥉 "
                        f"{package_button_label('3BLN')}"
                    ),
                    callback_data="pkg_3BLN"
                )
            ]

        ]
    )


    text = f"""🤖 <b>XAU AI ASSISTANT PREMIUM</b>

Halo <b>{message.from_user.first_name}</b> 👋

Silakan pilih paket membership:

🥇 <b>1 Bulan</b>
AI Assistant pribadi

🥈 <b>2 Bulan</b>
AI Assistant + Grup Diskusi & Sharing

🥉 <b>3 Bulan</b>
AI Assistant + Grup Diskusi & Sharing

Pilih paket di bawah untuk melanjutkan pembayaran."""


    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============================================================
# PILIH PACKAGE MANUAL
# ============================================================

@dp.callback_query(
    F.data.startswith("pkg_")
)
async def show_payment(
    callback: CallbackQuery
):

    package_key = callback.data.replace(
        "pkg_",
        ""
    )


    # ========================================================
    # VALIDASI PACKAGE
    # ========================================================

    if package_key not in PACKAGE_MAP:

        await callback.answer(
            "⚠️ Paket tidak ditemukan.",
            show_alert=True
        )

        return


    # ========================================================
    # SIMPAN PACKAGE
    # ========================================================

    user_packages[
        callback.from_user.id
    ] = package_key


    # ========================================================
    # HAPUS BUTTON LAMA
    # ========================================================

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass


    # ========================================================
    # QRIS
    # ========================================================

    await send_qris(
        callback.message,
        package_key
    )


    await callback.answer(
        "Paket berhasil dipilih"
    )


# ============================================================
# TERIMA BUKTI PEMBAYARAN
# ============================================================

@dp.message(F.photo)
async def receive_payment(
    message: Message
):

    user_id = message.from_user.id


    # ========================================================
    # CEK PACKAGE
    # ========================================================

    package_key = user_packages.get(
        user_id
    )


    if not package_key:

        await message.answer(
            "⚠️ Silakan pilih paket terlebih dahulu menggunakan /start."
        )

        return


    # ========================================================
    # SIMPAN PHOTO
    # ========================================================

    user_proofs[user_id] = (
        message.photo[-1].file_id
    )


    # ========================================================
    # BUTTON VERIFY
    # ========================================================

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


    text = """✅ <b>BUKTI PEMBAYARAN DITERIMA</b>

Status: 🟡 Menunggu verifikasi Admin

Klik tombol di bawah untuk mengirim bukti pembayaran ke Admin."""


    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============================================================
# VERIFY PAYMENT
# ============================================================

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


    if (
        not package_key
        or not proof
    ):

        await callback.answer(
            "⚠️ Data belum lengkap",
            show_alert=True
        )

        return


    # ========================================================
    # HAPUS BUTTON USER
    # ========================================================

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass


    data = PACKAGE_MAP[
        package_key
    ]


    # ========================================================
    # REFERRAL
    # ========================================================

    referral = user_referrals.get(
        user_id
    )


    referral_display = (
        referral
        if referral
        else "-"
    )


    # ========================================================
    # ADMIN KEYBOARD
    # ========================================================

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[

            [

                InlineKeyboardButton(
                    text="✅ APPROVE",
                    callback_data=(
                        f"approve_{user_id}"
                    )
                ),

                InlineKeyboardButton(
                    text="❌ REJECT",
                    callback_data=(
                        f"reject_{user_id}"
                    )
                )

            ]

        ]
    )


    # ========================================================
    # USERNAME
    # ========================================================

    username = (

        f"@{callback.from_user.username}"

        if callback.from_user.username

        else "-"

    )


    # ========================================================
    # ADMIN TEXT
    # ========================================================

    admin_text = f"""📥 <b>PAYMENT VERIFICATION</b>

👤 Nama: {callback.from_user.full_name}
🔹 Username: {username}
🆔 Telegram ID: <code>{user_id}</code>

📦 Paket: <b>{data['label']}</b>
💰 Total: <b>Rp {data['price']:,}</b>
🔗 Referral: <code>{referral_display}</code>

👥 Group Access:
{"✅ YA" if package_has_group_access(package_key) else "❌ TIDAK"}

⚡ Silakan lakukan verifikasi."""


    # ========================================================
    # SEND TO ALL ADMIN
    # ========================================================

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


    # ========================================================
    # USER MESSAGE
    # ========================================================

    await callback.message.answer(

        "⏳ <b>VERIFIKASI DIKIRIM</b>\n\n"
        "Status: 🟡 Menunggu approval Admin.",

        parse_mode="HTML"

    )


    await callback.answer(
        "Dikirim ke Admin"
    )


# ============================================================
# APPROVE MEMBER
# ============================================================

@dp.callback_query(
    F.data.startswith("approve_")
)
async def approve(
    callback: CallbackQuery
):

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass


    # ========================================================
    # USER ID
    # ========================================================

    user_id = int(
        callback.data.split("_")[1]
    )


    # ========================================================
    # GET USER
    # ========================================================

    try:

        user = await bot.get_chat(
            user_id
        )

    except Exception as e:

        await callback.answer(
            "User tidak ditemukan.",
            show_alert=True
        )

        print(
            f"[APPROVE] "
            f"Gagal get user {user_id}: {e}"
        )

        return


    # ========================================================
    # GET PACKAGE
    # ========================================================

    package_key = user_packages.get(
        user_id
    )


    if not package_key:

        await callback.answer(
            "Data paket tidak ditemukan",
            show_alert=True
        )

        return


    if package_key not in PACKAGE_MAP:

        await callback.answer(
            "Paket tidak valid",
            show_alert=True
        )

        return


    data = PACKAGE_MAP[
        package_key
    ]


    # ========================================================
    # EXPIRED
    # ========================================================

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


    # ========================================================
    # REFERRAL
    # ========================================================

    referral = user_referrals.get(
        user_id
    )


    # ========================================================
    # GROUP ACCESS
    # ========================================================

    has_group_access = package_has_group_access(
        package_key
    )


    # ========================================================
    # TARGET REFERRAL GROUP
    # ========================================================

    if has_group_access:

        target_group = get_referral_group(
            referral
        )

    else:

        target_group = None


    # ========================================================
    # REGISTER DATE
    # ========================================================

    register_date = datetime.now().strftime(
        "%d-%m-%Y"
    )


    # ========================================================
    # SAVE GOOGLE SHEET
    # ========================================================

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


    # ========================================================
    # USER BUTTON
    # ========================================================

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


    # ========================================================
    # GROUP INFO USER
    # ========================================================

    if has_group_access:

        group_user_text = """

👥 <b>Grup Diskusi & Sharing</b>
Akses grup akan diberikan sesuai proses membership."""

    else:

        group_user_text = """

🤖 <b>Akses Grup:</b>
Tidak termasuk dalam paket 1 Bulan."""


    # ========================================================
    # MEMBER ACTIVE MESSAGE
    # ========================================================

    member_text = f"""🎉 <b>MEMBERSHIP AKTIF</b>

📦 Paket: <b>{data['label']}</b>
💰 Harga: <b>Rp {data['price']:,}</b>
⏳ Masa Aktif: <b>{expired}</b>

✅ AI Assistant Telegram
✅ Analisa XAUUSD
✅ Smart Money Concept{group_user_text}

Selamat trading bersama
<b>XAU AI Assistant</b> 🤖"""


    await bot.send_message(

        chat_id=user_id,

        text=member_text,

        reply_markup=button,

        parse_mode="HTML"

    )


    # ========================================================
    # GROUP MESSAGE
    # ========================================================

    group_status = "NOT REQUIRED"


    if has_group_access:

        referral_display = (
            referral
            if referral
            else "TANPA REFERRAL"
        )


        group_text = f"""📦 <b>MEMBER BARU</b>

👤 <b>Nama:</b> {user.full_name}
🔹 <b>Username:</b> @{user.username if user.username else "-"}
🆔 <b>Telegram ID:</b> <code>{user_id}</code>

📦 <b>Paket:</b> {data['label']}
💰 <b>Harga:</b> Rp {data['price']:,}

🔗 <b>Referral:</b> <code>{referral_display}</code>
📅 <b>Register:</b> {register_date}
⏳ <b>Expired:</b> {expired}"""


        # ----------------------------------------------------
        # SEND TO REFERRAL GROUP
        # ----------------------------------------------------

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


    # ========================================================
    # ADMIN RESULT
    # ========================================================

    referral_display = (
        referral
        if referral
        else "TANPA REFERRAL"
    )


    if has_group_access:

        group_display = (
            f"<code>{target_group}</code>"
        )

    else:

        group_display = "TIDAK ADA"


    await callback.message.answer(

        f"✅ <b>MEMBER AKTIF</b>\n\n"

        f"👤 Nama: "
        f"<b>{user.full_name}</b>\n"

        f"📦 Paket: "
        f"<b>{data['label']}</b>\n"

        f"💰 Harga: "
        f"<b>Rp {data['price']:,}</b>\n"

        f"⏳ Expired: "
        f"<b>{expired}</b>\n\n"

        f"🔗 Referral: "
        f"<code>{referral_display}</code>\n"

        f"👥 Group Access: "
        f"<b>{'YA' if has_group_access else 'TIDAK'}</b>\n"

        f"📢 Group: "
        f"{group_display}\n"

        f"📡 Status: "
        f"<code>{group_status}</code>",

        parse_mode="HTML"

    )


    await callback.answer(
        "Member aktif"
    )


# ============================================================
# REJECT MEMBER
# ============================================================

@dp.callback_query(
    F.data.startswith("reject_")
)
async def reject(
    callback: CallbackQuery
):

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:

        pass


    user_id = int(
        callback.data.split("_")[1]
    )


    reject_text = """❌ <b>PEMBAYARAN BELUM DIVERIFIKASI</b>

Mohon periksa kembali bukti pembayaran dan nominal.

Jika membutuhkan bantuan, silakan hubungi Admin."""


    try:

        await bot.send_message(

            chat_id=user_id,

            text=reject_text,

            parse_mode="HTML"

        )

    except Exception as e:

        print(
            f"Gagal kirim reject ke "
            f"{user_id}: {e}"
        )


    await callback.message.answer(

        "❌ User telah diberi tahu bahwa payment belum bisa diverifikasi.",

        parse_mode="HTML"

    )


    await callback.answer(
        "Payment rejected"
    )


# ============================================================
# ADMIN: KIRIM PESAN KE USER
# ============================================================

@dp.message(
    F.text.startswith("/sent")
)
async def sent_to_user(
    message: Message
):

    # ========================================================
    # CEK ADMIN
    # ========================================================

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


    # ========================================================
    # VALIDASI TELEGRAM ID
    # ========================================================

    if not target_id_str.isdigit():

        await message.answer(
            "⚠️ Telegram ID harus berupa angka."
        )

        return


    target_id = int(
        target_id_str
    )


    # ========================================================
    # KIRIM PESAN
    # ========================================================

    try:

        await bot.send_message(

            chat_id=target_id,

            text=text_to_send

        )


        await message.answer(

            f"✅ Pesan terkirim ke "
            f"<code>{target_id}</code>\n\n"
            f"💬 {text_to_send}",

            parse_mode="HTML"

        )


    except Exception as e:

        await message.answer(

            f"❌ Gagal kirim ke "
            f"<code>{target_id}</code>\n"
            f"⚠️ {e}",

            parse_mode="HTML"

        )


# ============================================================
# RUN BOT
# ============================================================

async def main():

    print(
        "=========================================="
    )

    print(
        "🤖 XAU AI Assistant Bot Running..."
    )

    print(
        "=========================================="
    )

    print(
        "[PACKAGE] 1BLN = AI Assistant ONLY"
    )

    print(
        "[PACKAGE] 2BLN = AI Assistant + GROUP"
    )

    print(
        "[PACKAGE] 3BLN = AI Assistant + GROUP"
    )


    await dp.start_polling(
        bot
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
