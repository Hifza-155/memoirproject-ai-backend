from fastapi import FastAPI

app = FastAPI(title="Memoir App API") 

@app.get("/")
def read_root():
    return {"message": "API is successfully running!"}