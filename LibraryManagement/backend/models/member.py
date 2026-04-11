from dataclasses import asdict, dataclass


@dataclass
class Member:
    member_id: str
    name: str
    email: str
    phone: str
    membership_date: str
    status: str = "active"
    address: dict | None = None

    def __post_init__(self) -> None:
        self.status = (self.status or "active").lower()
        self.address = self.address or {}

    def to_dict(self) -> dict:
        return asdict(self)

