import datetime, time
import gi
import json
import threading
import numpy as np

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from pycoingecko import CoinGeckoAPI


class ConfigUpdater(threading.Thread):
    def __init__(self, handler):
        threading.Thread.__init__(self, target=update_conf_files, 
                                  args=(handler,))
        self.start()


class Handler:
    def __init__(self, builder):
        # Load the config file or the defaults if it fails
        try:
            with open('conf/config.json', 'r') as json_file:
                config = json.load(json_file)
        except FileNotFoundError:
            config = {'cryptocurrency': 'BTC', 'vs_currency': 'USD'}
        
        self.cg = CoinGeckoAPI()
        self.source_unit = builder.get_object('source_unit')
        self.conv_unit = builder.get_object('conv_unit')
        self.source_amount = builder.get_object('source_amount')
        self.conv_result = builder.get_object('conv_result')
        self.time_update = builder.get_object('time_update')
        self.crypto_completion = builder.get_object('crypto_completion')
        self.currency_completion = builder.get_object('currency_completion')
        self.current_rate = None
        self.current_crypto = config['cryptocurrency']
        self.current_currency = config['vs_currency']
        self.auto_update = True
        self.crypto_ids = load_supported_cryptos()
        self.currencies = load_supported_vs_currencies()
        self.source_unit.set_text(self.current_crypto)
        self.conv_unit.set_text(self.current_currency)
        
        if self.crypto_ids is None or self.currencies is None:
            # Download the config files directly from the API
            update_conf_files(self)
        
        else:
            # Updating the UI with the config values
            populate_completion(self.crypto_completion, self.crypto_ids)
            populate_completion(self.currency_completion, self.currencies)

            # Update the config files in the background
            ConfigUpdater(self)

        # Get and display the data received from the API
        self.updateValues()

    def onDestroy(self, *args):
        # Saves the active crypto and currency in the config file
        config = {'vs_currency': self.current_currency.upper(),
                  'cryptocurrency': self.current_crypto.upper()}

        with open('conf/config.json', 'w') as json_file:
            json.dump(config, json_file)

        Gtk.main_quit()

    def toggleAutoUpdate(self, *args):
        self.auto_update = not self.auto_update
        self.updateValues()
    
    def updateValues(self, *args):
        # TODO 5
        source = self.source_unit.get_text().lower()
        conv = self.conv_unit.get_text().lower()
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

        self.conv_result.set_text(convert(self.current_rate, amount))
        update_time_label(self.time_update)

    def convertValue(self, *args):
        source = self.source_unit.get_text().lower()
        conv = self.conv_unit.get_text().lower()

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
            self.conv_result.set_text(convert(self.current_rate, amount))
        else:
            self.conv_result.set_text("N/A")
        update_time_label(self.time_update)


def convert(rate, amount):
    # Remove the scientific notation and get the precision returned by the API
    str_rate = np.format_float_positional(rate, trim='-')
    if '.' in str_rate:
        precision = len(str_rate.split('.')[1])
    else:
        precision = 0

    return np.format_float_positional(round(rate * amount, precision), trim='-')


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


def update_conf_files(handler):
    # Fetch all the supported cryptos from CoinGecko and saves them using JSON
    cg = CoinGeckoAPI()
    data = cg.get_coins_list()
    vs_currencies = cg.get_supported_vs_currencies()

    supported_cryptos = {d['symbol']: d['id'] for d in data}

    with open('conf/supported_cryptos.json', 'w') as json_file:
        json.dump(supported_cryptos, json_file)

    with open('conf/supported_vs_currencies.json', 'w') as json_file:
        json.dump(vs_currencies, json_file)

    # Update the values loaded from previous config file
    handler.crypto_ids = supported_cryptos
    handler.currencies = sorted([vsc.upper() for vsc in vs_currencies])

    populate_completion(handler.crypto_completion, handler.crypto_ids)
    populate_completion(handler.currency_completion, handler.currencies)


def load_supported_cryptos():
    # Load the supported cryptocurrencies from a local JSON file (faster)
    try:
        with open('conf/supported_cryptos.json', 'r') as json_file:
            data = json.load(json_file)
        return data

    except FileNotFoundError:
        return None


def load_supported_vs_currencies():
    try:
        with open('conf/supported_vs_currencies.json', 'r') as json_file:
            data = json.load(json_file)
        return sorted([d.upper() for d in data])
    
    except FileNotFoundError:
        return None


def populate_completion(completion, values):
    values_store = Gtk.ListStore(str)

    for value in values:
        values_store.append([value.upper()])
    
    completion.set_model(values_store)
    completion.set_text_column(0)


def main():
    builder = Gtk.Builder()
    builder.add_from_file('layout.glade')

    window = builder.get_object('main_window')

    builder.connect_signals(Handler(builder))

    window.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
