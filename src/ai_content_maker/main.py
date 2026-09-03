from fastapi import FastAPI

app = FastAPI(title="AI Content Maker")

@app.get("/health")
def health():
    return {"status": "ok"}