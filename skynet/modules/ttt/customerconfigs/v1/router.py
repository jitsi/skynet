from fastapi import Depends, HTTPException
from fastapi_versionizer.versionizer import api_version

from skynet.auth.customer_id import CustomerId
from skynet.logs import get_logger
from skynet.utils import get_router
from skynet.modules.ttt.customerconfigs.v1.models import CustomerConfig, CustomerConfigPayload, CustomerConfigResponse
from skynet.modules.ttt.customerconfigs.utils import get_customerconfig_key, get_existing_customer_config
from skynet.modules.ttt.persistence import db

router = get_router()
log = get_logger(__name__)


def validate_customer_config_payload(payload: CustomerConfigPayload) -> None:
    if not payload.summary_prompt.strip():
        raise HTTPException(status_code=422, detail="summary_prompt cannot be empty")

    if len(payload.summary_prompt.strip()) < 100:
        raise HTTPException(status_code=422, detail="summary_prompt must be at least 100 characters")


@api_version(1)
@router.get('/config')
async def get_customer_config(customer_id=Depends(CustomerId())) -> CustomerConfig:
    """
    Get the current customer config.
    """
    config = await get_existing_customer_config(customer_id)

    if config:
        return CustomerConfig(
            summary_prompt=config.get('summary_prompt')
        )

    raise HTTPException(status_code=404, detail='Customer configuration not found')


@api_version(1)
@router.post('/config', dependencies=[Depends(validate_customer_config_payload)])
async def set_customer_config(payload: CustomerConfigPayload, customer_id=Depends(CustomerId())) -> CustomerConfigResponse:
    """
    Set the customer config.
    """
    # Store in database
    key = get_customerconfig_key(customer_id)
    config = {
        'summary_prompt': payload.summary_prompt
    }

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


