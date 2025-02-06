from fastapi import HTTPException, Request

from skynet.utils import get_customer_id


class CustomerId:
    async def __call__(self, request: Request):
        customer_id = get_customer_id(request)

        if customer_id is None:
            raise HTTPException(
                status_code=422,
                detail='Customer ID is required to be encoded in the JWT token or specified as a query parameter.',
            )

        return customer_id
