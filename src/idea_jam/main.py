from fastapi import FastAPI

app = FastAPI(title="Idea Jam")


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}
