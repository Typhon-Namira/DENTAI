"""Production identity extraction boundary and conservative V2 state mapping."""
from __future__ import annotations
from abc import ABC,abstractmethod
from pathlib import Path
from typing import Any
from .models import ExtractedField,ExtractedIdentity,ProductIdentityState,PatientProfile,PatientMatch
from .patient_identity import DICOM_FIELDS
from .patient_matching import normalize_text

IDENTITY_FIELDS={"patient_name","patient_id","date_of_birth","study_date","accession_number","clinic_name"}

class IdentityExtractionResult(dict):
    """JSON-ready extraction envelope; raw text is restricted clinical data."""

class IdentityExtractor(ABC):
    @abstractmethod
    def extract(self,path:Path)->IdentityExtractionResult: ...

class NoOpIdentityExtractor(IdentityExtractor):
    def extract(self,path:Path)->IdentityExtractionResult:
        return IdentityExtractionResult(fields={},raw_text=None,provider="NONE")

class OCRIdentityExtractor(IdentityExtractor):
    """Adapter over a replaceable OCR provider returning value/confidence/region."""
    def __init__(self,provider): self.provider=provider
    def extract(self,path:Path)->IdentityExtractionResult:
        raw=self.provider.extract(path);fields={};raw_text=None
        for key,item in raw.items():
            if isinstance(item,dict): value=item.get("value");confidence=float(item.get("confidence",0));region=item.get("source_region")
            else: value,confidence=item[:2];region=item[2] if len(item)>2 else None
            if key=="raw_text": raw_text=str(value);continue
            if key in IDENTITY_FIELDS and value:
                fields[key]=ExtractedField(value=str(value),source="OCR",confidence=confidence,verified=False,normalized_value=normalize_text(value),source_region=region)
        return IdentityExtractionResult(fields=fields,raw_text=raw_text,provider=type(self.provider).__name__)

class DICOMIdentityExtractor(IdentityExtractor):
    def extract(self,path:Path)->IdentityExtractionResult:
        try: import pydicom
        except ImportError: return IdentityExtractionResult(fields={},raw_text=None,provider="DICOM_UNAVAILABLE")
        ds=pydicom.dcmread(str(path),stop_before_pixels=True,force=True);fields={}
        for tag,name in DICOM_FIELDS.items():
            value=str(getattr(ds,tag,"")).strip()
            if not value: continue
            key=name if name in IDENTITY_FIELDS else tag
            fields[key]=ExtractedField(value=value.replace("^"," ") if tag=="PatientName" else value,source="DICOM",confidence=1.0,verified=False,normalized_value=normalize_text(value))
        return IdentityExtractionResult(fields=fields,raw_text=None,provider="DICOM")

def extracted_identity(result:IdentityExtractionResult)->ExtractedIdentity:
    known={k:v for k,v in result.get("fields",{}).items() if k in ExtractedIdentity.model_fields}
    metadata={k:v for k,v in result.get("fields",{}).items() if k not in ExtractedIdentity.model_fields}
    return ExtractedIdentity(**known,metadata=metadata)

def decide_identity_state(identity:ExtractedIdentity,matches:list[PatientMatch],*,minimum_confidence:float=.75)->ProductIdentityState:
    evidence=[x for x in (identity.patient_id,identity.patient_name,identity.date_of_birth) if x and x.value]
    if not evidence:return ProductIdentityState.IDENTITY_NOT_FOUND
    if len(matches)>1 and matches[0].match_score-matches[1].match_score<.10:return ProductIdentityState.IDENTITY_REVIEW_REQUIRED
    if matches and matches[0].match_score>=.95 and any(r in matches[0].match_reasons for r in ("EXACT_CLINIC_PATIENT_ID","EXACT_DICOM_PATIENT_ID","EXACT_EXTERNAL_PATIENT_ID")):
        return ProductIdentityState.IDENTITY_MATCHED_EXISTING
    if max(x.confidence for x in evidence)<minimum_confidence:return ProductIdentityState.IDENTITY_REVIEW_REQUIRED
    if identity.patient_name and not identity.patient_id:return ProductIdentityState.IDENTITY_REVIEW_REQUIRED
    return ProductIdentityState.IDENTITY_NEW_PATIENT_CANDIDATE

def profile_to_patient(profile:PatientProfile):
    from .models import Patient
    return Patient(patient_id=profile.patient_id,clinic_id=profile.clinic_id,clinic_patient_number=profile.clinic_local_identifier,full_name=profile.display_name,date_of_birth=profile.date_of_birth)
