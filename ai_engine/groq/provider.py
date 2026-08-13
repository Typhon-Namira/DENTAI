import json

import httpx
from pydantic import BaseModel, Field


class GroqClinicalSummary(BaseModel):
    doctor_summary: str
    important_changes: list[str] = Field(default_factory=list)
    monitoring_points: list[str] = Field(default_factory=list)
    questions_for_doctor: list[str] = Field(default_factory=list)
    patient_message_draft: str


class GroqClinicalSummaryProvider:
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str, timeout_seconds: int = 20):
        self.api_key, self.model, self.timeout_seconds = api_key, model, timeout_seconds

    async def summarize(self, structured_evidence: dict) -> GroqClinicalSummary:
        system = (
            "Return JSON only. Use supplied structured evidence exclusively. "
            "Do not create findings, change confidence, diagnose, prescribe, "
            "assign unsupported urgency, or expose alarming "
            "unconfirmed findings in the patient message. Dentist review is required."
        )
        schema = GroqClinicalSummary.model_json_schema()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(structured_evidence)},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "dentai_clinical_summary",
                            "schema": schema,
                            "strict": True,
                        },
                    },
                    "temperature": 0,
                },
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return GroqClinicalSummary.model_validate_json(content)
