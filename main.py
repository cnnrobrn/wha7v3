from fastapi import FastAPI, Request, Response
from typing import Optional
import httpx
import base64
import json
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path
from openai import OpenAI
from OpenAI import analyze_image, ImageAnalysisRequest, Outfits
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

app = FastAPI()

class Config:
    def __init__(self):
        self.VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")
        self.ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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
        global client
        client = OpenAI(api_key=self.OPENAI_API_KEY)
        logger.info("OpenAI client initialized")

config = Config()

async def download_media(media_url: str) -> Optional[str]:
    """Download media and convert to base64"""
    try:
        async with httpx.AsyncClient() as client:
            # Use Instagram access token for authentication
            headers = {"Authorization": f"Bearer {config.ACCESS_TOKEN}"}
            logger.info(f"Attempting to download media from: {media_url}")
            
            response = await client.get(media_url, headers=headers, follow_redirects=True)
            
            if response.status_code == 200:
                # Get content type and appropriate prefix
                content_type = response.headers.get('content-type', 'application/octet-stream')
                logger.info(f"Media downloaded successfully. Content type: {content_type}")
                
                # Convert to base64
                media_content = response.content
                base64_content = base64.b64encode(media_content).decode('utf-8')
                return f"data:{content_type};base64,{base64_content}"
            else:
                logger.error(f"Failed to download media. Status code: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error downloading media: {str(e)}")
        return None

async def process_image_with_openai(base64_image: str, message_text: str) -> Optional[Outfits]:
    """Process image using OpenAI analysis"""
    try:
        logger.info("Starting OpenAI image analysis")
        request = ImageAnalysisRequest(
            base64_image=base64_image,
            text=message_text or "Analyze this outfit"
        )
        
        logger.info("Calling OpenAI analyze_image function")
        result = await analyze_image(request)
        logger.info(f"OpenAI analysis completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in OpenAI processing: {str(e)}")
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
        logger.info(f"Received webhook: {json.dumps(body, indent=2)}")
        
        for entry in body.get('entry', []):
            for messaging in entry.get('messaging', []):
                message = messaging.get('message', {})
                message_text = message.get('text', '')
                
                attachments = message.get('attachments', [])
                for attachment in attachments:
                    content_type = attachment.get('type')
                    payload = attachment.get('payload', {})
                    media_url = payload.get('url')
                    
                    logger.info(f"Processing attachment - Type: {content_type}, URL: {media_url}")
                    
                    if media_url and content_type == 'share':  # Instagram sends images as 'share' type
                        base64_content = await download_media(media_url)
                        if base64_content:
                            logger.info("Media converted to base64 successfully")
                            
                            # Process image with OpenAI
                            analysis_result = await process_image_with_openai(
                                base64_content,
                                message_text
                            )
                            
                            if analysis_result:
                                logger.info("Analysis completed successfully")
                                response_text = f"Analysis Results:\n"
                                response_text += f"Response: {analysis_result.Response}\n\n"
                                response_text += "Articles of Clothing:\n"
                                for article in analysis_result.Article:
                                    response_text += f"- {article.Item}: {article.Search}\n"
                                
                                logger.info(f"Sending response: {response_text}")
                                # Here you would add code to send response_text back to Instagram
                            else:
                                logger.error("OpenAI analysis failed or returned no results")
                        else:
                            logger.error("Failed to download and convert media")
        
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server with verify token: {config.VERIFY_TOKEN}")
    uvicorn.run(app, host="0.0.0.0", port=8000)