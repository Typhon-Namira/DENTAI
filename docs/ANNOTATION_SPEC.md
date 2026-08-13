# OPG annotation specification

Use an open-source annotation tool capable of COCO JSON export. Every image and derivative must carry a stable de-identified `patient_group_id` and `source_image_id`. Supported geometry is a normalized `[x, y, width, height]` bounding box or segmentation polygon. Required fields are canonical condition label, original source label, optional FDI tooth number, reviewer pseudonym, review status, annotation version, and dataset license identifier. Severity may be recorded only when a clinician-approved definition is present.

Originals, crops, alternate views, and augmentations sharing a patient/image source must retain the same group ID so split logic cannot leak them across train, validation, and test. Operational clinic records are not eligible for annotation/training export without explicit authorization, de-identification, audit, consent/governance approval, and a versioned export manifest.

