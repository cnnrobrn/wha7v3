from fastapi import FastAPI, Request, Response
from typing import Optional
import httpx
import base64
import json
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path
from openai import OpenAI  # Add OpenAI import
from OpenAI import analyze_image, ImageAnalysisRequest, Outfits  # Import from your OpenAI.py

# Load environment variables
load_dotenv(override=True)

app = FastAPI()
client = OpenAI()  # Initialize OpenAI client

class Config:
    def __init__(self):
        self.VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")
        self.ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Add OpenAI API key
        self.validate_config()
        self.initialize_openai()
    
    def validate_config(self):
        if not self.VERIFY_TOKEN:
            raise ValueError("INSTAGRAM_VERIFY_TOKEN must be set in .env file")
        if not self.ACCESS_TOKEN:
            raise ValueError("INSTAGRAM_ACCESS_TOKEN must be set in .env file")
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set in .env file")
    
    def initialize_openai(self):
        """Initialize OpenAI client with API key"""
        global client  # Make client available globally
        client = OpenAI(api_key=self.OPENAI_API_KEY)

config = Config()

def get_base64_prefix(content_type: str) -> str:
    """Get the appropriate base64 prefix based on content type"""
    if content_type.startswith('image/'):
        return f"data:{content_type};base64,"
    elif content_type.startswith('video/'):
        return f"data:{content_type};base64,"
    return "data:application/octet-stream;base64,"

async def download_media(media_url: str) -> Optional[str]:
    """Download media and convert to base64"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {config.ACCESS_TOKEN}"}
        response = await client.get(media_url, headers=headers)
        
        if response.status_code == 200:
            # Get content type and appropriate prefix
            content_type = response.headers.get('content-type', 'application/octet-stream')
            prefix = get_base64_prefix(content_type)
            
            # Convert to base64
            media_content = response.content
            base64_content = base64.b64encode(media_content).decode('utf-8')
            
            # Return complete string with prefix
            return f"{prefix}{base64_content}"
        return None

async def process_image_with_openai(base64_image: str, message_text: str) -> Optional[Outfits]:
    """Process image using OpenAI analysis"""
    try:
        # Create analysis request
        request = ImageAnalysisRequest(
            base64_image=base64_image,
            text=message_text
        )
        
        # Call OpenAI analysis function
        result = await analyze_image(request)
        print(f"OpenAI Analysis Result: {result}")
        return result
    
    except Exception as e:
        print(f"Error in OpenAI processing: {str(e)}")
        return None

@app.get("/")
async def verify_webhook(request: Request):
    """Handle GET requests for webhook verification"""
    params = dict(request.query_params)
    
    print("Received verification request with params:", params)
    
    hub_mode = params.get('hub.mode')
    hub_verify_token = params.get('hub.verify_token')
    hub_challenge = params.get('hub.challenge')

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
        print(f"Received webhook: {json.dumps(body, indent=2)}")
        
        for entry in body.get('entry', []):
            for messaging in entry.get('messaging', []):
                message = messaging.get('message', {})
                message_text = message.get('text', '')
                
                attachments = message.get('attachments', [])
                for attachment in attachments:
                    content_type = attachment.get('type')
                    media_url = attachment.get('payload', {}).get('url')
                    
                    print(f"Content Type: {content_type}")
                    print(f"Message Text: {message_text}")
                    
                    if media_url and content_type == 'image':  # Only process images
                        base64_content = await download_media(media_url)
                        if base64_content:
                            print("Media downloaded and converted to base64")
                            
                            # Process image with OpenAI
                            analysis_result = await process_image_with_openai(
                                base64_content,
                                message_text
                            )
                            
                            if analysis_result:
                                # Here you can handle the analysis result
                                # For example, send it back to the user via Instagram
                                print("Analysis completed:", analysis_result)
                                
                                # Format response message
                                response_text = f"Analysis Results:\n"
                                response_text += f"Response: {analysis_result.Response}\n\n"
                                response_text += "Articles of Clothing:\n"
                                for article in analysis_result.Article:
                                    response_text += f"- {article.Item}: {article.Search}\n"
                                
                                # Here you would add code to send response_text back to Instagram
                                # This depends on your Instagram messaging API implementation
                            
        return Response(status_code=200)
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server with verify token: {config.VERIFY_TOKEN}")
    uvicorn.run(app, host="0.0.0.0", port=8000)