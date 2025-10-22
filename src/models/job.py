from enum import Enum

class JobStatus(str, Enum):
    """
    Job Status Enumeration
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
