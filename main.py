try: from pip._internal.operations import freeze
except ImportError: # pip < 10.0
    from pip.operations import freeze

pkgs = freeze.freeze()
for pkg in pkgs: print(pkg)
import os 
from fastapi import FastAPI, HTTPException, File, UploadFile,Query
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import google.generativeai as genai
import json
from PIL import Image
import io
import requests
import fitz  # PyMuPDF
import os


from dotenv import load_dotenv
# Load the environment variables from the .env file
load_dotenv()

# Configure Gemini API
secret = os.environ["GEMINI"]
genai.configure(api_key=secret)
model_vision = genai.GenerativeModel('gemini-1.5-flash')
model_text = genai.GenerativeModel('gemini-pro')






app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





def vision(file_content):
    # Open the PDF
    pdf_document = fitz.open("pdf",file_content)
    gemini_input = ["extract the whole text"]
    # Iterate through the pages
    for page_num in range(len(pdf_document)):
        # Select the page
        page = pdf_document.load_page(page_num)
        
        # Render the page to a pixmap (image)
        pix = page.get_pixmap()
        print(type(pix))
        
        # Convert the pixmap to bytes
        img_bytes = pix.tobytes("png")
        
        # Convert bytes to a PIL Image
        img = Image.open(io.BytesIO(img_bytes))
        gemini_input.append(img)
        # # Save the image if needed
        # img.save(f'page_{page_num + 1}.png')
    
    print("PDF pages converted to images successfully!")
    
    # Now you can pass the PIL image to the model_vision
    response = model_vision.generate_content(gemini_input).text
    return response


@app.post("/get_ocr_data/")
async def get_data(user_id: str = Query(...),input_file: UploadFile = File(...)):
    #try:
        # Determine the file type by reading the first few bytes
        file_content = await input_file.read()
        file_type = input_file.content_type
        
        text = ""

        if file_type == "application/pdf":
                # Read PDF file using PyPDF2
                pdf_reader = PdfReader(io.BytesIO(file_content))
                for page in pdf_reader.pages:
                    text += page.extract_text()
                    
                if len(text)<10:
                   print("vision called")
                   text = vision(file_content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        

        # Call Gemini (or another model) to extract required data
        prompt = f"""This is CV data: {text.strip()} 
                IMPORTANT: The output should be a JSON array! Make Sure the JSON is valid.
                                                                  
                Example Output:
                [
                    "firstname" : "firstname",
                    "lastname" : "lastname",
                    "email" : "email",
                    "contact_number" : "contact number",
                    "home_address" : "full home address",
                    "home_town" : "home town or city",
                    "total_years_of_experience" : "total years of experience",
                    "education": "Institution Name, Degree Name,
                    "LinkedIn_link" : "LinkedIn link",
                    "positions": [ "Job title 1", "Job title 2", "Job title 3" ],
                    "industry": "[ "industry 1", "industry 2", "industry 3" ],  # List all industries the candidate has worked in, inferred from job titles, companies, or experience",
                    "experience" : "experience",
                    "skills" : skills(Identify and list specific skills mentioned in both the skills section and inferred from the experience section)
                ]
                """
        
        response = model_text.generate_content(prompt)
        print(response.text)
        data = json.loads(response.text.replace("JSON", "").replace("json", "").replace("```", ""))
        return {"data": data}

    #except Exception as e:
        #raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")