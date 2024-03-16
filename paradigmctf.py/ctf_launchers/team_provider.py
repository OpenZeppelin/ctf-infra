import abc
import os
import base64
from dataclasses import dataclass
from typing import Optional

import requests
from cryptography.fernet import Fernet

def encrypt(message: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(message)

def decrypt(token: bytes, key: bytes) -> bytes:
    return Fernet(key).decrypt(token)


class TeamProvider(abc.ABC):
    @abc.abstractmethod
    def get_team(self) -> Optional[str]:
        pass


class TicketTeamProvider(TeamProvider):
    @dataclass
    class Ticket:
        challenge_id: str
        team_id: str

    def __init__(self, challenge_id):
        self.__challenge_id = challenge_id

    def get_team(self):
        ticket = self.__check_ticket(input("ticket? "))
        if not ticket:
            print("invalid ticket!")
            return None

        if ticket.challenge_id != self.__challenge_id:
            print("invalid ticket!")
            return None

        return ticket.team_id

    def __check_ticket(self, ticket: str) -> Ticket:
        std_base64chars = "0123456789"
        custom = "0629851743"

        key=os.getenv("SECRET", "secret")
        decrypted = decrypt(ticket, key).decode()

        x = decrypted.translate(str(ticket).maketrans(custom, std_base64chars))
        decoded = base64.b64decode(x).decode().split(',')
        chall = decoded[0]
        id = decoded[1]

        ticket_info = requests.get(
            "https://ctf.openzeppelin.com/api/v1/challenges/check-ticket/" + id,
        ).json()
        if not ticket_info["data"] or not ticket_info["success"]:
            return None

        return TicketTeamProvider.Ticket(
            challenge_id=chall,
            team_id=id,
        )


class StaticTeamProvider(TeamProvider):
    def __init__(self, team_id, ticket):
        self.__team_id = team_id
        self.__ticket = ticket

    def get_team(self) -> str | None:
        ticket = input("ticket? ")

        if ticket != self.__ticket:
            print("invalid ticket!")
            return None

        return self.__team_id


class LocalTeamProvider(TeamProvider):
    def __init__(self, team_id):
        self.__team_id = team_id

    def get_team(self):
        return self.__team_id


def get_team_provider() -> TeamProvider:
    env = os.getenv("ENV", "local")
    if env == "local":
        return LocalTeamProvider(team_id="local")
    elif env == "dev":
        return StaticTeamProvider(team_id="dev", ticket="dev2023")
    else:
        return TicketTeamProvider(challenge_id=os.getenv("CHALLENGE_ID", "challenge"))
