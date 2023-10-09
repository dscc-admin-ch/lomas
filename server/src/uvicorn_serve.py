import os
import uvicorn

if __name__ == "__main__":
    os.chdir("/code/")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=80,
        log_level="info",
        workers=5,
        reload=True,
    )
