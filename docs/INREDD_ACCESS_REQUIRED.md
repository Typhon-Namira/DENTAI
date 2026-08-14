# InReDD-PAN924 access required

Dataset: InReDD-Dataset-PAN924 v1.0.0  
Version DOI: https://doi.org/10.13026/r5nt-we67  
Latest DOI: https://doi.org/10.13026/85hv-ct26  
Access class: PhysioNet **Contributor Review**  
Agreement: PhysioNet Contributor Review Health Data Use Agreement 1.5.0

The files are not anonymously or immediately downloadable. Do not share credentials or downloaded
files with another user; the agreement makes access individual.

## Required user actions

1. Create or sign in to a PhysioNet account: https://physionet.org/login/.
2. Complete PhysioNet credentialing at https://physionet.org/settings/profile/ using an
   institutional/educational email and an appropriate professional reference.
3. Complete recognized Good Clinical Practice training. PhysioNet recommends the free CITI
   “Data or Specimens Only Research” course under “Massachusetts Institute of Technology
   Affiliates”: https://physionet.org/about/citi-course/.
4. Upload the full CITI **training report**, not only the certificate, and wait for credentialing
   approval. PhysioNet says normal review can take several business days and currently warns that
   staffing changes may cause longer delays.
5. Open https://physionet.org/content/inredd-dataset-pan924/1.0.0/, accept the Contributor Review
   Health Data Use Agreement 1.5.0, and submit a project-specific request to the InReDD authors.
   Describe DENTAI as research-only tooth detection/instance segmentation/FDI experimentation,
   the intended security controls, and the public code-repository obligation for publications.
6. Wait for author approval. Access is not granted merely by completing PhysioNet credentialing.
7. Once approved, authenticate using the individual approved account and use only the download
   command displayed by PhysioNet. Do not paste credentials into the repository or commit them.

## Verified record contents (metadata only)

- 924 anonymized panoramic radiographs.
- Original 2903×1536 JPEG images, described as lossless/16-bit clinical exports subsequently
  reduced from 300 to 90 dpi.
- 924 images with mouth/tooth rectangular annotations: 20,033 tooth boxes plus 924 mouth boxes.
- 200 images with 4,621 tooth polygon masks and FDI position labels.
- COCO-compatible combined and per-image JSON files (`mouth_and_teeth_labels` and
  `teeth_fdi_labels`), plus utility scripts.
- Published image records contain a random identifier, age, and sex. The primary record does not
  claim that multiple records from the same patient can be linked or excluded; patient-level
  independence therefore remains unverified until the actual files/documentation are audited.

Exact filenames, sizes, archive checksums, and directory structure are not exposed to an
unauthorized session and must not be guessed. On approval, ingest into
`data/raw/inredd_dataset_pan924/1.0.0/`, preserve downloads unchanged, compute SHA-256, and rerun the
full audit before creating splits.

