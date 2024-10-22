import abc
import os
import traceback
from dataclasses import dataclass
from typing import Callable, Dict, List
import requests
import json

import requests
from ctf_launchers.team_provider import TeamProvider
from ctf_launchers.utils import deploy, deploy_cairo, deploy_nitro, http_url_to_ws
from ctf_server.types import (
    CreateInstanceRequest,
    DaemonInstanceArgs,
    LaunchAnvilInstanceArgs,
    UserData,
    get_player_account,
    get_privileged_web3,
)
from eth_account.hdaccount import generate_mnemonic

CHALLENGE = os.getenv("CHALLENGE", "challenge")
ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST", "http://orchestrator:7283")
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "http://127.0.0.1:8545")

ETH_RPC_URL = os.getenv("ETH_RPC_URL")
TIMEOUT = int(os.getenv("TIMEOUT", "720"))


@dataclass
class Action:
    name: str
    handler: Callable[[], int]


class Launcher(abc.ABC):
    def __init__(
        self, type: str, project_location: str, provider: TeamProvider, actions: List[Action] = []
    ):
        self.type = type
        self.project_location = project_location
        self.__team_provider = provider

        self._actions = [
            Action(name="launch new instance", handler=self.launch_instance),
            Action(name="kill instance", handler=self.kill_instance),
        ] + actions

    def run(self):
        self.team = self.__team_provider.get_team()
        if not self.team:
            exit(1)

        self.mnemonic = generate_mnemonic(12, lang="english")

        for i, action in enumerate(self._actions):
            print(f"{i+1} - {action.name}")

        try:
            handler = self._actions[int(input("action? ")) - 1]
        except:
            print("can you not")
            exit(1)

        try:
            exit(handler.handler())
        except Exception as e:
            traceback.print_exc()
            print("an error occurred", e)
            exit(1)

    def get_anvil_instances(self) -> Dict[str, LaunchAnvilInstanceArgs]:
        return {
            "main": self.get_anvil_instance(),
        }

    def get_daemon_instances(self) -> Dict[str, DaemonInstanceArgs]:
        return {}

    def get_anvil_instance(self, **kwargs) -> LaunchAnvilInstanceArgs:
        if not "balance" in kwargs:
            kwargs["balance"] = 1000
        if not "accounts" in kwargs:
            kwargs["accounts"] = 2
        # if not "fork_url" in kwargs:
        #     kwargs["fork_url"] = ETH_RPC_URL
        if not "mnemonic" in kwargs:
            kwargs["mnemonic"] = self.mnemonic
        return LaunchAnvilInstanceArgs(
            **kwargs,
        )

    def get_instance_id(self) -> str:
        return f"chal-{CHALLENGE}-{self.team}".lower()

    def update_metadata(self, new_metadata: Dict[str, str]):
        resp = requests.post(
            f"{ORCHESTRATOR_HOST}/instances/{self.get_instance_id()}/metadata",
            json=new_metadata,
        )
        body = resp.json()
        if not body["ok"]:
            print(body["message"])
            return 1

    def launch_instance(self) -> int:
        print("creating private blockchain...")
        body = requests.post(
            f"{ORCHESTRATOR_HOST}/instances",
            json=CreateInstanceRequest(
                type=self.type,
                instance_id=self.get_instance_id(),
                timeout=TIMEOUT,
                anvil_instances=self.get_anvil_instances(),
                daemon_instances=self.get_daemon_instances(),
            ),
        ).json()
        if body["ok"] == False:
            raise Exception(body["message"])

        user_data = body["data"]

        print("deploying challenge...")

        if self.type == "starknet":
            web3 = get_privileged_web3(user_data, "main")

            credentials = [["0x64b48806902a367c8598f4f95c305e8c1a1acba5f082d294a43793113115691", "0x71d7bb07b9a64f6f78ac4c816aff4da9"], ["0x78662e7352d062084b0010068b99288486c2d8b914f6e2a55ce945f8792c8b1", "0xe1406455b7d66b1690803be066cbe5e"]]

            challenge_addr = self.deploy_cairo(user_data, credentials)
            priv_key = credentials[1][1]
        elif self.type == "nitro":
            challenge_addr = self.deploy_nitro(user_data, self.mnemonic)
            priv_key = get_player_account(self.mnemonic).key.hex()
        else:
            challenge_addr = self.deploy(user_data, self.mnemonic)
            priv_key = get_player_account(self.mnemonic).key.hex()

        self.update_metadata(
            {"mnemonic": self.mnemonic, "challenge_address": challenge_addr}
        )

        PUBLIC_WEBSOCKET_HOST = http_url_to_ws(PUBLIC_HOST)

        print()
        print(f"your private blockchain has been set up")
        print(
            f"it will automatically terminate in {round(TIMEOUT/60)} minutes")
        print(f"---")
        print(f"rpc endpoints:")
        for id in user_data["anvil_instances"]:
            print(f"    - {PUBLIC_HOST}/{user_data['external_id']}/{id}")
            print(
                f"    - {PUBLIC_WEBSOCKET_HOST}/{user_data['external_id']}/{id}/ws")

        if self.type == "starknet":
            print(f"player address:     {credentials[1][0]}")
        print(
            f"private key:        {priv_key}")
        print(f"challenge contract: {challenge_addr}")
        return 0

    def kill_instance(self) -> int:
        resp = requests.delete(
            f"{ORCHESTRATOR_HOST}/instances/{self.get_instance_id()}")
        body = resp.json()

        print(body["message"])
        return 1

    def deploy(self, user_data: UserData, mnemonic: str) -> str:
        web3 = get_privileged_web3(user_data, "main")

        return deploy(
            web3, self.project_location, mnemonic, env=self.get_deployment_args(
                user_data)
        )

    def deploy_cairo(self, user_data: UserData, credentials: list) -> str:
        web3 = get_privileged_web3(user_data, "main")

        return deploy_cairo(web3, self.project_location, credentials, env=self.get_deployment_args(user_data))

    def deploy_nitro(self, user_data: UserData, mnemonic: str) -> str:
        web3 = get_privileged_web3(user_data, "main")

        return deploy_nitro(
            web3, self.project_location, mnemonic, env=self.get_deployment_args(
                user_data)
        )

    def get_deployment_args(self, user_data: UserData) -> Dict[str, str]:
        return {}

    def get_credentials(self, url: str) -> list:
        x = requests.get(url + '/predeployed_accounts')
        data = json.loads(x.text)

        system = []
        player = []

        system.append(data[0]['address'])
        system.append(data[0]['private_key'])

        player.append(data[1]['address'])
        player.append(data[1]['private_key'])

        return [system, player]
