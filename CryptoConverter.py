import datetime, time
import gi
import json

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from pycoingecko import CoinGeckoAPI


class Handler:
    def __init__(self, builder, default):
        self.source_unit = builder.get_object('source_unit')
        self.conv_unit = builder.get_object('conv_unit')
        self.source_amount = builder.get_object('source_amount')
        self.conv_result = builder.get_object('conv_result')
        self.time_update = builder.get_object('time_update')
        self.cg = CoinGeckoAPI()
        self.current_rate = None
        self.current_crypto = None
        self.current_currency = None
        self.auto_update = True
        self.crypto_ids = load_supported_cryptos()
        self.currencies = load_supported_vs_currencies()
        populate_combobox(self.conv_unit, self.currencies, default)
        self.convertValue()

    def onDestroy(self, *args):
        Gtk.main_quit()

    def toggleAutoUpdate(self, *args):
        self.auto_update = not self.auto_update
        self.updateValues()
    
    def updateValues(self, *args):
        # TODO 5
        source = self.source_unit.get_text().lower()
        conv = self.currencies[self.conv_unit.get_active()].lower()
        try:
            amount = float(self.source_amount.get_text())
        except ValueError:
            return 0

        if source in self.crypto_ids:
            cid = self.crypto_ids[source]
            data = self.cg.get_price(ids=cid, vs_currencies=conv)
            self.current_rate = data[cid][conv]
        else:
            return 0

        # TODO 3
        self.conv_result.set_text(f"{amount * self.current_rate:.8f}")
        update_time_label(self.time_update)

    def convertValue(self, *args):
        source = self.source_unit.get_text().lower()
        conv = self.currencies[self.conv_unit.get_active()].lower()
        try:
            amount = float(self.source_amount.get_text())
        except ValueError:
            amount = None

        # Get the price from CG API and save it if crypto or currency changed
        if self.current_crypto != source or self.current_currency != conv:
            if source in self.crypto_ids:
                cid = self.crypto_ids[source]
                data = self.cg.get_price(ids=cid, vs_currencies=conv)
                self.current_rate = data[cid][conv]
                self.current_crypto = source
                self.current_currency = conv
            else:
                # TODO 4
                amount = None

        if amount:
            # TODO 3
            self.conv_result.set_text(f"{amount * self.current_rate:.8f}")
        else:
            self.conv_result.set_text("N/A")
        update_time_label(self.time_update)


def update_time_label(label):
    if time.localtime().tm_isdst:
        utc_offset_sec = time.altzone
    else:
        utc_offset_sec = time.timezone

    utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
    now = datetime.datetime.now()
    now = now.replace(tzinfo=datetime.timezone(offset=utc_offset)).isoformat()
    now = now.split('.')[0].replace('T', ' ')

    label.set_text(f"Powered by CoinGecko\nLast updated: {now}")


def update_conf_files():
    # Fetch all the supported cryptos from CoinGecko and saves them using JSON
    cg = CoinGeckoAPI()
    data = cg.get_coins_list()
    vs_currencies = cg.get_supported_vs_currencies()

    supported_cryptos = {d['symbol']: d['id'] for d in data}

    with open('conf/supported_cryptos.json', 'w') as json_file:
        json.dump(supported_cryptos, json_file)

    with open('conf/supported_vs_currencies.json', 'w') as json_file:
        json.dump(vs_currencies, json_file)


def load_supported_cryptos():
    # Load the supported cryptocurrencies from a local JSON file (faster)
    with open('conf/supported_cryptos.json', 'r') as json_file:
        data = json.load(json_file)    
    
    return data


def load_supported_vs_currencies():
    with open('conf/supported_vs_currencies.json', 'r') as json_file:
        data = json.load(json_file)

    return sorted([d.upper() for d in data])


def populate_combobox(cbox, values, default):
    values_store = Gtk.ListStore(str)
    
    for value in values:
        values_store.append([value])

    cbox.set_model(values_store)
    cbox.set_active(values.index(default))


def main():
    builder = Gtk.Builder()
    builder.add_from_file('layout.glade')

    window = builder.get_object('main_window')

    builder.connect_signals(Handler(builder, 'USD'))

    window.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()

# TODO 1: Remember the last currency selected instead of USD
# TODO 2: Add a background service/thread to update the config files once in a 
#         while. Update it once when started, update values when received and
#         make sure to not run it more than once every 24h.
# TODO 3: Format should adapt to the currency precision (8 for BTC, 2 for EUR)
# TODO 4: Showing that the typed crypto doesn't exist (red border?)
# TODO 5: Auto-update feature : background thread that runs the updateValues
#         method every minute if self.auto_update is True
# TODO 6: Add a way to select either a custom rate/price (useful for exchanges)
#         or the live one provided by CoinGecko (use auto-update if selected)
# TODO 7: Find a way to improve the latency induced by quering the API with
#         every letter typed (caching, wait for whem user stopped typing, 
#         fetch the api in background and display a loading icon?)
# TODO 8: Write the readme