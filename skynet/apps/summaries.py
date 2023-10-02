from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_versionizer.versionizer import versionize

from skynet.routers.v1 import router as v1_router

app = FastAPI()
app.include_router(v1_router)

versionize(
    app=app,
    prefix_format='/v{major}',
    docs_url='/docs',
    enable_latest=False,
    sorted_routes=True
)

@app.get("/")
def root():
    return RedirectResponse(url='v1/docs')

__all__ = [ 'app' ]
