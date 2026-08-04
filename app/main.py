from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import settings
from app.routes import router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI backend for video upload and matching.",
)


@app.get("/")
async def root() -> dict:
    return {"status": "ok"}


@app.get("/upload-page", response_class=HTMLResponse)
async def upload_page() -> HTMLResponse:
    return HTMLResponse(
        content="""
        <!doctype html>
        <html lang=\"en\">
        <head>
            <meta charset=\"utf-8\">
            <title>Video Upload</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 640px; margin: 40px auto; }
                form { display: grid; gap: 12px; }
                input, button { padding: 10px; font-size: 16px; }
            </style>
        </head>
        <body>
            <h1>Upload videos</h1>
            <form action=\"/upload\" method=\"post\" enctype=\"multipart/form-data\">
                <input type=\"file\" name=\"files\" multiple required>
                <button type=\"submit\">Upload</button>
            </form>
        </body>
        </html>
        """,
        status_code=200,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(router)
