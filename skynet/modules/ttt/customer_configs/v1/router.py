from fastapi import Depends, HTTPException
from fastapi_versionizer.versionizer import api_version

from skynet.auth.customer_id import CustomerId
from skynet.env import summary_minimum_payload_length
from skynet.logs import get_logger
from skynet.modules.ttt.customer_configs.utils import get_customerconfig_key, get_existing_customer_config
from skynet.modules.ttt.customer_configs.v1.models import CustomerConfig, CustomerConfigPayload, CustomerConfigResponse
from skynet.modules.ttt.persistence import db
from skynet.utils import get_router

router = get_router()
log = get_logger(__name__)


def validate_customer_config_payload(payload: CustomerConfigPayload) -> None:
    if not payload.live_summary_prompt.strip():
        raise HTTPException(status_code=422, detail="live_summary_prompt cannot be empty")

    if len(payload.live_summary_prompt.strip()) < summary_minimum_payload_length:
        raise HTTPException(
            status_code=422, detail=f"live_summary_prompt must be at least {summary_minimum_payload_length} characters"
        )


@api_version(1)
@router.get('/config')
async def get_customer_config(customer_id=Depends(CustomerId())) -> CustomerConfig:
    """
    Get the current customer config.
    """
    config = await get_existing_customer_config(customer_id)

    if config:
        return CustomerConfig(live_summary_prompt=config.get('live_summary_prompt'))

    raise HTTPException(status_code=404, detail='Customer configuration not found')


@api_version(1)
@router.post('/config', dependencies=[Depends(validate_customer_config_payload)])
async def set_customer_config(
    payload: CustomerConfigPayload, customer_id=Depends(CustomerId())
) -> CustomerConfigResponse:
    """
    Set the customer config.
    """
    # Store in database
    key = get_customerconfig_key(customer_id)
    config = {'live_summary_prompt': payload.live_summary_prompt}

    import json

    await db.set(key, json.dumps(config))

    log.info(f"Updated customer config for customer {customer_id}")

    return CustomerConfigResponse()


@api_version(1)
@router.delete('/config')
async def delete_customer_config(customer_id=Depends(CustomerId())) -> CustomerConfigResponse:
    """
    Delete the customer config.
    """
    config = await get_existing_customer_config(customer_id)

    if not config:
        raise HTTPException(status_code=404, detail='Customer configuration not found')

    key = get_customerconfig_key(customer_id)
    await db.delete(key)

    log.info(f"Deleted customer config for customer {customer_id}")

    return CustomerConfigResponse()
