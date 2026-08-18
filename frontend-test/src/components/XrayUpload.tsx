import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { XRay } from "../api/types";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "application/dicom"];
const MAX_SIZE_BYTES = 15 * 1024 * 1024;

interface XrayUploadProps {
  patientId: string;
  onUploaded: (xray: XRay) => Promise<void> | void;
}

function normalizedFile(file: File): File {
  if (!file.type && file.name.toLowerCase().endsWith(".dcm")) {
    return new File([file], file.name, { type: "application/dicom", lastModified: file.lastModified });
  }
  return file;
}

export function XrayUpload({ patientId, onUploaded }: XrayUploadProps) {
  const uploadRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [state, setState] = useState<"idle" | "selected" | "uploading" | "uploaded" | "error">("idle");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    setFile(null);
    setPreview("");
    setState("idle");
    setError("");
    setDragging(false);
  }, [patientId]);

  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function select(candidate: File) {
    const next = normalizedFile(candidate);
    setError("");
    if (!ACCEPTED_TYPES.includes(next.type)) {
      setFile(null);
      setState("error");
      setError("Unsupported file type. Use JPEG, PNG, WebP, or DICOM.");
      return;
    }
    if (next.size > MAX_SIZE_BYTES) {
      setFile(null);
      setState("error");
      setError("File is larger than the backend default limit of 15 MB.");
      return;
    }
    setFile(next);
    setState("selected");
  }

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const candidate = event.target.files?.item(0);
    if (candidate) select(candidate);
    event.currentTarget.value = "";
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const candidate = event.dataTransfer.files.item(0);
    if (candidate) select(candidate);
  }

  async function upload() {
    if (!file) return;
    setState("uploading");
    setError("");
    try {
      const xrayRecord = await api.uploadXray(patientId, file);
      setState("uploaded");
      await onUploaded(xrayRecord);
    } catch (reason) {
      setState("error");
      setError(errorMessage(reason));
    }
  }

  return (
    <section className="card upload-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AI Workspace</p>
          <h3>Upload or capture an X-ray</h3>
        </div>
        <span className={"upload-state " + state}>{state}</span>
      </div>

      <div
        className={"drop-zone" + (dragging ? " dragging" : "")}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <span className="upload-icon" aria-hidden="true">⌁</span>
        <strong>Drop an X-ray image here</strong>
        <span>or choose the easiest way to add it</span>
        <div className="upload-choice-row">
          <button className="button button-accent" type="button" onClick={() => uploadRef.current?.click()}>
            ↑ Upload file
          </button>
          <button className="button button-secondary" type="button" onClick={() => cameraRef.current?.click()}>
            ◉ Take photo
          </button>
          <button className="button button-secondary" type="button" onClick={() => galleryRef.current?.click()}>
            ▣ From gallery
          </button>
        </div>
        <span>Supports PNG, JPG, WebP, DICOM · max size 15 MB</span>

        <input
          ref={uploadRef}
          className="sr-only"
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.dcm,image/jpeg,image/png,image/webp,application/dicom"
          onChange={pick}
        />
        <input
          ref={cameraRef}
          className="sr-only"
          type="file"
          accept="image/*"
          capture="environment"
          onChange={pick}
        />
        <input
          ref={galleryRef}
          className="sr-only"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={pick}
        />
      </div>

      {file && (
        <div className="file-card">
          {preview ? (
            <img src={preview} alt="Local preview of selected X-ray" />
          ) : (
            <div className="dicom-preview">DICOM</div>
          )}
          <div>
            <strong>{file.name}</strong>
            <span>{file.type} · {(file.size / 1024 / 1024).toFixed(2)} MB</span>
          </div>
          <button className="button button-primary" type="button" disabled={state === "uploading"} onClick={() => void upload()}>
            {state === "uploading" ? "Uploading…" : state === "uploaded" ? "Upload again" : "Upload X-ray"}
          </button>
        </div>
      )}
      {error && <div className="error-panel" role="alert">{error}</div>}
    </section>
  );
}
