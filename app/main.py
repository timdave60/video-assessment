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
async def root(request: Request):
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return HTMLResponse(
            content="""
            <!doctype html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <title>Video Matching Demo</title>
                <style>
                    body { margin: 0; font-family: Inter, Arial, sans-serif; background: #f5f7fb; color: #1f2937; }
                    .shell { max-width: 920px; margin: 0 auto; padding: 40px 20px 56px; }
                    .hero { background: linear-gradient(135deg, #0f172a 0%, #2563eb 100%); color: white; border-radius: 24px; padding: 32px; box-shadow: 0 16px 32px rgba(15, 23, 42, 0.16); }
                    .hero h1 { margin: 0 0 8px; font-size: 2rem; }
                    .hero p { margin: 0; opacity: 0.9; }
                    .cta-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px; }
                    .btn { display: inline-block; padding: 10px 16px; border-radius: 999px; text-decoration: none; font-weight: 600; }
                    .btn-primary { background: white; color: #2563eb; }
                    .btn-secondary { border: 1px solid rgba(255,255,255,0.35); color: white; }
                    .panel { margin-top: 20px; background: white; border: 1px solid #e2e8f0; border-radius: 20px; padding: 24px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06); }
                    .muted { color: #6b7280; }
                </style>
            </head>
            <body>
                <div class="shell">
                    <section class="hero">
                        <h1>Video Matching Demo</h1>
                        <p>Upload videos, browse your library, and inspect same-content matches in a polished browser flow.</p>
                        <div class="cta-row">
                            <a class="btn btn-primary" href="/upload-page">Open the demo</a>
                        </div>
                    </section>
                    <section class="panel">
                        <h2>What this demo does</h2>
                        <p class="muted">It supports video upload, ratio-based library filtering, delete actions, and cross-bucket matching based on visual similarity.</p>
                    </section>
                </div>
            </body>
            </html>
            """,
            status_code=200,
        )
    return JSONResponse(content={"status": "ok"})


@app.get("/upload-page", response_class=HTMLResponse)
async def upload_page() -> HTMLResponse:
    return HTMLResponse(
        content="""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>Video Upload Demo</title>
            <style>
                body { margin: 0; font-family: Inter, Arial, sans-serif; background: #f5f7fb; color: #1f2937; }
                .shell { max-width: 1080px; margin: 0 auto; padding: 32px 20px 48px; }
                .hero { background: linear-gradient(135deg, #0f172a 0%, #2563eb 100%); color: white; border-radius: 24px; padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 16px 32px rgba(15, 23, 42, 0.16); }
                .hero h1 { margin: 0 0 8px; font-size: 1.9rem; }
                .hero p { margin: 0; opacity: 0.92; }
                .panel { background: white; border: 1px solid #e2e8f0; border-radius: 20px; padding: 22px; margin-bottom: 20px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05); }
                .upload-form { display: grid; gap: 12px; }
                .field-label { font-weight: 600; }
                input, select, button { padding: 10px 12px; font-size: 15px; border-radius: 10px; border: 1px solid #d1d5db; }
                button { background: #2563eb; color: white; border: none; cursor: pointer; font-weight: 600; }
                button:hover { opacity: 0.95; }
                button:disabled { opacity: 0.7; cursor: wait; }
                .panel-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
                .panel-header h2 { margin: 0; }
                .filter-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
                .grid { display: grid; grid-template-columns: 1fr; gap: 14px; }
                .card { border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; background: #fafafa; }
                .card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
                .pill { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; background: #dbeafe; color: #1d4ed8; font-size: 12px; font-weight: 700; }
                .meta { margin-top: 6px; color: #64748b; font-size: 14px; }
                .action-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
                .secondary { background: #f3f4f6; color: #111827; border: 1px solid #d1d5db; }
                .muted { color: #6b7280; }
                .empty-state { padding: 16px; border: 1px dashed #cbd5e1; border-radius: 12px; background: #f8fafc; color: #475569; text-align: center; }
                .status { min-height: 24px; margin-top: 8px; color: #475569; }
                .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #ddd; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 6px; }
                @keyframes spin { to { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <div class="shell">
                <section class="hero">
                    <h1>Video Matching Demo</h1>
                    <p>Upload videos, review the library, and inspect same-content matches with a cleaner experience.</p>
                </section>

                <section class="panel">
                    <form id="upload-form" class="upload-form">
                        <label class="field-label" for="file-input">Choose one or more videos</label>
                        <input id="file-input" type="file" name="files" multiple required>
                        <button type="submit">Upload Video</button>
                    </form>
                    <div id="status" class="status"></div>
                </section>

                <section class="panel">
                    <div class="panel-header">
                        <div>
                            <h2>Video Library</h2>
                            <p class="muted">Browse videos by ratio bucket and inspect their matches.</p>
                        </div>
                        <div class="filter-row">
                            <label for="ratio-filter" class="muted">Filter by ratio bucket:</label>
                            <select id="ratio-filter">
                                <option value="">All</option>
                                <option value="9:16">9:16</option>
                                <option value="1:1">1:1</option>
                                <option value="4:5">4:5</option>
                                <option value="16:9">16:9</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                    </div>
                    <div id="results"></div>
                </section>
            </div>
            <script>
                const form = document.getElementById('upload-form');
                const fileInput = document.getElementById('file-input');
                const status = document.getElementById('status');
                const results = document.getElementById('results');
                const ratioFilter = document.getElementById('ratio-filter');

                async function loadVideos() {
                    const ratio = ratioFilter.value;
                    const url = ratio ? `/videos?ratio=${encodeURIComponent(ratio)}` : '/videos';
                    results.innerHTML = '<div class="empty-state"><span class="spinner"></span>Loading videos…</div>';
                    try {
                        const response = await fetch(url);
                        const payload = await response.json();
                        if (!response.ok) {
                            throw new Error(payload.detail || 'Unable to load videos.');
                        }
                        renderUploadedVideos(payload);
                    } catch (error) {
                        results.innerHTML = `<div class="empty-state">${error.message || 'Unable to load videos.'}</div>`;
                    }
                }

                ratioFilter.addEventListener('change', () => loadVideos());

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
                        form.reset();
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
                    button.innerHTML = '<span class="spinner"></span>Finding matches...';
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
                            matchContainer.innerHTML = '<div class="muted">No matching videos found.</div>';
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
                        matchContainer.innerHTML = `<div class="muted">${message}</div>`;
                    } finally {
                        window.clearTimeout(timeoutId);
                        button.disabled = false;
                        button.innerHTML = 'Find Matches';
                    }
                }

                function renderUploadedVideos(videos) {
                    if (!Array.isArray(videos) || !videos.length) {
                        results.innerHTML = '<div class="empty-state">No videos uploaded yet. Add your first video to begin.</div>';
                        return;
                    }

                    const wrapper = document.createElement('div');
                    wrapper.className = 'grid';
                    videos.forEach((video) => {
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.innerHTML = `
                            <div class="card-head">
                                <strong>${video.filename}</strong>
                                <span class="pill">${video.ratio_bucket || 'Unknown'}</span>
                            </div>
                            <div class="meta">Video ID: ${video.video_id}</div>
                            <div class="meta">Dimensions: ${video.width} × ${video.height}</div>
                            <div class="meta">Aspect ratio: ${video.aspect_ratio}</div>
                            <div class="action-row">
                                <button type="button" class="find-matches">Find Matches</button>
                                <button type="button" class="delete-video secondary">Delete</button>
                            </div>
                            <div class="match-results"></div>
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
