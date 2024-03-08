from starknet_py.net.full_node_client import FullNodeClient
import requests


def starknet_setBalance(
    web3: FullNodeClient,
    addr: str,
    balance: int,
):
    requests.post(web3.url + '/mint', json = {
        'address': addr,
        'amount': balance
    })

