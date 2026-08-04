# Take-Home Assessment Backend

This project implements a FastAPI backend for uploading MP4 videos, storing metadata in memory, and performing visual matching based on sampled frame fingerprints.

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running locally

Start the development server with:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

- http://127.0.0.1:8000/docs for Swagger UI
- http://127.0.0.1:8000/redoc for ReDoc

## Testing with Swagger

1. Open the Swagger UI at http://127.0.0.1:8000/docs.
2. Use the /upload endpoint to upload MP4 files.
3. Use /videos to list uploaded videos.
4. Use /match?video_id=<id> to retrieve ranked visual matches.

## Deployment on Render

This project is prepared for deployment as a Render Free Web Service.

Use the provided render.yaml file with:

- Python runtime
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## API endpoints

- POST /upload
  - Accepts multipart form field `files`
  - Uploads MP4 files and returns metadata including aspect ratio and bucket
- GET /videos
  - Lists all uploaded videos
  - Supports optional `ratio` filter for canonical buckets
- DELETE /videos/{video_id}
  - Deletes the uploaded file, fingerprint, and in-memory metadata
- GET /match?video_id=<id>
  - Returns ranked visual matches for the provided video ID

## Assumptions

- Videos are stored only in memory for metadata and fingerprints.
- Uploaded files are kept under the uploads directory.
- Matching is based on visual frame fingerprints and does not rely on filenames, metadata, or duration.

## Limitations

- The implementation is intentionally simple and uses in-memory storage only.
- Matching quality depends on the video content and frame sampling strategy.
- Only MP4 uploads are processed by the upload endpoint.
- Videos in the `Other` ratio bucket are ignored during matching.
