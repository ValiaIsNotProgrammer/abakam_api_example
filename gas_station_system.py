from datetime import datetime
from typing import Any, Union

import requests
from bs4 import BeautifulSoup
import html

from base import BaseSystem, Credential, Transaction, InvalidCredentialsError, Point, Station
from utils import binary_search_by_names, get_fixed_unicode_escape


class GasStationSystem(BaseSystem):
    base_url: str = 'https://test-app.avtoversant.ru'
    login_endpoint: str = '/account/login'
    transaction_endpoint: str = '/account/transactions?page_size=100'
    station_endpoint: str = '/abakam/gasstations/stations'
    headers: dict = {
        'X-WINTER-REQUEST-HANDLER': None,
        'X-Requested-With': 'XMLHttpRequest'
    }
    MultiFormEntry = dict[str, Union[None, tuple[None, str]]]

    def __init__(self):
        self.last_page = 0
        self.stations = []
        super().__init__()

    def is_valid_user(self, credential: Credential) -> bool:
        data = self._get_auth_data_from_credential(credential)
        ajax_handler = "onSignin"
        r = self._post_ajax(endpoint=self.login_endpoint, data=data, ajax_handler=ajax_handler)
        if r.status_code != 200:
            return False
        credential.token = r.cookies["user_auth"]
        return True

    def auth(self, credential: Credential) -> None:
        self.credential = credential
        if not self.is_valid_user(credential):
            raise InvalidCredentialsError("Not a valid credential")
        if not credential.url:
            credential.url = self.base_url
    
    def get_transactions(self, from_date: datetime, to_date: datetime) -> list[Transaction]:

        page = 1
        soup = self._get_soup(from_date=from_date, to_date=to_date, page=page)
        self.last_page = self.get_last_page(soup)
        self.stations = sorted(self.get_stations(), key=lambda x: int(x['name']))
        transactions = self._parse_transactions(soup.find("table"))
        total_transactions = transactions

        while self.last_page > page:
            print("page:", page)
            page += 1
            soup = self._get_soup(from_date=from_date, to_date=to_date, page=page)
            transactions = self._parse_transactions(soup.find("table"))
            total_transactions += transactions
        return total_transactions

    def get_stations(self) -> list[dict[str, Any]]:
        r = self._get(self.station_endpoint)
        return r.json()

    def get_station_by_station_name(self, station_name: str) -> Station:
        station = binary_search_by_names(self.stations, station_name)
        return Station(**self._get_clean_station(station))

    def _parse_transactions(self, table) -> list[Transaction]:
        transactions = []

        for row in table.find_all('tr'):
            t = Transaction()
            cells = []
            for column in row.find_all('td'):
                cell = column.text.replace("n", "").strip()
                cells.append(cell)
            t.code, t.date, contract, t.card, station_name, broken_service_name, t.volume, t.sum = cells
            t.service = get_fixed_unicode_escape(broken_service_name)
            if (contract not in self.credential.contracts.split(",") and self.credential.contracts) or\
               (t.service == "Пополнение баланса"):
                continue
            t.station, t.credential = self.get_station_by_station_name(station_name), self.credential
            transactions.append(t)

        return transactions

    def _get_soup(self, *, from_date: datetime, to_date: datetime, page: int) -> BeautifulSoup:
        data = self._get_transactions_data_from_date(from_date=from_date, to_date=to_date, page=page)
        ajax_handler = "onFilter"
        r = self._post_ajax(endpoint=self.transaction_endpoint, data=data, ajax_handler=ajax_handler)
        soup = BeautifulSoup(html.unescape(r.text.replace("\\", "")), 'html.parser')
        return soup

    def _post_ajax(self, endpoint: str, data: MultiFormEntry, ajax_handler: str) -> requests.Response:
        endpoint = endpoint if endpoint.startswith("/") else "/" + endpoint
        self.headers["X-WINTER-REQUEST-HANDLER"] = ajax_handler
        cookies = {}
        if self.credential.token:
            cookies = {"user_auth": self.credential.token}
        r = requests.post(self.base_url + endpoint, headers=self.headers, files=data, cookies=cookies)
        return r

    def _get(self, endpoint: str) -> requests.Response:
        "Without authentication"
        endpoint = endpoint if endpoint.startswith("/") else "/" + endpoint
        r = requests.get(self.base_url + endpoint)
        return r

    @staticmethod
    def _get_auth_data_from_credential(credential: Credential) -> MultiFormEntry:
        multiform_data = {
            'login': (None, credential.login),
            'password': (None, credential.password),
            'remember': (None, "1")
            }
        return multiform_data

    @staticmethod
    def _get_transactions_data_from_date(*, from_date: datetime, to_date: datetime, page: int) -> MultiFormEntry:
        multiform_data = {
            'start_date': (None, from_date.strftime("%Y-%m-%d")),
            'end_date': (None, to_date.strftime("%Y-%m-%d")),
            'start_time': (None, ""),
            'end_time': (None, ""),
            'page': (None, str(page)),
            }
        return multiform_data

    @staticmethod
    def get_last_page(soup) -> int:
        pagination_tag = soup.find('ul', class_="pagination justify-content-center")
        if not pagination_tag:
            return 1
        last_page = pagination_tag.find_all('li')[-2].text.replace("n", "")
        return int(last_page)

    @staticmethod
    def _get_clean_station(station: dict) -> dict:
        new_station = {}
        new_station["code"] = station["id"]
        new_station["name"] = station["name"]
        # new_station["brand"] = station["brand"]
        new_station["address"] = station["address"]
        new_station["point"] = station['point'] = Point(lat=station["lat"], lng=station["lng"])
        return new_station
