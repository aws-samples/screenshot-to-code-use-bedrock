import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=7001, reload=True)
