from fastapi import FastAPI, Request, Response
from typing import Optional
import httpx
import base64
import json
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

class WebhookVerification(BaseModel):
    hub_mode: str
    hub_challenge: str
    hub_verify_token: str

class Config:
    """Configuration class to manage environment variables"""
    def __init__(self):
        self.VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")
        self.ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.API_VERSION = os.getenv("INSTAGRAM_API_VERSION", "v18.0")  # Default to v18.0
        self.BASE_URL = os.getenv("INSTAGRAM_API_BASE_URL", "https://graph.instagram.com")
        self.PORT = int(os.getenv("PORT", "8000"))
        self.HOST = os.getenv("HOST", "0.0.0.0")
        
        # Validate required environment variables
        self.validate_config()
    
    def validate_config(self):
        """Validate that all required environment variables are set"""
        if not self.VERIFY_TOKEN:
            raise ValueError("INSTAGRAM_VERIFY_TOKEN must be set in .env file")
        if not self.ACCESS_TOKEN:
            raise ValueError("INSTAGRAM_ACCESS_TOKEN must be set in .env file")

# Initialize config
config = Config()

async def download_media(media_url: str) -> Optional[str]:
    """
    Download media from Instagram and convert to base64
    """
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {config.ACCESS_TOKEN}"}
        response = await client.get(media_url, headers=headers)
        
        if response.status_code == 200:
            media_content = response.content
            base64_content = base64.b64encode(media_content).decode('utf-8')
            return base64_content
        return None

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verify the webhook subscription
    """
    params = dict(request.query_params)
    
    if params.get('hub.mode') == 'subscribe' and params.get('hub.verify_token') == config.VERIFY_TOKEN:
        return Response(content=params.get('hub.challenge'), media_type="text/plain")
    return Response(status_code=400)

@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming webhook events from Instagram
    """
    try:
        body = await request.json()
        
        # Entry contains array of messaging events
        for entry in body.get('entry', []):
            for messaging in entry.get('messaging', []):
                sender_id = messaging.get('sender', {}).get('id')
                recipient_id = messaging.get('recipient', {}).get('id')
                timestamp = messaging.get('timestamp')
                
                message = messaging.get('message', {})
                message_text = message.get('text', '')
                
                # Handle attachments (media)
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
                            # You might want to save this to a file or database
                            
        return Response(status_code=200)
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)