from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi_versionizer.versionizer import versionize

from skynet.routers.v1 import router as v1_router


app = FastAPI()
app.include_router(v1_router)

versions = versionize(
    app=app,
    prefix_format='/v{major}',
    docs_url='/docs',
    enable_latest=True,
    sorted_routes=True
)

# Add additional routes after versioning so they are not versioned.
#

@app.get("/")
def root():
    return RedirectResponse(url='/latest/docs')

@app.get("/healthz")
def health():
    """
    Health checking for k8s.
    """

    return {"status": "ok"}
