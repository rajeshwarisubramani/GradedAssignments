from dataclasses import asdict, dataclass


@dataclass
class Member:
    member_id: str
    name: str
    age: int
    contact_info: str

    def to_dict(self) -> dict:
        return asdict(self)

