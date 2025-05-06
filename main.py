import json
import time


class Conf:
    def __init__(self) -> None:
        text = open("example.json", "r+", encoding="utf-8").read()
        try:
            self.data = json.loads(text)
        except BaseException:
            try:
                self.data = eval(text)
            except BaseException:
                exit("Invalid secrets.json.")

    def products(self, pid: str = None):
        if value := self.data["products"].get(pid):
            return value
        return self.data["products"]

    @property
    def owner(self):
        return int(self.data["owner_id"])

    @property
    def wallets(self):
        return self.data["crypto_wallets_adrs"]

    @property
    def BOT_TOKEN(self):
        return self.data["bot_token"]


Var = Conf()

from telethon import TelegramClient, events, Button
from telethon.utils import get_display_name
from config import Var
from datetime import datetime
import re, aiohttp, secrets

try:
    bot = TelegramClient(None, 2040, "b18441a1ff607e10a989891a5462e627").start(
        bot_token=Var.BOT_TOKEN
    )
    print("Bot Started...")
except Exception as er:
    print(er)
    exit()

COIN_GECKO_ID = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "USDT": "tether"}
PAYMENT_CONF = {}
ADMIN_ORDER_SLIP = """
**✅ Payment Confirmed ✅**

**🪪 Name:** {}
**🆔 ID:** `{}`
**🆔 Username:** @{}

**💳 Temp Order No.:** #{}
**⏱ Time:** `{}`
**💰 Price:** `{}`
**📥 Service:** `{}`
"""

APS = """
** ⚠️ Alert User Reaches Payment Screen**
**🪪 Name:** {}
**🆔 ID:** `{}`
**🆔 Username:** @{}

**⏱ Time:** `{}`
**💰 Price:** `{}`
**📥 Service:** `{}`
"""


# Global cache dictionary
_cache = {"timestamp": 0, "rate": {}}


async def eur_to_crypto(eur_amount, crypto_id="bitcoin"):
    current_time = time.time()
    # Check if we have a recent cached rate
    if crypto_id in _cache["rate"] and current_time - _cache["timestamp"] < 60:
        rate = _cache["rate"][crypto_id]
    else:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": crypto_id, "vs_currencies": "eur"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"HTTP error: {response.status}")
                    return None
                data = await response.json()
                try:
                    rate = data[crypto_id]["eur"]
                    _cache["timestamp"] = current_time
                    _cache["rate"][crypto_id] = rate
                except BaseException:
                    print("Invalid crypto ID or API error.")
                    return None

    crypto_amount = eur_amount / rate
    return f"{crypto_amount:.6f}"


@bot.on(events.NewMessage(pattern="/start"))
async def st(e):
    data: dict = Var.products()
    _lst = [Button.inline(data[x]["title"], data=f"buy_{x}") for x in data.keys()]
    button = list(zip(_lst[::2], _lst[1::2]))
    button.append(
        [_lst[-(z + 1)] for z in reversed(range(len(_lst) - ((len(_lst) // 2) * 2)))]
    )
    await e.reply("**Welcome. Select the access you want to unlock:**", buttons=button)


@bot.on(events.callbackquery.CallbackQuery(data=re.compile("buy_(.*)")))
async def _(e):
    pid = e.pattern_match.group(1).decode("utf-8")
    data: dict = Var.wallets
    _lst = [Button.inline(x, data=f"{x}_{pid}") for x in data.keys()]
    button = list(zip(_lst[::2], _lst[1::2]))
    button.append(
        [_lst[-(z + 1)] for z in reversed(range(len(_lst) - ((len(_lst) // 2) * 2)))]
    )
    await e.edit("__Select your payment currency: 💳__", buttons=button)


@bot.on(events.callbackquery.CallbackQuery(data=re.compile("(.*)_(.*)")))
async def _(e):
    currency = e.pattern_match.group(1).decode("utf-8").strip()
    if currency not in Var.wallets.keys():
        return
    pid = e.pattern_match.group(2).decode("utf-8").strip()
    euro = Var.products(pid)["price"]
    crypto_amount = await eur_to_crypto(euro, COIN_GECKO_ID[currency])
    uid = secrets.token_hex(6)
    PAYMENT_CONF[uid] = {
        "client_id": e.sender_id,
        "client_name": get_display_name(await bot.get_entity(int(e.sender_id))),
        "username": e.sender.username or "N/A",
        "time": datetime.now().strftime("%H:%M:%S"),
        "price": f"{crypto_amount} {currency}",
        "pid": pid,
    }
    # adtxt = APS.format(
    #     PAYMENT_CONF[uid]["client_name"],
    #     PAYMENT_CONF[uid]["client_id"],
    #     PAYMENT_CONF[uid]["username"],
    #     PAYMENT_CONF[uid]["time"],
    #     PAYMENT_CONF[uid]["price"],
    #     Var.products(pid)["title"],
    # )
    # await bot.send_message(Var.owner, adtxt)
    await e.edit(
        f"🛒 **Purchase Summary**\n\n"
        f"• Product: `{Var.products(pid)['title']}`\n"
        f"• Amount to Pay: `{crypto_amount}` **{currency}**\n"
        f"• Live Rate: `€{euro}` ≈ `{crypto_amount}` **{currency}**\n\n"
        f"🏦 **Payment Address**\n"
        f"`{Var.wallets[currency]}`\n\n"
        f"**Once payment is complete, please confirm by pressing the button below:**",
        buttons=[[Button.inline("🔒 Transaction Completed", data=f"cliconf_{uid}")]],
    )


@bot.on(events.callbackquery.CallbackQuery(data=re.compile("cliconf_(.*)")))
async def _(e):
    uid = e.pattern_match.group(1).decode("utf-8")
    data = PAYMENT_CONF[uid]
    await bot.send_message(
        Var.owner,
        ADMIN_ORDER_SLIP.format(
            data["client_name"],
            data["client_id"],
            data["username"],
            uid,
            data["time"],
            data["price"],
            Var.products(data["pid"])["title"],
            # "N/A",
        ),
        # buttons=[[Button.inline("Confrim!!", data=f"admconf_{uid}")]],
    )
    await e.edit(
        "✅ Access will be unlocked after manual verification."
        # "__🤝 Thanks For Placing Order 🤝, You Will Get Your Order Onces Confrimed By Admins__"
    )


# @bot.on(events.callbackquery.CallbackQuery(data=re.compile("admconf_(.*)")))
# async def _(e):
#     if e.sender_id != Var.owner:
#         return
#     uid = e.pattern_match.group(1).decode("utf-8")
#     data = PAYMENT_CONF[uid]
#     txt = ADMIN_ORDER_SLIP.format(
#         data["client_name"],
#         data["client_id"],
#         data["username"],
#         uid,
#         data["time"],
#         data["price"],
#         Var.products(data["pid"])["title"],
#         "CONFRIMED",
#     )
#     await bot.send_message(int(data["client_id"]), txt)
#     await bot.send_message(
#         int(data["client_id"]), "**✅ Payment confirmed. Access granted.**"
#     )
#     await e.edit(txt)


bot.loop.run_forever()
