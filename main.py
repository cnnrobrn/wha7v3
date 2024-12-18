from fastapi import FastAPI, Request, Response
from typing import Optional
import httpx
import base64
import json
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(override=True)

app = FastAPI()

class Config:
    def __init__(self):
        self.VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")
        self.ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.validate_config()
    
    def validate_config(self):
        if not self.VERIFY_TOKEN:
            raise ValueError("INSTAGRAM_VERIFY_TOKEN must be set in .env file")
        if not self.ACCESS_TOKEN:
            raise ValueError("INSTAGRAM_ACCESS_TOKEN must be set in .env file")

config = Config()

async def download_media(media_url: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {config.ACCESS_TOKEN}"}
        response = await client.get(media_url, headers=headers)
        
        if response.status_code == 200:
            media_content = response.content
            base64_content = base64.b64encode(media_content).decode('utf-8')
            return base64_content
        return None

async def process_webhook_data(body: dict):
    """Process webhook data regardless of endpoint"""
    print(f"Processing webhook data: {json.dumps(body, indent=2)}")
    
    for entry in body.get('entry', []):
        for messaging in entry.get('messaging', []):
            sender_id = messaging.get('sender', {}).get('id')
            recipient_id = messaging.get('recipient', {}).get('id')
            timestamp = messaging.get('timestamp')
            
            message = messaging.get('message', {})
            message_text = message.get('text', '')
            
            attachments = message.get('attachments', [])
            for attachment in attachments:
                content_type = attachment.get('type')
                media_url = attachment.get('payload', {}).get('url')
                
                print(f"Content Type: {content_type}")
                print(f"Message Text: {message_text}")
                
                if media_url:
                    base64_content = await download_media(media_url)
                    if base64_content:
                        print(f"Media downloaded and converted to base64")

@app.get("/")
async def verify_webhook(request: Request):
    """Handle GET requests for webhook verification"""
    params = dict(request.query_params)
    
    print("Received verification request with params:", params)
    print("Expected verify token:", config.VERIFY_TOKEN)
    
    hub_mode = params.get('hub.mode')
    hub_verify_token = params.get('hub.verify_token')
    hub_challenge = params.get('hub.challenge')
    
    print(f"hub.mode: {hub_mode}")
    print(f"hub.verify_token: {hub_verify_token}")
    print(f"hub.challenge: {hub_challenge}")

    if hub_mode == "subscribe" and hub_verify_token == config.VERIFY_TOKEN:
        print("Verification successful!")
        if hub_challenge:
            return int(hub_challenge)
        return Response(status_code=200)
    
    print("Verification failed!")
    return Response(status_code=403)

@app.post("/")
@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle POST requests at both root and /webhook endpoints"""
    try:
        body = await request.json()
        await process_webhook_data(body)
        return Response(status_code=200)
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server with verify token: {config.VERIFY_TOKEN}")
    uvicorn.run(app, host="0.0.0.0", port=8000)