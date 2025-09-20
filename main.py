from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, world!"}


@app.post("/")
async def receive_github_info(request: Request):
    payload = await request.json()  # read JSON body
    print(payload)  # optional, prints to console/logs
    return {"received": payload}  # returns it back in the response


@app.get("/ping")
def ping():
    return {"status": "pong"}
