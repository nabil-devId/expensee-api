from enum import Enum as PyEnum

class ReceiptStatus(str, PyEnum):
    """Enum for receipt status.

    Values:
        PENDING: Receipt has been uploaded but not yet processed.
        PROCESSED: Receipt has been processed by the system.
        ACCEPTED: Receipt has been reviewed and accepted.
        REJECTED: Receipt has been reviewed and rejected.
    """
    PENDING = "pending"
    PROCESSED = "processed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

