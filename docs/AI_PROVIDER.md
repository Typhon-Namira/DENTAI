# AI provider

Implement `DentalAIProvider.analyze_xray` and select it in the provider factory. Provider output remains unconfirmed: it creates `source=AI`, `review_status=PENDING` findings. Doctor confirmation creates a separate `source=DENTIST` record. The bundled provider is deterministic mock decision support and makes no accuracy, regulatory, or diagnosis claim.

