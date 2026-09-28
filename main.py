import asyncio
import re

from datetime import datetime, timedelta


from aiogram import (
    Bot,
    Dispatcher,
    F
)

from aiogram.filters import (
    CommandStart,
    Command
)

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


from packages import (
    PACKAGE_MAP
)


from spreadsheet import (
    save_member,
    get_expired_group_members,
    update_member_status
)


# ==========================================
# BOT
# ==========================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# ==========================================
# TEMP MEMORY
# ==========================================

user_packages = {}

user_proofs = {}

user_referrals = {}


# ==========================================
# GROUP ACCESS
# ==========================================

def package_has_group_access(
    package_key
):

    return package_key in (
        "2BLN",
        "3BLN"
    )


# ==========================================
# ADMIN CHECK
# ==========================================

def is_admin(
    user_id
):

    if isinstance(
        ADMIN_IDS,
        (list, tuple, set)
    ):

        return user_id in ADMIN_IDS

    return user_id == ADMIN_IDS


# ==========================================
# REFERRAL GROUP
# ==========================================

def get_referral_group(
    referral=None
):

    # ======================================
    # NO REFERRAL
    # ======================================

    if not referral:

        print(
            "[REFERRAL GROUP] "
            "Referral kosong -> PAYMENT_GROUP_ID"
        )

        return PAYMENT_GROUP_ID

    referral = str(
        referral
    ).strip().upper()

    # ======================================
    # NORMALIZE JOIN PAYLOAD
    # ======================================

    if referral.startswith(
        "JOIN_"
    ):

        # ----------------------------------
        # JOIN_1BLN_REF_AKMAL
        # JOIN_2BLN_REF_AKMAL
        # JOIN_3BLN_REF_AKMAL
        # ----------------------------------

        match = re.search(
            r"_REF_([A-Z0-9_]+)$",
            referral
        )

        if match:

            referral = (
                "REF_"
                + match.group(1)
            )

        else:

            # ----------------------------------
            # JOIN_1BLN_AKMAL
            # JOIN_2BLN_AKMAL
            # JOIN_3BLN_AKMAL
            # ----------------------------------

            match = re.search(
                r"JOIN_(?:1BLN|2BLN|3BLN)_([A-Z0-9_]+)$",
                referral
            )

            if match:

                referral = (
                    "REF_"
                    + match.group(1)
                )

    # ======================================
    # ADD REF_ PREFIX
    # ======================================

    elif not referral.startswith(
        "REF_"
    ):

        referral = (
            "REF_"
            + referral
        )

    # ======================================
    # SEARCH REFERRAL GROUP
    # ======================================

    for key, group_id in REFERRAL_GROUPS.items():

        normalized_key = str(
            key
        ).strip().upper()

        if normalized_key == referral:

            print(
                f"[REFERRAL GROUP] "
                f"{referral} -> {group_id}"
            )

            return group_id

        if (
            not normalized_key.startswith(
                "REF_"
            )
            and
            "REF_" + normalized_key
            == referral
        ):

            print(
                f"[REFERRAL GROUP] "
                f"{referral} -> {group_id}"
            )

            return group_id

    # ======================================
    # FALLBACK
    # ======================================

    print(
        f"[REFERRAL GROUP] "
        f"{referral} tidak ditemukan -> "
        f"{PAYMENT_GROUP_ID}"
    )

    return PAYMENT_GROUP_ID


# ==========================================
# PARSE START PAYLOAD
# ==========================================

def parse_start_payload(
    payload
):

    if not payload:

        return None, None

    payload = str(
        payload
    ).strip().upper()

    # ======================================
    # JOIN_1BLN
    # JOIN_2BLN
    # JOIN_3BLN
    # ======================================

    match = re.match(
        r"^JOIN_(1BLN|2BLN|3BLN)$",
        payload
    )

    if match:

        return (
            match.group(1),
            None
        )

    # ======================================
    # JOIN_1BLN_REF_AKMAL
    # ======================================

    match = re.match(
        r"^JOIN_(1BLN|2BLN|3BLN)_REF_(.+)$",
        payload
    )

    if match:

        return (
            match.group(1),
            "REF_" + match.group(2)
        )

    # ======================================
    # JOIN_1BLN_AKMAL
    # ======================================

    match = re.match(
        r"^JOIN_(1BLN|2BLN|3BLN)_(.+)$",
        payload
    )

    if match:

        return (
            match.group(1),
            "REF_" + match.group(2)
        )

    # ======================================
    # REF_AKMAL
    # ======================================

    if payload.startswith(
        "REF_"
    ):

        return (
            None,
            payload
        )

    # ======================================
    # AKMAL
    # ======================================

    if re.match(
        r"^[A-Z0-9_]+$",
        payload
    ):

        return (
            None,
            "REF_" + payload
        )

    return (
        None,
        None
    )


# ==========================================
# CREATE ONE TIME INVITE
# ==========================================

async def create_group_invite(
    group_id,
    user_id
):

    try:

        expire_at = int(
            (
                datetime.now()
                +
                timedelta(hours=24)
            ).timestamp()
        )

        invite = await bot.create_chat_invite_link(

            chat_id=group_id,

            name=f"Member {user_id}",

            member_limit=1,

            expire_date=expire_at

        )

        print(
            f"[GROUP INVITE] "
            f"Created for user {user_id}"
        )

        return invite.invite_link

    except Exception as e:

        print(
            "[GROUP INVITE] "
            "Create invite error:"
        )

        print(e)

        return None


# ==========================================
# KICK MEMBER
# ==========================================

async def kick_member(
    group_id,
    user_id
):

    try:

        # ==================================
        # BAN
        # ==================================

        await bot.ban_chat_member(

            chat_id=group_id,

            user_id=int(
                user_id
            )

        )

        # ==================================
        # UNBAN
        # ==================================

        await bot.unban_chat_member(

            chat_id=group_id,

            user_id=int(
                user_id
            ),

            only_if_banned=True

        )

        print(
            f"[GROUP] "
            f"Member {user_id} "
            f"berhasil dikeluarkan."
        )

        return True

    except Exception as e:

        print(
            f"[GROUP] "
            f"Gagal kick {user_id}:"
        )

        print(e)

        return False


# ==========================================
# EXPIRED CHECK
# ==========================================

async def check_expired_members():

    print(
        "[EXPIRED MONITOR] "
        "Checking..."
    )

    members = await asyncio.to_thread(
        get_expired_group_members
    )

    if not members:

        print(
            "[EXPIRED CHECK] "
            "Ditemukan 0 member expired."
        )

        return

    print(
        f"[EXPIRED CHECK] "
        f"Ditemukan {len(members)} member expired."
    )

    for member in members:

        try:

            user_id = int(
                member[
                    "telegram_id"
                ]
            )

            referral = member.get(
                "referral",
                ""
            )

            group_id = get_referral_group(
                referral
            )

            # ==================================
            # ONLY GROUP PACKAGE
            # ==================================

            package_label = str(
                member.get(
                    "paket",
                    ""
                )
            ).upper()

            if (
                "2 BULAN" not in package_label
                and
                "3 BULAN" not in package_label
            ):

                continue

            # ==================================
            # KICK
            # ==================================

            kicked = await kick_member(
                group_id,
                user_id
            )

            if kicked:

                # ==================================
                # UPDATE SHEET
                # ==================================

                await asyncio.to_thread(

                    update_member_status,

                    user_id,

                    "EXPIRED"

                )

                # ==================================
                # NOTIFY USER
                # ==================================

                try:

                    await bot.send_message(

                        user_id,

                        "⏰ <b>Masa membership kamu telah berakhir.</b>\n\n"

                        "Akses Grup Diskusi & Sharing telah dihentikan.\n\n"

                        "Silakan melakukan perpanjangan "
                        "membership jika ingin mendapatkan "
                        "akses kembali.",

                        parse_mode="HTML"

                    )

                except Exception as e:

                    print(
                        "[EXPIRED] "
                        "Gagal kirim notifikasi:"
                    )

                    print(e)

        except Exception as e:

            print(
                "[EXPIRED MONITOR] Error:"
            )

            print(e)


# ==========================================
# EXPIRED MONITOR
# ==========================================

async def expired_monitor():

    print(
        "⏰ Expired Monitor Started"
    )

    while True:

        try:

            await check_expired_members()

        except Exception as e:

            print(
                "[EXPIRED MONITOR ERROR]"
            )

            print(e)

        await asyncio.sleep(
            600
        )


# ==========================================
# START
# ==========================================

@dp.message(
    CommandStart()
)

async def start_handler(
    message: Message
):

    parts = message.text.split(
        maxsplit=1
    )

    args = (
        parts[1]
        if len(parts) > 1
        else None
    )

    package_key, referral = parse_start_payload(
        args
    )

    # ======================================
    # SAVE REFERRAL
    # ======================================

    if referral:

        user_referrals[
            message.from_user.id
        ] = referral

        print(
            f"[REFERRAL] "
            f"User "
            f"{message.from_user.id} "
            f"-> "
            f"{referral}"
        )

    # ======================================
    # SAVE PACKAGE
    # ======================================

    if package_key:

        user_packages[
            message.from_user.id
        ] = package_key

    # ======================================
    # PACKAGE MENU
    # ======================================

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(
                    text="💎 1 Bulan — Rp500.000",
                    callback_data="pkg_1BLN"
                )

            ],

            [

                InlineKeyboardButton(
                    text="🔥 2 Bulan — Rp800.000",
                    callback_data="pkg_2BLN"
                )

            ],

            [

                InlineKeyboardButton(
                    text="👑 3 Bulan — Rp1.000.000",
                    callback_data="pkg_3BLN"
                )

            ]

        ]

    )

    await message.answer(

        "🤖 <b>XAU AI INTELLIGENCE</b>\n\n"

        "Pilih paket membership kamu:\n\n"

        "💎 <b>1 Bulan — Rp500.000</b>\n"
        "AI Assistant\n\n"

        "🔥 <b>2 Bulan — Rp800.000</b>\n"
        "AI Assistant + Grup Diskusi & Sharing\n\n"

        "👑 <b>3 Bulan — Rp1.000.000</b>\n"
        "AI Assistant + Grup Diskusi & Sharing",

        reply_markup=keyboard,

        parse_mode="HTML"

    )


# ==========================================
# PACKAGE BUTTON
# ==========================================

@dp.callback_query(
    F.data.startswith("pkg_")
)

async def package_handler(
    callback: CallbackQuery
):

    package_key = callback.data.replace(
        "pkg_",
        ""
    )

    if package_key not in PACKAGE_MAP:

        await callback.answer(
            "Paket tidak tersedia.",
            show_alert=True
        )

        return

    user_id = callback.from_user.id

    user_packages[
        user_id
    ] = package_key

    await callback.answer()

    package = PACKAGE_MAP[
        package_key
    ]

    price = package[
        "price"
    ]

    label = package[
        "label"
    ]

    # ======================================
    # ACCESS INFO
    # ======================================

    if package_has_group_access(
        package_key
    ):

        access_text = (
            "✅ AI Assistant\n"
            "✅ Grup Diskusi & Sharing"
        )

    else:

        access_text = (
            "✅ AI Assistant\n"
            "❌ Tanpa akses grup"
        )

    # ======================================
    # PAYMENT BUTTON
    # ======================================

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="💳 BAYAR & KIRIM BUKTI",

                    callback_data="payment"

                )

            ]

        ]

    )

    await callback.message.edit_text(

        "📦 <b>PAKET YANG DIPILIH</b>\n\n"

        f"<b>{label}</b>\n"

        f"Harga: <b>Rp{price:,}</b>\n\n"

        f"{access_text}\n\n"

        "Silakan lakukan pembayaran melalui QRIS.\n"

        "Setelah pembayaran, kirim bukti transfer "
        "ke bot ini.",

        reply_markup=keyboard,

        parse_mode="HTML"

    )


# ==========================================
# PAYMENT
# ==========================================

@dp.callback_query(
    F.data == "payment"
)

async def payment_handler(
    callback: CallbackQuery
):

    user_id = callback.from_user.id

    package_key = user_packages.get(
        user_id
    )

    if not package_key:

        await callback.answer(

            "Silakan pilih paket terlebih dahulu.",

            show_alert=True

        )

        return

    await callback.answer()

    package = PACKAGE_MAP[
        package_key
    ]

    price = package[
        "price"
    ]

    label = package[
        "label"
    ]

    # ======================================
    # QRIS
    # ======================================

    try:

        photo = FSInputFile(
            "assets/qris.jpg"
        )

        await callback.message.answer_photo(

            photo=photo,

            caption=(

                "💳 <b>PEMBAYARAN QRIS</b>\n\n"

                f"Paket: <b>{label}</b>\n"

                f"Harga: <b>Rp{price:,}</b>\n\n"

                "Silakan scan QRIS di atas.\n\n"

                "Setelah pembayaran berhasil, "
                "kirim <b>foto bukti pembayaran</b> "
                "ke bot ini.\n\n"

                "Admin akan melakukan verifikasi."

            ),

            parse_mode="HTML"

        )

    except Exception as e:

        print(
            "[QRIS] Error:"
        )

        print(e)

        await callback.message.answer(

            "QRIS sedang tidak tersedia. "
            "Silakan hubungi admin."

        )


# ==========================================
# RECEIVE PAYMENT PROOF
# ==========================================

@dp.message(
    F.photo
)

async def receive_payment_proof(
    message: Message
):

    user_id = message.from_user.id

    package_key = user_packages.get(
        user_id
    )

    if not package_key:

        await message.answer(

            "Silakan pilih paket terlebih dahulu "
            "dengan /start."

        )

        return

    photo = message.photo[
        -1
    ]

    user_proofs[
        user_id
    ] = photo.file_id

    await message.answer(

        "✅ <b>Bukti pembayaran diterima.</b>\n\n"

        "Silakan isi data berikut untuk "
        "menyesuaikan Signal AI dengan broker "
        "yang kamu gunakan:\n\n"

        "<b>Nama :</b>\n"
        "<b>Broker :</b>\n"
        "<b>Gmail :</b>\n\n"

        "Kirim format tersebut ke sini ya.",

        parse_mode="HTML"

    )


# ==========================================
# RECEIVE USER DATA
# ==========================================

@dp.message(
    F.text
)

async def receive_user_data(
    message: Message
):

    user_id = message.from_user.id

    if user_id not in user_proofs:

        return

    text = message.text.strip()

    package_key = user_packages.get(
        user_id
    )

    if not package_key:

        await message.answer(
            "Paket tidak ditemukan. Silakan /start kembali."
        )

        return

    # ======================================
    # SEND DATA TO ADMIN
    # ======================================

    admin_ids = (

        ADMIN_IDS
        if isinstance(
            ADMIN_IDS,
            (list, tuple, set)
        )
        else [ADMIN_IDS]

    )

    for admin_id in admin_ids:

        try:

            await bot.send_message(

                admin_id,

                "📋 <b>DATA MEMBER BARU</b>\n\n"

                f"👤 Telegram ID: "
                f"<code>{user_id}</code>\n"

                f"Username: "
                f"@{message.from_user.username or '-'}\n\n"

                f"📦 Paket: "
                f"<b>{PACKAGE_MAP[package_key]['label']}</b>\n\n"

                f"📝 Data Member:\n"
                f"{text}",

                parse_mode="HTML"

            )

            # ==================================
            # SEND PAYMENT PROOF
            # ==================================

            await bot.send_photo(

                admin_id,

                user_proofs[user_id],

                caption=(
                    "💳 Bukti pembayaran "
                    f"User ID {user_id}"
                )

            )

            # ==================================
            # APPROVE / REJECT
            # ==================================

            keyboard = InlineKeyboardMarkup(

                inline_keyboard=[

                    [

                        InlineKeyboardButton(

                            text="✅ TERIMA",

                            callback_data=f"approve_{user_id}"

                        ),

                        InlineKeyboardButton(

                            text="❌ TOLAK",

                            callback_data=f"reject_{user_id}"

                        )

                    ]

                ]

            )

            await bot.send_message(

                admin_id,

                "Pilih tindakan:",

                reply_markup=keyboard

            )

        except Exception as e:

            print(
                "[ADMIN] "
                "Send data error:"
            )

            print(e)

    await message.answer(

        "✅ Data kamu sudah dikirim ke admin.\n\n"

        "Silakan tunggu proses verifikasi."

    )


# ==========================================
# APPROVE
# ==========================================

@dp.callback_query(
    F.data.startswith("approve_")
)

async def approve_handler(
    callback: CallbackQuery
):

    # ======================================
    # ADMIN CHECK
    # ======================================

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(

            "Tidak memiliki akses.",

            show_alert=True

        )

        return

    # ======================================
    # USER ID
    # ======================================

    user_id = int(
        callback.data.split(
            "_"
        )[1]
    )

    # ======================================
    # PACKAGE
    # ======================================

    package_key = user_packages.get(
        user_id
    )

    if not package_key:

        await callback.answer(

            "Data paket user tidak ditemukan.",

            show_alert=True

        )

        return

    if package_key not in PACKAGE_MAP:

        await callback.answer(

            "Paket tidak valid.",

            show_alert=True

        )

        return

    package = PACKAGE_MAP[
        package_key
    ]

    # ======================================
    # DATE
    # ======================================

    now = datetime.now()

    expired = (
        now
        +
        timedelta(
            days=package["days"]
        )
    )

    # ======================================
    # REFERRAL
    # ======================================

    referral = user_referrals.get(
        user_id,
        ""
    )

    # ======================================
    # USERNAME
    # ======================================

    username = ""

    try:

        username = (
            callback.message
            .chat
            .username
            or ""
        )

    except Exception:

        username = ""

    if username:

        telegram_name = (
            f"@{username}"
        )

    else:

        telegram_name = "-"

    # ======================================
    # MEMBER DATA
    # ======================================

    member_data = {

        "telegram_id":
            user_id,

        "username":
            username,

        "nama":
            "",

        "paket":
            package["label"],

        "harga":
            package["price"],

        "register":
            now.strftime(
                "%d-%m-%Y %H:%M:%S"
            ),

        "expired":
            expired.strftime(
                "%d-%m-%Y %H:%M:%S"
            ),

        "status":
            "ACTIVE",

        "referral":
            referral

    }

    # ======================================
    # SAVE GOOGLE SHEET
    # ======================================

    saved = await asyncio.to_thread(

        save_member,

        member_data

    )

    if not saved:

        await callback.answer(

            "Gagal menyimpan ke Google Sheet.",

            show_alert=True

        )

        return

    print(
        "[APPROVED] "
        f"User {user_id} "
        f"berhasil disimpan."
    )

    # ======================================
    # GET REFERRAL GROUP
    # ======================================

    group_id = get_referral_group(
        referral
    )

    print(
        "[REFERRAL GROUP] "
        f"Referral: {referral or '-'} "
        f"-> Group ID: {group_id}"
    )

    # ======================================
    # CREATE INVITE
    # ONLY 2BLN + 3BLN
    # ======================================

    invite_link = None

    if package_has_group_access(
        package_key
    ):

        invite_link = await create_group_invite(

            group_id,

            user_id

        )

        if invite_link:

            print(
                "[GROUP INVITE] "
                f"User {user_id} -> SUCCESS"
            )

        else:

            print(
                "[GROUP INVITE] "
                f"User {user_id} -> FAILED"
            )

    else:

        print(
            "[GROUP ACCESS] "
            f"User {user_id} "
            f"paket {package['label']} "
            "tidak memiliki akses grup."
        )

    # ======================================
    # SEND USER APPROVAL MESSAGE
    # ======================================

    try:

        user_keyboard = []

        # ----------------------------------
        # AI ASSISTANT
        # ----------------------------------

        user_keyboard.append([

            InlineKeyboardButton(

                text="🤖 BUKA AI ASSISTANT",

                url=SIGNAL_BOT

            )

        ])

        # ----------------------------------
        # GROUP
        # ----------------------------------

        if invite_link:

            user_keyboard.append([

                InlineKeyboardButton(

                    text="👥 MASUK GRUP DISKUSI",

                    url=invite_link

                )

            ])

        await bot.send_message(

            user_id,

            "🎉 <b>PEMBAYARAN DISETUJUI</b>\n\n"

            f"📦 Paket: "
            f"<b>{package['label']}</b>\n"

            f"💰 Harga: "
            f"<b>Rp{package['price']:,}</b>\n\n"

            f"📅 Aktif sampai:\n"
            f"<b>{expired.strftime('%d-%m-%Y %H:%M:%S')}</b>\n\n"

            "Akses kamu:",

            reply_markup=InlineKeyboardMarkup(

                inline_keyboard=user_keyboard

            ),

            parse_mode="HTML"

        )

    except Exception as e:

        print(
            "[APPROVED] "
            "User notification error:"
        )

        print(e)

    # ======================================
    # REFERRAL GROUP NOTIFICATION
    # ======================================

    try:

        referral_text = (
            referral
            if referral
            else "-"
        )

        group_message = (

            "🔔 <b>MEMBER BARU</b>\n\n"

            f"Nama Telegram/ID : "
            f"{telegram_name} / "
            f"<code>{user_id}</code>\n"

            f"Jumlah Nominal Langganan : "
            f"<b>Rp{package['price']:,}</b>\n"

            f"Durasi Langganan : "
            f"<b>{package['label']}</b>\n"

            f"Referal : "
            f"<b>{referral_text}</b>"

        )

        await bot.send_message(

            group_id,

            group_message,

            parse_mode="HTML"

        )

        print(
            "[REFERRAL GROUP] "
            f"Notification SUCCESS "
            f"-> {group_id}"
        )

    except Exception as e:

        print(
            "[REFERRAL GROUP] "
            f"Notification FAILED "
            f"-> {group_id}"
        )

        print(e)

    # ======================================
    # REMOVE ADMIN BUTTON
    # ======================================

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception as e:

        print(
            "[ADMIN] "
            "Failed to remove buttons:"
        )

        print(e)

    # ======================================
    # ADMIN RESULT
    # ======================================

    result_text = (

        f"✅ User <code>{user_id}</code> "
        "berhasil disetujui.\n\n"

        f"📦 Paket: "
        f"<b>{package['label']}</b>\n"

        f"💰 Harga: "
        f"<b>Rp{package['price']:,}</b>\n"

        f"📅 Expired: "
        f"<b>{expired.strftime('%d-%m-%Y %H:%M:%S')}</b>\n"

        f"🔗 Referral: "
        f"<b>{referral or '-'}</b>\n"

    )

    if invite_link:

        result_text += (
            "\n👥 Invite grup berhasil dibuat."
        )

    else:

        result_text += (
            "\n🤖 Paket AI Assistant saja."
        )

    result_text += (

        "\n\n📨 Notifikasi referral: "
        "<b>TERKIRIM</b>"

    )

    await callback.message.answer(

        result_text,

        parse_mode="HTML"

    )

    await callback.answer(
        "Member disetujui."
    )


# ==========================================
# REJECT
# ==========================================

@dp.callback_query(
    F.data.startswith("reject_")
)

async def reject_handler(
    callback: CallbackQuery
):

    # ======================================
    # ADMIN CHECK
    # ======================================

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(

            "Tidak memiliki akses.",

            show_alert=True

        )

        return

    user_id = int(
        callback.data.split(
            "_"
        )[1]
    )

    # ======================================
    # USER NOTIFICATION
    # ======================================

    try:

        await bot.send_message(

            user_id,

            "❌ <b>Pembayaran belum dapat disetujui.</b>\n\n"

            "Silakan hubungi admin jika "
            "ada kesalahan pada proses pembayaran.",

            parse_mode="HTML"

        )

    except Exception as e:

        print(
            "[REJECT] "
            "Notification error:"
        )

        print(e)

    # ======================================
    # REMOVE BUTTON
    # ======================================

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception as e:

        print(
            "[REJECT] "
            "Failed remove buttons:"
        )

        print(e)

    await callback.message.answer(

        f"❌ User <code>{user_id}</code> "
        "ditolak.",

        parse_mode="HTML"

    )

    await callback.answer(
        "Pembayaran ditolak."
    )


# ==========================================
# ADMIN SEND MESSAGE
# ==========================================

@dp.message(
    Command("sent")
)

async def sent_handler(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        await message.answer(

            "Format:\n\n"

            "<code>/sent TELEGRAM_ID PESAN</code>",

            parse_mode="HTML"

        )

        return

    try:

        user_id = int(
            parts[1]
        )

        text = parts[2]

        await bot.send_message(

            user_id,

            text

        )

        await message.answer(
            "✅ Pesan berhasil dikirim."
        )

    except Exception as e:

        await message.answer(

            f"❌ Gagal mengirim:\n{e}"

        )


# ==========================================
# MAIN
# ==========================================

async def main():

    print(
        "=========================================="
    )

    print(
        "🤖 XAU AI ASSISTANT BOT STARTING..."
    )

    print(
        "=========================================="
    )

    # ======================================
    # START EXPIRED MONITOR
    # ======================================

    asyncio.create_task(
        expired_monitor()
    )

    print(
        "⏰ Expired Monitor: EVERY 10 MINUTES"
    )

    print(
        "👥 Group Access: 2BLN + 3BLN"
    )

    print(
        "🤖 AI Assistant: ALL PACKAGES"
    )

    print(
        "❌ Trial: DISABLED"
    )

    # ======================================
    # START BOT
    # ======================================

    await dp.start_polling(
        bot
    )


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
