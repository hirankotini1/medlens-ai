"""
MEDLENS — Multi-Format Health Report File Parser
Supports CSV, PDF (pypdf), Plain Text, and Scanned Image files.
Extracts raw text streams and structured records while separating metadata from laboratory data.
"""

import io 
import re 
import csv 
import base64 
from typing import Dict ,Any ,List ,Tuple 
from pypdf import PdfReader 


ALLOWED_EXTENSIONS ={".pdf",".csv",".jpg",".jpeg",".png",".txt"}
MAX_FILE_SIZE_BYTES =10 *1024 *1024 


def validate_file_metadata (filename :str ,file_bytes :bytes )->str :
    """Validate file extension and size. Returns normalized extension."""
    if not filename :
        raise ValueError ("Filename is missing.")

    ext ="."+filename .rsplit (".",1 )[-1 ].lower ()if "."in filename else ""
    if ext not in ALLOWED_EXTENSIONS :
        raise ValueError (f"Unsupported file format '{ext }'. Allowed formats: PDF, CSV, JPG, JPEG, PNG, TXT.")

    if len (file_bytes )>MAX_FILE_SIZE_BYTES :
        raise ValueError (f"File size ({len (file_bytes )/(1024 *1024 ):.1f}MB) exceeds maximum allowable limit of 10MB.")

    if len (file_bytes )==0 :
        raise ValueError ("Uploaded file is empty.")

    return ext 


def parse_csv_report (file_bytes :bytes )->Tuple [Dict [str ,Any ],List [Dict [str ,Any ]]]:
    """
    Parse CSV laboratory file into metadata dict and raw biomarker items list.
    Supports both key-value header metadata pairs and tabular biomarker columns.
    """
    try :
        decoded =file_bytes .decode ("utf-8-sig",errors ="replace")
    except Exception as e :
        raise ValueError (f"Failed to decode CSV text: {e }")

    reader =csv .reader (io .StringIO (decoded ))
    rows =[[field .strip ()for field in r ]for r in reader if any (field .strip ()for field in r )]
    if not rows :
        raise ValueError ("CSV report contains no readable rows.")

    metadata :Dict [str ,Any ]={}
    parsed_items :List [Dict [str ,Any ]]=[]


    first_row_lower =[c .lower ()for c in rows [0 ]]
    is_horizontal_table =(
    len (rows )>=2 and 
    len (rows [0 ])>=3 and 
    any (any (k in col for k in ["patient","age","gender","hemoglobin","hgb","bilirubin","tsh"])for col in first_row_lower )and 
    not any (first_row_lower [0 ]==h for h in ["investigation","biomarker","parameter","test name","test"])
    )

    if is_horizontal_table :
        headers =rows [0 ]
        data_row =rows [1 ]
        for col_name ,val in zip (headers ,data_row ):
            clean_k =re .sub (r'[^a-zA-Z0-9\s]',' ',col_name .lower ()).strip ()
            if any (k in clean_k for k in ["patient id","uhid","mrn","pid"]):
                metadata ["patient_id"]=val 
            elif any (k in clean_k for k in ["patient name","name"]):
                metadata ["patient_name"]=val 
            elif clean_k in ["age","patient age"]:
                m =re .search (r'\d+',val )
                if m :metadata ["age"]=int (m .group (0 ))
            elif clean_k in ["gender","sex"]:
                metadata ["gender"]=val .capitalize ()
            elif any (k in clean_k for k in ["report id","accession","bill no"]):
                metadata ["report_id"]=val 
            elif clean_k in ["date","report date"]:
                metadata ["report_date"]=val 
            else :
                parsed_items .append ({"parameter":col_name ,"value_raw":val })
        return metadata ,parsed_items 


    for row in rows :
        if len (row )==2 :
            key_raw ,val_raw =row [0 ].strip (),row [1 ].strip ()
            clean_k =re .sub (r'[^a-zA-Z0-9\s]',' ',key_raw .lower ()).strip ()
            if any (k in clean_k for k in ["patient id","uhid","mrn","pid"]):
                metadata ["patient_id"]=val_raw 
            elif any (k in clean_k for k in ["patient name","name"]):
                metadata ["patient_name"]=val_raw 
            elif clean_k in ["age","patient age"]:
                m =re .search (r'\d+',val_raw )
                if m :metadata ["age"]=int (m .group (0 ))
            elif clean_k in ["gender","sex"]:
                metadata ["gender"]=val_raw .capitalize ()
            elif any (k in clean_k for k in ["report id","accession","bill no"]):
                metadata ["report_id"]=val_raw 
            elif clean_k in ["date","report date"]:
                metadata ["report_date"]=val_raw 
            elif clean_k in ["referring doctor","referred by","doctor"]:
                metadata ["referring_doctor"]=val_raw 
            else :
                parsed_items .append ({"parameter":key_raw ,"value_raw":val_raw })
        elif len (row )>=3 :
            row_lower =[c .lower ()for c in row ]
            if any (h in row_lower [0 ]for h in ["investigation","biomarker","parameter","test"]):
                continue 
            parsed_items .append ({
            "parameter":row [0 ],
            "value_raw":row [1 ],
            "unit":row [2 ]if len (row )>2 else "",
            "reference_range":row [3 ]if len (row )>3 else "",
            "status":row [4 ]if len (row )>4 else ""
            })

    return metadata ,parsed_items 


def parse_pdf_report (file_bytes :bytes )->Tuple [str ,List [Dict [str ,Any ]]]:
    """
    Parse PDF laboratory report using pypdf.
    Uses layout-mode spatial text extraction to preserve table columns,
    falls back to plain stream extraction, and checks for raster images if text is absent.
    """
    try :
        pdf_stream =io .BytesIO (file_bytes )
        reader =PdfReader (pdf_stream )
        layout_text =""
        plain_text =""
        image_data_uris =[]

        for page in reader .pages :

            try :
                p_layout =page .extract_text (extraction_mode ="layout")
                if p_layout :
                    layout_text +=p_layout +"\n"
            except Exception :
                pass 


            try :
                p_plain =page .extract_text ()
                if p_plain :
                    plain_text +=p_plain +"\n"
            except Exception :
                pass 


            if hasattr (page ,'images')and page .images :
                for img_obj in page .images :
                    try :
                        img_bytes =img_obj .data 
                        img_name =img_obj .name .lower ()
                        mime ="image/png"if img_name .endswith (".png")else "image/jpeg"
                        b64 =base64 .b64encode (img_bytes ).decode ("utf-8")
                        image_data_uris .append (f"data:{mime };base64,{b64 }")
                    except Exception :
                        pass 
    except Exception as e :
        raise ValueError (f"Corrupted or password-protected PDF document: {e }")


    chosen_text =layout_text if len (layout_text .strip ())>=len (plain_text .strip ())*0.5 and layout_text .strip ()else plain_text 

    if not chosen_text .strip ():
        if image_data_uris :

            return f"[Scanned Image PDF: {len (image_data_uris )} page images detected]",[]
        raise ValueError ("Could not extract readable text from PDF. The document may be an empty or unsupported scanned raster image.")

    return chosen_text ,[]


def parse_image_report (file_bytes :bytes ,filename :str )->Tuple [str ,str ]:
    """Encodes report image as base64 for vision processing."""
    mime_type ="image/jpeg"
    if filename .lower ().endswith (".png"):
        mime_type ="image/png"

    b64_data =base64 .b64encode (file_bytes ).decode ("utf-8")
    return f"data:{mime_type };base64,{b64_data }",f"[Image Report: {filename } ({len (file_bytes )} bytes)]"
