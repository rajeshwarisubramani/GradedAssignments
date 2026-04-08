from dataclasses import asdict, dataclass


@dataclass
class TransactionEvent:
    tx_id: str
    event_type: str
    book_id: str
    member_id: str
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)

