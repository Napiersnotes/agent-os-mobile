"""
Minimal FastAPI app for testing
"""
from fastapi import FastAPI

app = FastAPI(title="Agent OS Mobile", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Agent OS Mobile API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-os-mobile"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
