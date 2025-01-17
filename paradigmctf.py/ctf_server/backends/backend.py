import abc
import logging
import random
import string
import time
from threading import Thread
import requests
import json

from ctf_server.databases.database import Database
from ctf_server.types import (
    DEFAULT_ACCOUNTS,
    DEFAULT_BALANCE,
    DEFAULT_DERIVATION_PATH,
    DEFAULT_MNEMONIC,
    CreateInstanceRequest,
    LaunchAnvilInstanceArgs,
    UserData,
)
from eth_account import Account
from eth_account.hdaccount import key_from_seed, seed_from_mnemonic
from foundry.anvil import anvil_setBalance
from starknet.anvil import starknet_getVersion
from web3 import Web3


class InstanceExists(Exception):
    pass


class Backend(abc.ABC):
    def __init__(self, database: Database):
        self._database = database

        Thread(
            target=self.__instance_pruner_thread,
            name=f"{self.__class__.__name__} Anvil Pruner",
            daemon=True,
        ).start()

    def __instance_pruner_thread(self):
        while True:
            try:
                for instance in self._database.get_expired_instances():
                    logging.info(
                        "pruning expired instance: %s", instance["instance_id"]
                    )

                    self.kill_instance(instance["instance_id"])
            except Exception as e:
                logging.error("failed to prune instances", exc_info=e)
            time.sleep(1)

    def launch_instance(self, args: CreateInstanceRequest) -> UserData:
        if self._database.get_instance(args["instance_id"]) is not None:
            raise InstanceExists()

        try:
            user_data = self._launch_instance_impl(args)
            self._database.register_instance(args["instance_id"], user_data)
            return user_data

        except:
            self._cleanup_instance(args)
            raise

    def _launch_instance_impl(self, args: CreateInstanceRequest) -> UserData:
        pass

    def _cleanup_instance(self, args: CreateInstanceRequest):
        pass

    @abc.abstractmethod
    def kill_instance(self, id: str) -> UserData:
        pass

    def _generate_rpc_id(self, N: int = 24) -> str:
        return "".join(
            random.SystemRandom().choice(string.ascii_letters) for _ in range(N)
        )

    def __derive_account(self, derivation_path: str, mnemonic: str, index: int) -> str:
        seed = seed_from_mnemonic(mnemonic, "")
        private_key = key_from_seed(seed, f"{derivation_path}{index}")

        return Account.from_key(private_key)

    def _prepare_node(self, args: LaunchAnvilInstanceArgs, web3: Web3):
        while not web3.is_connected():
            time.sleep(0.1)
            continue

        for i in range(args.get("accounts", DEFAULT_ACCOUNTS)):
            anvil_setBalance(
                web3,
                self.__derive_account(
                    args.get("derivation_path", DEFAULT_DERIVATION_PATH),
                    args.get("mnemonic", DEFAULT_MNEMONIC),
                    i,
                ).address,
                hex(int(args.get("balance", DEFAULT_BALANCE) * 10**18)),
            )

    def _prepare_node_starknet(self, args: LaunchAnvilInstanceArgs, web3: Web3):
        while True:
            try:
                starknet_getVersion(web3)
                break
            except:
                time.sleep(0.1)

    def _prepare_node_nitro(self, args: LaunchAnvilInstanceArgs, web3: Web3):
        while not web3.is_connected():
            time.sleep(0.1)
            continue

        pk = "0xb6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659"
        acc = web3.eth.account.from_key(pk)

        for i in range(args.get("accounts", DEFAULT_ACCOUNTS)):
            transaction = {
                'from': acc.address,
                'to': self.__derive_account(
                    args.get("derivation_path", DEFAULT_DERIVATION_PATH),
                    args.get("mnemonic", DEFAULT_MNEMONIC),
                    i,
                ).address,
                'value': 250 * 10 ** 18,
                'nonce': web3.eth.get_transaction_count(acc.address),
                'gas': 1000000,
                'chainId': web3.eth.chain_id,
                'gasPrice': web3.eth.gas_price
            }

            signed = web3.eth.account.sign_transaction(transaction, pk)

            web3.eth.send_raw_transaction(signed.rawTransaction)
