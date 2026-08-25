from datetime import datetime
from typing import List

from pydantic import BaseModel


class HistoryListItem(
    BaseModel
):
    id: int

    filename: str
    duration: float

    overall_score: int
    overall_level: str

    created_at: datetime


class HistoryListResponse(
    BaseModel
):
    items: List[
        HistoryListItem
    ]
