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
            <title>Video Upload Demo</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
                form { display: grid; gap: 12px; margin-bottom: 24px; }
                input, button { padding: 10px; font-size: 16px; }
                .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
                .grid { display: grid; gap: 12px; }
                .muted { color: #666; }
                .matches { margin-top: 12px; padding-left: 16px; }
                .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #ddd; border-top-color: #333; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 6px; }
                @keyframes spin { to { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <h1>Video Upload Demo</h1>
            <p class=\"muted\">Upload videos and inspect same-content matches.</p>
            <p class=\"muted\">The browser upload uses multipart/form-data and sends files to the existing /upload endpoint.</p>
            <form id=\"upload-form\">
                <input id=\"file-input\" type=\"file\" name=\"files\" multiple required>
                <button type=\"submit\">Upload Videos</button>
            </form>
            <div id=\"status\" class=\"muted\"></div>
            <h2>Uploaded Videos</h2>
            <div id=\"results\"></div>
            <script>
                const form = document.getElementById('upload-form');
                const fileInput = document.getElementById('file-input');
                const status = document.getElementById('status');
                const results = document.getElementById('results');

                async function loadVideos() {
                    try {
                        const response = await fetch('/videos');
                        const payload = await response.json();
                        if (!response.ok) {
                            throw new Error(payload.detail || 'Unable to load videos.');
                        }
                        renderUploadedVideos(payload);
                    } catch (error) {
                        results.innerHTML = `<div class="muted">${error.message || 'Unable to load videos.'}</div>`;
                    }
                }

                form.addEventListener('submit', async (event) => {
                    event.preventDefault();
                    const files = Array.from(fileInput.files || []);
                    if (!files.length) {
                        status.textContent = 'Please choose at least one video.';
                        return;
                    }

                    status.textContent = 'Uploading...';
                    const formData = new FormData();
                    files.forEach((file) => formData.append('files', file));

                    try {
                        const response = await fetch('/upload', { method: 'POST', body: formData });
                        const payload = await response.json();
                        if (!response.ok) {
                            throw new Error(payload.detail || 'Upload failed.');
                        }

                        await loadVideos();
                        status.textContent = `Uploaded ${payload.length} video${payload.length === 1 ? '' : 's'} successfully.`;
                    } catch (error) {
                        status.textContent = error.message || 'Upload failed.';
                    }
                });

                async function deleteVideo(videoId, button) {
                    const card = button.closest('.card');
                    if (!card) {
                        return;
                    }

                    button.disabled = true;
                    button.textContent = 'Deleting...';

                    try {
                        const response = await fetch(`/videos/${encodeURIComponent(videoId)}`, { method: 'DELETE' });
                        const payload = await response.json();
                        if (!response.ok) {
                            throw new Error(payload.detail || 'Delete failed.');
                        }
                        card.remove();
                        status.textContent = `Deleted video ${videoId}.`;
                    } catch (error) {
                        status.textContent = error.message || 'Delete failed.';
                        button.disabled = false;
                        button.textContent = 'Delete';
                    }
                }

                async function findMatches(videoId, button) {
                    const card = button.closest('.card');
                    const matchContainer = card ? card.querySelector('.match-results') : null;
                    if (!matchContainer) {
                        return;
                    }

                    button.disabled = true;
                    button.innerHTML = '<span class=\"spinner\"></span>Finding matches...';
                    matchContainer.innerHTML = '';

                    const controller = new AbortController();
                    const timeoutId = window.setTimeout(() => controller.abort(), 20000);

                    try {
                        const response = await fetch(`/match?video_id=${encodeURIComponent(videoId)}`, { signal: controller.signal });
                        let payload = null;
                        try {
                            payload = await response.json();
                        } catch (parseError) {
                            payload = null;
                        }

                        if (!response.ok) {
                            const detail = payload && payload.detail ? payload.detail : 'Unable to load matches.';
                            throw new Error(detail);
                        }

                        if (!payload || !payload.length) {
                            matchContainer.innerHTML = '<div class=\"muted\">No matching videos found.</div>';
                        } else {
                            const list = document.createElement('ul');
                            payload.forEach((item) => {
                                const entry = document.createElement('li');
                                entry.innerHTML = `<strong>${item.filename}</strong> — ${item.video_id}<br/>Confidence: ${Number(item.confidence).toFixed(2)}`;
                                list.appendChild(entry);
                            });
                            matchContainer.appendChild(list);
                        }
                    } catch (error) {
                        const message = error.name === 'AbortError' ? 'The request timed out. Please try again.' : (error.message || 'Unable to load matches.');
                        matchContainer.innerHTML = `<div class=\"muted\">${message}</div>`;
                    } finally {
                        window.clearTimeout(timeoutId);
                        button.disabled = false;
                        button.innerHTML = 'Find Matches';
                    }
                }

                function renderUploadedVideos(videos) {
                    if (!Array.isArray(videos) || !videos.length) {
                        results.innerHTML = '<div class="muted">No videos uploaded yet.</div>';
                        return;
                    }

                    const wrapper = document.createElement('div');
                    wrapper.className = 'grid';
                    videos.forEach((video) => {
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.innerHTML = `
                            <div><strong>${video.filename}</strong></div>
                            <div class=\"muted\">Video ID: ${video.video_id}</div>
                            <div class=\"muted\">Width: ${video.width} · Height: ${video.height}</div>
                            <div class=\"muted\">Aspect Ratio: ${video.aspect_ratio} · Bucket: ${video.ratio_bucket}</div>
                            <div style=\"margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;\">
                                <button type=\"button\" class=\"find-matches\">Find Matches</button>
                                <button type=\"button\" class=\"delete-video\">Delete</button>
                            </div>
                            <div class=\"match-results\"></div>
                        `;
                        const button = card.querySelector('.find-matches');
                        const deleteButton = card.querySelector('.delete-video');
                        button.addEventListener('click', () => findMatches(video.video_id, button));
                        deleteButton.addEventListener('click', () => deleteVideo(video.video_id, deleteButton));
                        wrapper.appendChild(card);
                    });
                    results.innerHTML = '';
                    results.appendChild(wrapper);
                }

                loadVideos();
            </script>
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
