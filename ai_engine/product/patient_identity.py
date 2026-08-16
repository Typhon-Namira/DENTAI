"""DICOM and vendor-neutral OCR identity extraction."""
from abc import ABC,abstractmethod
from pathlib import Path
from typing import Any
from .models import ExtractedField,ExtractedIdentity,IdentityResolution,IdentityStatus

DICOM_FIELDS={"PatientName":"patient_name","PatientID":"patient_id","PatientBirthDate":"date_of_birth","PatientSex":"sex","StudyDate":"study_date","StudyTime":"study_time","StudyInstanceUID":"study_instance_uid","AccessionNumber":"accession_number","InstitutionName":"clinic_name","Manufacturer":"manufacturer","ManufacturerModelName":"manufacturer_model_name"}
class IdentityOCRProvider(ABC):
 @abstractmethod
 def extract(self,image_path:Path)->dict[str,tuple[str,float]]: ...
class NoOpOCRProvider(IdentityOCRProvider):
 def extract(self,image_path:Path): return {}
class TesseractOCRProvider(IdentityOCRProvider):
 """Optional local adapter. Parsing remains conservative and vendor-configurable."""
 def extract(self,image_path:Path):
  try:
   import pytesseract
   from PIL import Image
  except ImportError: return {}
  text=pytesseract.image_to_string(Image.open(image_path));return {"raw_text":(text,.50)} if text.strip() else {}
def extract_dicom_identity(path:Path)->ExtractedIdentity:
 try: import pydicom
 except ImportError: return ExtractedIdentity()
 ds=pydicom.dcmread(str(path),stop_before_pixels=True,force=True);values={};meta={}
 for tag,name in DICOM_FIELDS.items():
  value=str(getattr(ds,tag,"")).strip()
  if not value:continue
  field=ExtractedField(value=value.replace('^',' ') if tag=='PatientName'else value,source="DICOM",confidence=1.0,verified=False)
  if name in ExtractedIdentity.model_fields:values[name]=field
  else:meta[name]=field
 values['metadata']=meta;return ExtractedIdentity(**values)
def extract_image_identity(path:Path,provider:IdentityOCRProvider|None=None)->ExtractedIdentity:
 raw=(provider or NoOpOCRProvider()).extract(path);values={};meta={}
 for name,(value,confidence)in raw.items():
  field=ExtractedField(value=value,source="OCR",confidence=confidence,verified=False)
  if name in ExtractedIdentity.model_fields:values[name]=field
  else:meta[name]=field
 values['metadata']=meta;return ExtractedIdentity(**values)
def extract_identity(path:str|Path,provider:IdentityOCRProvider|None=None)->IdentityResolution:
 p=Path(path);identity=extract_dicom_identity(p) if p.suffix.lower()in('.dcm','.dicom')else extract_image_identity(p,provider)
 found=any(getattr(identity,x)and getattr(identity,x).value for x in ('patient_name','patient_id','date_of_birth'))
 return IdentityResolution(status=IdentityStatus.IDENTITY_NEEDS_CONFIRMATION if found else IdentityStatus.IDENTITY_NOT_FOUND,extracted_identity=identity,requires_confirmation=True,confidence=max([getattr(identity,x).confidence for x in ('patient_name','patient_id','date_of_birth')if getattr(identity,x)],default=0))
