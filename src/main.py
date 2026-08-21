from fastapi import FastAPI

app = FastAPI(title="Memoir App API") 

@app.get("/")
def read_root():
    return {"message": "API is successfully running!"}

# 3. Health Check Endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}