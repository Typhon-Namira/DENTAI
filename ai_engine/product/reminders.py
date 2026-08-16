"""Reminder scheduling domain service; delivery providers are intentionally absent."""
from datetime import datetime
from .models import Reminder
from .patient_matching import new_id

CHANNELS={"SMS","EMAIL","WHATSAPP","IN_APP"}

def schedule_reminder(*,clinic_id:str,patient_id:str,case_id:str,scheduled_at:datetime,
                      channel:str,reminder_type:str,message_template:str,created_by:str,
                      tooth_fdi:str|None=None)->Reminder:
    if channel not in CHANNELS:
        raise ValueError(f"unsupported reminder channel: {channel}")
    return Reminder(reminder_id=new_id("REM"),clinic_id=clinic_id,patient_id=patient_id,
                    case_id=case_id,tooth_fdi=tooth_fdi,reminder_type=reminder_type,
                    scheduled_at=scheduled_at,channel=channel,
                    message_template=message_template,created_by=created_by)

class ReminderDeliveryProvider:
    """Future provider boundary. V1 schedules data but sends no messages."""
    def send(self,reminder:Reminder)->None:
        raise NotImplementedError
