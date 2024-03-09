from web3 import Web3
from web3.types import RPCResponse


def check_error(resp: RPCResponse):
    if "error" in resp:
        raise Exception("rpc exception", resp["error"])


def starknet_getVersion(web3: Web3):
    check_error(web3.provider.make_request("starknet_specVersion", []))
