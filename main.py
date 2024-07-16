
from datetime import datetime

from base import Credential
from gas_station_system import GasStationSystem


if __name__ == '__main__':
    cred = Credential(
        url='https://test-app.avtoversant.ru',
        login='test',
        password='v78ilRB63Y1b',
        contracts="001,003",
    )
    system = GasStationSystem()
    system.auth(cred)
    transactions = system.get_transactions(
        from_date=datetime(2024, 1, 1),
        to_date=datetime(2024, 7, 1),
    )

    print('Transactions count', len(transactions))

    for tr in transactions[:10]:
        print(tr)

    