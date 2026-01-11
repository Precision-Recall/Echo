"""
Google Slides AI Generator - Based on User Reference Images
Template Design: Title slide + Point/Summary alternating layouts
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from classroom_tools import get_slides_service, get_drive_service
import json
import os
import config
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel
import vertexai

router = APIRouter()

# Initialize Vertex AI
client_config = config.get_client_config()
if client_config["api_type"] == "paid":
    credentials_dict = json.loads(client_config["credentials_json"])
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=[
            "https://www.googleapis.com/auth/generative-language",
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    vertexai.init(
        project=client_config["project_id"],
        location=client_config["location"],
        credentials=credentials
    )
    print(f"✅ Slides endpoints using Vertex AI (Project: {client_config['project_id']})")
else:
    raise Exception("Slides endpoints require Vertex AI (paid tier) configuration.")

# Theme colors
THEME = {
    "colors": {
        "primary": "#60A5FA",      # Light Blue
        "background": "#1E293B",   # Dark Blue-Gray
        "text": "#E2E8F0",         # Light Gray
        "heading": "#FFFFFF",      # White
    },
    "fonts": {
        "heading": "Poppins",
        "body": "Source Sans Pro",
    },
}

EMU = 914400

def hex_to_rgb_dict(hex_color):
    hex_color = hex_color.lstrip('#')
    return {
        "red": int(hex_color[0:2], 16) / 255.0,
        "green": int(hex_color[2:4], 16) / 255.0,
        "blue": int(hex_color[4:6], 16) / 255.0
    }

def inches_to_emu(inches):
    return int(inches * EMU)

class GenerateOutlineRequest(BaseModel):
    topic: str
    num_slides: int

class SlideData(BaseModel):
    title: str
    content: str  # Can be bullets or summary text
    image_prompt: Optional[str] = None
    has_image: bool = False
    layout_type: str  # "points" or "summary"

class CreatePresentationRequest(BaseModel):
    title: str
    subtitle: str
    slides: List[SlideData]
    image_file_ids: List[str]
    title_image_id: Optional[str] = None

@router.post("/api/slides/generate-outline")
async def generate_outline_endpoint(
    request: GenerateOutlineRequest,
    authorization: str = Header(None),
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """Generate outline - Points or Summary layouts"""
    if not authorization or not x_user_email:
        raise HTTPException(status_code=401, detail="Missing authorization or user email")
    
    try:
        model = GenerativeModel('gemini-2.0-flash-exp')
        
        # Calculate content slides needed
        content_slides_needed = request.num_slides - 1
        
        prompt = f"""Generate a professional presentation outline: {request.topic}

CRITICAL REQUIREMENTS:
1. Generate EXACTLY {content_slides_needed} content slides (total with title = {request.num_slides})
2. Alternate between TWO layout types:
   - "points": 2-4 numbered bullet points (detailed, 10-15 words each)
   - "summary": 1-2 paragraph summary (40-60 words total) with image
3. Title slide: title (3-6 words) + subtitle format like "Date: Sunday, January 11, 2026"
4. Every slide with "summary" layout gets has_image: true
5. Points layout = no image, Summary layout = image

LAYOUT PATTERN:
- Slide 1 (content): "points" layout, no image
- Slide 2 (content): "summary" layout, HAS IMAGE
- Slide 3 (content): "points" layout, no image
- Slide 4 (content): "summary" layout, HAS IMAGE
... continue alternating

JSON FORMAT:
{{
  "title": "Short Main Title",
  "subtitle": "Date: Sunday, January 11, 2026",
  "title_image_prompt": "Modern technology workspace with laptop and digital displays, professional corporate style, dark background, 4K",
  "slides": [
    {{
      "title": "Key Technologies",
      "content": "Machine Learning: Algorithms enhance predictive capabilities in engineering applications.\\nRobotics and Automation: Processes increase efficiency and reduce human error in tasks.\\nNatural Language Processing: Streamlines project management and communication using AI-driven insights.",
      "has_image": false,
      "image_prompt": null,
      "layout_type": "points"
    }},
    {{
      "title": "Another Section",
      "content": "Comprehensive paragraph explaining the topic in detail. This summary provides valuable context and insights that help understand the broader implications and practical applications of the concept being discussed.",
      "has_image": true,
      "image_prompt": "Professional conceptual visualization, modern corporate style, dark background, 4K",
      "layout_type": "summary"
    }}
    ... GENERATE EXACTLY {content_slides_needed} SLIDES TOTAL (not including title)
  ]
}}

CONTENT FORMATTING:
- For "points": Format as "Title: Description" separated by "\\n"
  Example: "Machine Learning: Algorithms enhance predictive capabilities in engineering applications.\\nRobotics and Automation: Processes increase efficiency and reduce human error.\\nNatural Language Processing: Streamlines project management and communication using AI-driven insights."
- For "summary": Write flowing paragraph text (40-60 words)
- Each point title: 2-4 words, clear and concise
- Each point description: 8-12 words, detailed and informative
- Summary: Complete thoughts, professional tone

CRITICAL: The "slides" array must have EXACTLY {content_slides_needed} items!

Generate now:"""

        response = model.generate_content(prompt)
        outline_text = response.text.strip()
        
        if "```json" in outline_text:
            outline_text = outline_text.split("```json")[1].split("```")[0].strip()
        elif "```" in outline_text:
            outline_text = outline_text.split("```")[1].split("```")[0].strip()
        
        outline = json.loads(outline_text)
        
        # Validate slide count
        slides_generated = len(outline.get("slides", []))
        if slides_generated != content_slides_needed:
            print(f"⚠️ Expected {content_slides_needed} slides, got {slides_generated}. Adjusting...")
        
        print(f"✅ Generated outline: {outline.get('title')} ({len(outline.get('slides', []))} content slides)")
        return outline
        
    except Exception as e:
        print(f"❌ Error in generate_outline: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/slides/create")
async def create_presentation_endpoint(
    request: CreatePresentationRequest,
    authorization: str = Header(None),
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """Create presentation matching reference images"""
    if not authorization or not x_user_email:
        raise HTTPException(status_code=401, detail="Missing authorization or user email")
    
    firebase_token = authorization.replace("Bearer ", "")
    
    try:
        slides_service = await get_slides_service(x_user_email, firebase_token)
        
        # Create presentation
        presentation = slides_service.presentations().create(
            body={"title": request.title}
        ).execute()
        presentation_id = presentation.get("presentationId")
        
        print(f"📊 Created presentation: {request.title} (ID: {presentation_id})")
        
        # Get first slide
        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        first_slide = presentation.get("slides", [])[0]
        first_slide_id = first_slide["objectId"]
        
        # ==== TITLE SLIDE - Split layout: Left text with dark bg, Right image edge-to-edge ====
        title_requests = []
        
        # Delete default placeholders
        for element in first_slide.get("pageElements", []):
            if "shape" in element:
                placeholder = element.get("shape", {}).get("placeholder", {})
                if placeholder.get("type") in ["TITLE", "CENTERED_TITLE", "SUBTITLE", "BODY"]:
                    title_requests.append({
                        "deleteObject": {"objectId": element["objectId"]}
                    })
        
        # Set dark background for title slide (matching theme)
        title_requests.append({
            "updatePageProperties": {
                "objectId": first_slide_id,
                "pageProperties": {
                    "pageBackgroundFill": {
                        "solidFill": {"color": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["background"])}}
                    }
                },
                "fields": "pageBackgroundFill"
            }
        })
        
        # Image on RIGHT HALF - extends completely to edges (5 inches wide, full height)
        if request.title_image_id:
            title_requests.append({
                "createImage": {
                    "objectId": "title_bg_img",
                    "url": f"https://drive.google.com/uc?export=view&id={request.title_image_id}",
                    "elementProperties": {
                        "pageObjectId": first_slide_id,
                        "size": {
                            "width": {"magnitude": inches_to_emu(5), "unit": "EMU"},
                            "height": {"magnitude": inches_to_emu(5.625), "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": inches_to_emu(5),
                            "translateY": 0,
                            "unit": "EMU"
                        }
                    }
                }
            })
        
        # Title text (left side, centered vertically)
        title_requests.extend([
            {
                "createShape": {
                    "objectId": "title_text",
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": first_slide_id,
                        "size": {
                            "width": {"magnitude": inches_to_emu(4.5), "unit": "EMU"},
                            "height": {"magnitude": inches_to_emu(2), "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": inches_to_emu(0.3),
                            "translateY": inches_to_emu(1.5),
                            "unit": "EMU"
                        }
                    }
                }
            },
            {"insertText": {"objectId": "title_text", "text": request.title, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": "title_text",
                "textRange": {"type": "ALL"},
                "style": {
                    "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["heading"])}},
                    "fontSize": {"magnitude": 40, "unit": "PT"},
                    "fontFamily": THEME["fonts"]["heading"],
                    "bold": True
                },
                "fields": "foregroundColor,fontSize,fontFamily,bold"
            }},
            {"updateParagraphStyle": {
                "objectId": "title_text",
                "textRange": {"type": "ALL"},
                "style": {"alignment": "START", "lineSpacing": 110},
                "fields": "alignment,lineSpacing"
            }}
        ])
        
        # Subtitle (below title on left side)
        title_requests.extend([
            {
                "createShape": {
                    "objectId": "subtitle_text",
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": first_slide_id,
                        "size": {
                            "width": {"magnitude": inches_to_emu(4.5), "unit": "EMU"},
                            "height": {"magnitude": inches_to_emu(0.8), "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": inches_to_emu(0.3),
                            "translateY": inches_to_emu(3.7),
                            "unit": "EMU"
                        }
                    }
                }
            },
            {"insertText": {"objectId": "subtitle_text", "text": request.subtitle, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": "subtitle_text",
                "textRange": {"type": "ALL"},
                "style": {
                    "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["text"])}},
                    "fontSize": {"magnitude": 16, "unit": "PT"},
                    "fontFamily": THEME["fonts"]["body"]
                },
                "fields": "foregroundColor,fontSize,fontFamily"
            }},
            {"updateParagraphStyle": {
                "objectId": "subtitle_text",
                "textRange": {"type": "ALL"},
                "style": {"alignment": "START"},
                "fields": "alignment"
            }}
        ])
        
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": title_requests}
        ).execute()
        print("✅ Title slide created (dark bg, text left, image right edge-to-edge)")
        
        # ==== CONTENT SLIDES ====
        slide_ids = [f"slide_{i}" for i in range(1, len(request.slides) + 1)]
        
        if slide_ids:
            create_requests = [
                {
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {"predefinedLayout": "BLANK"}
                    }
                } for slide_id in slide_ids
            ]
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": create_requests}
            ).execute()
            print(f"✅ Created {len(slide_ids)} content slides")
        
        # Add content
        content_requests = []
        image_index = 0
        
        for i, slide_data in enumerate(request.slides, start=1):
            slide_id = f"slide_{i}"
            
            # Dark background
            content_requests.append({
                "updatePageProperties": {
                    "objectId": slide_id,
                    "pageProperties": {
                        "pageBackgroundFill": {
                            "solidFill": {"color": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["background"])}}
                        }
                    },
                    "fields": "pageBackgroundFill"
                }
            })
            
            if slide_data.layout_type == "points":
                # Points layout (matching reference image 1)
                content_requests.extend(
                    create_points_layout(slide_id, i, slide_data.title, slide_data.content)
                )
            else:  # summary
                # Summary layout with image
                has_image = slide_data.has_image and image_index < len(request.image_file_ids)
                image_id = request.image_file_ids[image_index] if has_image else None
                
                content_requests.extend(
                    create_summary_layout(slide_id, i, slide_data.title, slide_data.content, image_id)
                )
                
                if has_image:
                    image_index += 1
        
        # Execute all content requests
        if content_requests:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": content_requests}
            ).execute()
            print(f"✅ Added content ({len(request.slides)} slides, {image_index} images)")
        
        return {
            "success": True,
            "presentation_id": presentation_id,
            "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
            "view_url": f"https://docs.google.com/presentation/d/{presentation_id}/present",
            "message": f"Created presentation with {len(request.slides) + 1} slides!"
        }
        
    except Exception as e:
        print(f"❌ Error creating presentation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def create_points_layout(slide_id, slide_idx, title, content):
    """
    Points layout - COMPACT NUMBERED DESIGN (matching reference image)
    Small numbered boxes on left, title + description next to them
    """
    requests = []
    
    # Parse points from content
    points = [p.strip() for p in content.split('\n') if p.strip()]
    num_points = min(len(points), 4)  # Max 4 points
    
    # Title
    requests.extend([
        {
            "createShape": {
                "objectId": f"title_{slide_idx}",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": inches_to_emu(9), "unit": "EMU"},
                        "height": {"magnitude": inches_to_emu(0.6), "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": inches_to_emu(0.5),
                        "translateY": inches_to_emu(0.5),
                        "unit": "EMU"
                    }
                }
            }
        },
        {"insertText": {"objectId": f"title_{slide_idx}", "text": title, "insertionIndex": 0}},
        {"updateTextStyle": {
            "objectId": f"title_{slide_idx}",
            "textRange": {"type": "ALL"},
            "style": {
                "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["heading"])}},
                "fontSize": {"magnitude": 32, "unit": "PT"},
                "fontFamily": THEME["fonts"]["heading"]
            },
            "fields": "foregroundColor,fontSize,fontFamily"
        }}
    ])
    
    # Create compact numbered items (matching reference)
    start_y = 1.5
    item_height = 1.2
    number_box_size = 0.6
    
    for idx, point_text in enumerate(points[:num_points]):
        # Parse title and description
        parts = point_text.split(':', 1)
        if len(parts) == 2:
            item_title = parts[0].strip()
            item_desc = parts[1].strip()
        else:
            item_title = point_text[:30] + "..." if len(point_text) > 30 else point_text
            item_desc = point_text
        
        item_y = start_y + (idx * item_height)
        
        # Numbered box (small, left side)
        number_box_id = f"num_box_{slide_idx}_{idx}"
        requests.extend([
            {
                "createShape": {
                    "objectId": number_box_id,
                    "shapeType": "ROUND_RECTANGLE",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": inches_to_emu(number_box_size), "unit": "EMU"},
                            "height": {"magnitude": inches_to_emu(number_box_size), "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": inches_to_emu(0.5),
                            "translateY": inches_to_emu(item_y),
                            "unit": "EMU"
                        }
                    }
                }
            },
            {"updateShapeProperties": {
                "objectId": number_box_id,
                "shapeProperties": {
                    "shapeBackgroundFill": {
                        "solidFill": {"color": {"rgbColor": hex_to_rgb_dict("#E5E7EB")}}
                    },
                    "outline": {"propertyState": "NOT_RENDERED"}
                },
                "fields": "shapeBackgroundFill,outline"
            }},
            {"insertText": {"objectId": number_box_id, "text": str(idx + 1), "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": number_box_id,
                "textRange": {"type": "ALL"},
                "style": {
                    "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict("#1F2937")}},
                    "fontSize": {"magnitude": 28, "unit": "PT"},
                    "fontFamily": THEME["fonts"]["heading"],
                    "bold": True
                },
                "fields": "foregroundColor,fontSize,fontFamily,bold"
            }},
            {"updateParagraphStyle": {
                "objectId": number_box_id,
                "textRange": {"type": "ALL"},
                "style": {"alignment": "CENTER"},
                "fields": "alignment"
            }}
        ])
        
        # Title text (next to number)
        title_id = f"item_title_{slide_idx}_{idx}"
        requests.extend([
            {
                "createShape": {
                    "objectId": title_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": inches_to_emu(8.2), "unit": "EMU"},
                            "height": {"magnitude": inches_to_emu(0.3), "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": inches_to_emu(1.3),
                            "translateY": inches_to_emu(item_y),
                            "unit": "EMU"
                        }
                    }
                }
            },
            {"insertText": {"objectId": title_id, "text": item_title, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": title_id,
                "textRange": {"type": "ALL"},
                "style": {
                    "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["heading"])}},
                    "fontSize": {"magnitude": 20, "unit": "PT"},
                    "fontFamily": THEME["fonts"]["heading"],
                    "bold": True
                },
                "fields": "foregroundColor,fontSize,fontFamily,bold"
            }}
        ])
        
        # Description text (below title)
        desc_id = f"item_desc_{slide_idx}_{idx}"
        requests.extend([
            {
                "createShape": {
                    "objectId": desc_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": inches_to_emu(8.2), "unit": "EMU"},
                            "height": {"magnitude": inches_to_emu(0.7), "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1, "scaleY": 1,
                            "translateX": inches_to_emu(1.3),
                            "translateY": inches_to_emu(item_y + 0.35),
                            "unit": "EMU"
                        }
                    }
                }
            },
            {"insertText": {"objectId": desc_id, "text": item_desc, "insertionIndex": 0}},
            {"updateTextStyle": {
                "objectId": desc_id,
                "textRange": {"type": "ALL"},
                "style": {
                    "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["text"])}},
                    "fontSize": {"magnitude": 14, "unit": "PT"},
                    "fontFamily": THEME["fonts"]["body"]
                },
                "fields": "foregroundColor,fontSize,fontFamily"
            }},
            {"updateParagraphStyle": {
                "objectId": desc_id,
                "textRange": {"type": "ALL"},
                "style": {"lineSpacing": 115},
                "fields": "lineSpacing"
            }}
        ])
    
    return requests


def create_summary_layout(slide_id, slide_idx, title, content, image_id):
    """
    Summary layout - Text summary with side image
    """
    requests = []
    
    # Title
    requests.extend([
        {
            "createShape": {
                "objectId": f"title_{slide_idx}",
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": inches_to_emu(9), "unit": "EMU"},
                        "height": {"magnitude": inches_to_emu(0.6), "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": inches_to_emu(0.5),
                        "translateY": inches_to_emu(0.5),
                        "unit": "EMU"
                    }
                }
            }
        },
        {"insertText": {"objectId": f"title_{slide_idx}", "text": title, "insertionIndex": 0}},
        {"updateTextStyle": {
            "objectId": f"title_{slide_idx}",
            "textRange": {"type": "ALL"},
            "style": {
                "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["heading"])}},
                "fontSize": {"magnitude": 32, "unit": "PT"},
                "fontFamily": THEME["fonts"]["heading"]
            },
            "fields": "foregroundColor,fontSize,fontFamily"
        }}
    ])
    
    # Summary text box
    if image_id:
        # Text on left, image on right
        text_w = 5.0
        text_x = 0.5
        img_x, img_y = 5.8, 1.2
        img_w, img_h = 3.7, 4.0
    else:
        # Full width text
        text_w = 9.0
        text_x = 0.5
    
    summary_box_id = f"summary_{slide_idx}"
    requests.extend([
        {
            "createShape": {
                "objectId": summary_box_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": inches_to_emu(text_w), "unit": "EMU"},
                        "height": {"magnitude": inches_to_emu(4.0), "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": inches_to_emu(text_x),
                        "translateY": inches_to_emu(1.3),
                        "unit": "EMU"
                    }
                }
            }
        },
        {"insertText": {"objectId": summary_box_id, "text": content, "insertionIndex": 0}},
        {"updateTextStyle": {
            "objectId": summary_box_id,
            "textRange": {"type": "ALL"},
            "style": {
                "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb_dict(THEME["colors"]["text"])}},
                "fontSize": {"magnitude": 16, "unit": "PT"},
                "fontFamily": THEME["fonts"]["body"]
            },
            "fields": "foregroundColor,fontSize,fontFamily"
        }},
        {"updateParagraphStyle": {
            "objectId": summary_box_id,
            "textRange": {"type": "ALL"},
            "style": {"lineSpacing": 140},
            "fields": "lineSpacing"
        }}
    ])
    
    # Add image if provided
    if image_id:
        requests.append({
            "createImage": {
                "objectId": f"img_{slide_idx}",
                "url": f"https://drive.google.com/uc?export=view&id={image_id}",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": inches_to_emu(img_w), "unit": "EMU"},
                        "height": {"magnitude": inches_to_emu(img_h), "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX": inches_to_emu(img_x),
                        "translateY": inches_to_emu(img_y),
                        "unit": "EMU"
                    }
                }
            }
        })
    
    return requests

