import json


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
