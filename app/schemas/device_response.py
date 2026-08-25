from pydantic import BaseModel


class DeviceTokenResponse(
    BaseModel
):
    token: str
