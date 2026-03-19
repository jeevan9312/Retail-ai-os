from fastapi import FastAPI, UploadFile, HTTPException
import pandas as pd
import io
from validator import validate_transactions
from s3_uploader import upload_to_s3
from kafka_producer import publish_to_kafka

app = FastAPI(title="Retail AI OS — Ingestion Service")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "ingestion"}

@app.post("/ingest/transactions")
async def ingest_transactions(file: UploadFile):
    """Accept CSV upload, validate, push to S3 + Kafka"""
    
    # Read uploaded file
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    
    # Validate
    validation = validate_transactions(df)
    if not validation['passed']:
        raise HTTPException(
            status_code=400,
            detail={"message": "Data quality failed", "issues": validation['issues']}
        )
    
    # Save locally then upload to S3
    local_path = f"/tmp/{file.filename}"
    df.to_csv(local_path, index=False)
    s3_path = upload_to_s3(local_path, "transactions")
    
    # Publish sample events to Kafka (first 100 rows)
    for _, row in df.head(100).iterrows():
        publish_to_kafka("retail.pos.transactions", row.to_dict())
    
    return {
        "status":    "success",
        "rows":      len(df),
        "s3_path":   s3_path,
        "kafka":     "published"
    }

@app.get("/status")
def status():
    return {"pipeline": "active", "topics": ["retail.pos.transactions"]}