from fastapi import FastAPI, Request
from update_project import pipeline, Config 
from dotenv import load_dotenv

load_dotenv()

config = Config()

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, world!"}


@app.post("/")
async def receive_github_info(request: Request):
    payload = await request.json() 
    print(payload)  

    pipeline(config)

    return {"success" : True} 

@app.get("/ping")
def ping():
    return {"status": "pong"}
