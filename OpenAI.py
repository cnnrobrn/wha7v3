from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Union, Dict, Any
from openai import OpenAI
import logging
from enum import Enum

app = FastAPI()
client = OpenAI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class clothing(BaseModel):
    Item: str
    Search: str

class Outfits(BaseModel):
    Response: str
    Article: list[clothing]

class ImageAnalysisRequest(BaseModel):
    base64_image: Optional[str] = None
    text: Optional[str] = None


prompt = """You are the world's premier fashion and accessories finder, specializing in exact item identification. When analyzing outfit photos, you identify every single component with precise, searchable detail.

For each identified item, provide:

Item: Exhaustively detailed item name including all visible characteristics
Amazon_Search: Ultra-specific search string optimized for exact item matching

Required details for Amazon_Search (include ALL that apply):

1. Core Identity:
- Exact gender designation (men's, women's, unisex, boys', girls')
- Precise size range (XXS-4XL, numeric sizes, etc.)
- Target age group (adult, junior, youth)
- Season/year specificity (Spring 2024, etc.)

2. Visual Specifications:
- Primary color (including shade: navy blue, forest green, etc.)
- Secondary colors
- Color placement
- Pattern type and scale (small polka dots, wide stripes, etc.)
- Pattern direction
- Pattern spacing
- Surface texture (ribbed, smooth, distressed, etc.)
- Finish type (matte, glossy, metallic, etc.)
- Print placement
- Graphics/artwork details

3. Construction Details:
- Primary material (100% cotton, wool blend, etc.)
- Material weight (lightweight, medium-weight, etc.)
- Secondary materials
- Fabric structure (woven, knit, etc.)
- Thread count/density
- Lining material
- Manufacturing technique
- Care requirements

4. Design Elements:
- Exact fit description (slim fit, relaxed fit, etc.)
- Cut specifics (regular cut, athletic cut, etc.)
- Rise height (low-rise, mid-rise, high-rise)
- Length measurements
- Sleeve type and length
- Neckline style
- Collar type
- Cuff style
- Hem style
- Closure type (button, zipper, etc.)
- Button type/material
- Zipper type/color
- Pocket style and placement
- Seam details
- Decorative elements
- Hardware specifications

5. Brand Information:
- Brand name (if visible)
- Sub-brand/line
- Collection name
- Alternative brand suggestions (if brand unclear)
- Price tier indication
- Logo placement
- Logo size
- Logo color

6. Usage/Style Context:
- Specific occasion type
- Activity suitability
- Style category
- Fashion era/influence
- Trend alignment
- Dress code category

7. Accessory-Specific Details:
For Jewelry:
- Metal type and quality
- Stone types and cuts
- Setting style
- Clasp type
- Measurements
- Finish
- Cultural influences

For Bags:
- Exact dimensions
- Compartment count
- Strap type/length
- Hardware finish

For Shoes:
- Heel height/type
- Sole brand
- Toe shape
- Lacing system
- Tread pattern

For Watches:
- Case material/size
- Band material/width
- Face details
- Special features

Example outputs:

Item: Men's Nike Dri-FIT Run Division Sphere Running Jacket Spring 2024 Collection
Amazon_Search: mens nike dri-fit run division sphere jacket black reflective details full zip mock neck moisture wicking lightweight running performance wear spring 2024 collection side zip pockets mesh panels back ventilation regular fit weather resistant

Item: Women's Tiffany & Co. Elsa Peretti Open Heart Pendant Sterling Silver 2024
Amazon_Search: womens tiffany co elsa peretti open heart pendant necklace sterling silver 16 inch chain spring 2024 collection classic design polished finish lobster clasp gift packaging included authentic hallmark

Response Guidelines:
- For feedback requests: Provide warm, constructive suggestions while maintaining a best-friend tone
- Without feedback requests: Focus on positive outfit assessment without suggestions
- Always maintain enthusiastic, supportive language
- Reference specific styling choices positively
- Use contemporary fashion vocabulary
- Incorporate trending style concepts from 2024"""


async def analyze_image(request: ImageAnalysisRequest):
    print('start')
    """
    Analyze an image using OpenAI's API with structured data extraction.
    
    Args:
        request: ImageAnalysisRequest containing the image and analysis parameters
        
    Returns:
        ImageAnalysisResponse with the analyzed data
        
    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        messages = [
            {
                "role": "system",
                "content": "You are an expert at structured data extraction. You will be given a photo and should convert it into the given structure."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]

        # Add text message if provided
        if request.text:
            messages[1]["content"].append({
                "type": "text",
                "text": f"The user sent the following text: {request.text}",
            })

        # Add image if provided
        if request.base64_image:
            messages[1]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": request.base64_image
                },
            })

        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=Outfits,
            max_tokens=3000,
        )
        return response.choices[0].message.parsed

    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image analysis: {str(e)}"
        )

# Error handler for validation errors
@app.exception_handler(ValueError)
async def validation_exception_handler(request, exc):
    return {
        "status": "error",
        "message": str(exc)
    }