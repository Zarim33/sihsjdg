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


async def eur_to_crypto(eur_amount, crypto_id="bitcoin"):
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
                crypto_amount = eur_amount / rate
                return f"{crypto_amount:.6f}"
            except KeyError:
                print("Invalid crypto ID or API error.")
                return None


@bot.on(events.NewMessage(pattern="/start"))
async def st(e):
    data: dict = Var.products()
    _lst = [Button.inline(data[x]["title"], data=f"buy_{x}") for x in data.keys()]
    button = list(zip(_lst[::2], _lst[1::2]))
    button.append([_lst[-1]]) if len(_lst) % 2 else None
    await e.reply("**Welcome. Select the access you want to unlock:**", buttons=button)


@bot.on(events.callbackquery.CallbackQuery(data=re.compile("buy_(.*)")))
async def _(e):
    pid = e.pattern_match.group(1).decode("utf-8")
    data: dict = Var.wallets
    _lst = [Button.inline(x, data=f"{x}_{pid}") for x in data.keys()]
    button = list(zip(_lst[::2], _lst[1::2]))
    button.append([_lst[-1]]) if len(_lst) % 2 else None
    await e.edit("__Select your payment currency: 💳__", buttons=button)


@bot.on(events.callbackquery.CallbackQuery(data=re.compile("(.*)_(.*)")))
async def _(e):
    currency = e.pattern_match.group(1).decode("utf-8").strip()
    pid = e.pattern_match.group(2).decode("utf-8").strip()
    
    if currency not in Var.wallets:
        await e.answer("Invalid currency selected.", alert=True)
        return

    euro = Var.products(pid)["price"]
    crypto_id = COIN_GECKO_ID.get(currency)
    crypto_amount = await eur_to_crypto(euro, crypto_id)

    if crypto_amount is None:
        await e.edit("⚠️ Failed to fetch live rate. Try again later.")
        return

    uid = secrets.token_hex(6)
    PAYMENT_CONF[uid] = {
        "client_id": e.sender_id,
        "client_name": get_display_name(await bot.get_entity(int(e.sender_id))),
        "username": e.sender.username or "N/A",
        "time": datetime.now().strftime("%H:%M:%S"),
        "price": f"{crypto_amount} {currency}",
        "pid": pid,
    }

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
    if uid not in PAYMENT_CONF:
        await e.edit("❌ Error: Invalid payment session. Please restart with /start.")
        return

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
        ),
    )
    await e.edit("✅ Access will be unlocked after manual verification.")


bot.loop.run_forever()
