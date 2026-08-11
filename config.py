BOT_TOKEN = "8760132995:AAEjQjCMqcMdb_nBaieqoIRDQcpfedw8nSI"

# ==========================================
# ADMIN
# ==========================================

ADMIN_ID = 1305881282

ADMIN_IDS = [
    1305881282,
]


# ==========================================
# PAYMENT GROUP
# ==========================================
# Grup utama / fallback.
#
# Jika referral:
# - tidak ada
# - tidak ditemukan di REFERRAL_GROUPS
#
# maka hasil APPROVE dikirim ke grup ini.

PAYMENT_GROUP_ID = -1003934607716


# ==========================================
# BOT
# ==========================================

SIGNAL_BOT = "https://t.me/AIGOLDASSISTANT_BOT?start"


# ==========================================
# REFERRAL GROUPS
# ==========================================
#
# Format:
#
# "NAMA_REFERRAL": GROUP_ID
#
# Referral dari website akan dicocokkan
# dengan nama di bawah ini.
#
# Contoh link:
# https://t.me/AIGOLDASSISTANT_BOT?start=BUDI
#
# Jika BUDI ada di sini:
#   APPROVE -> grup BUDI
#
# Jika BUDI tidak ada:
#   APPROVE -> PAYMENT_GROUP_ID

REFERRAL_GROUPS = {

    "REF_YURI": -1004415837135,
    "REF_ILHAM": -5539361849,
}


# ==========================================
# DEFAULT
# ==========================================

DEFAULT_REFERRAL = None
