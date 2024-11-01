from fastapi import FastAPI, HTTPException, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
from PIL import Image
import io
import requests
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to process PDF using vision model (if needed)
def vision(file_path):
    pdf_document = fitz.open(file_path)
    gemini_input = ["extract the whole text"]
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        gemini_input.append(img)
    
    # Call Gemini's model to process the images
    response = model_vision.generate_content(gemini_input).text
    return response

# API endpoint to process the PDF
@app.post("/get_ocr_data/")
async def get_data(user_id: str = Query(...), file_path: str = Query(...)):
    try:
        # Read the file content from the provided file path
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="File not found")

        text = ""
        with open(file_path, "rb") as file:
            file_content = file.read()
            pdf_reader = PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                text += page.extract_text()
        
        if len(text) < 10:
            text = vision(file_path)  # Call vision if text extraction fails

        # Prompt to extract relevant information
        prompt = f"""This is CV data: {text.strip()} 
        IMPORTANT: The output should be a JSON array! Make sure the JSON is valid.
        Example Output:
        [
            "firstname": "firstname",
            "lastname": "lastname",
            "email": "email",
            "gender": "gender",
            "contact_number": "contact number",
            "home_address": "full home address",
            "home_town": "home town or city",
            "total_years_of_experience": "total years of experience",
            "LinkedIn_link": "LinkedIn link",
            "positions": ["Job title 1", "Job title 2"],
            "industry": "industry of work",
            "experience": "experience",
            "skills": ["skill1", "skill2"]
        ]"""
        
        response = model_text.generate_content(prompt)
        data = json.loads(response.text.replace("JSON", "").replace("json", "").replace("```", ""))
        return {"data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
