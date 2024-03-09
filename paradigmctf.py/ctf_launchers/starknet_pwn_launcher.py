import os
import json
import requests
from ctf_launchers.launcher import Action, Launcher, ORCHESTRATOR_HOST, CHALLENGE
from ctf_launchers.team_provider import TeamProvider, get_team_provider
from ctf_server.types import UserData, get_privileged_web3

FLAG = os.getenv("FLAG", "PCTF{flag}")


class StarknetPwnChallengeLauncher(Launcher):
    def __init__(
        self,
        project_location: str = "challenge/project",
        provider: TeamProvider = get_team_provider(),
    ):
        super().__init__(
            'starknet',
            project_location,
            provider,
            [
                Action(name="get flag", handler=self.get_flag),
            ],
        )

    def get_flag(self) -> int:
        instance_body = requests.get(
            f"{ORCHESTRATOR_HOST}/instances/{self.get_instance_id()}").json()
        if not instance_body['ok']:
            print(instance_body['message'])
            return 1

        user_data = instance_body['data']

        if not self.is_solved(
            user_data, user_data['metadata']["challenge_address"]
        ):
            print("are you sure you solved it?")
            return 1

        print(FLAG)
        return 0

    def is_solved(self, user_data: UserData, addr: str) -> bool:
        web3 = get_privileged_web3(user_data, "main")

        x = requests.post(web3.provider.endpoint_uri + "/rpc", json={
            "id": 1,
            "jsonrpc": "2.0",
            "method": "starknet_call",
            "params": [
                {
                    "contract_address": addr,
                    "calldata": [],
                    "entry_point_selector": "0x1f8ddd388f265b0bcab25a3e457e789fe182bdf8ede59d9ef42b3158a533c8"
                },
                "latest"
            ]
        })

        solved = True if json.loads(x.text)['result'][0] == "0x0" else False

        return solved
