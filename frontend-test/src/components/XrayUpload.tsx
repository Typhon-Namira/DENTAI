import { useEffect, useRef, useState, type DragEvent } from "react";
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
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [state, setState] = useState<"idle" | "selected" | "uploading" | "uploaded" | "error">("idle");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

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
      const xray = await api.uploadXray(patientId, file);
      setState("uploaded");
      await onUploaded(xray);
    } catch (reason) {
      setState("error");
      setError(errorMessage(reason));
    }
  }

  return (
    <section className="card upload-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">New study</p>
          <h3>Upload an X-ray</h3>
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
        <span className="upload-icon" aria-hidden="true">↑</span>
        <strong>Drop an OPG image here</strong>
        <span>JPEG, PNG, WebP, or DICOM · up to 15 MB by default</span>
        <button className="button button-secondary" type="button" onClick={() => inputRef.current?.click()}>
          Choose file
        </button>
        <input
          ref={inputRef}
          className="sr-only"
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.dcm,image/jpeg,image/png,image/webp,application/dicom"
          onChange={(event) => {
            const candidate = event.target.files?.item(0);
            if (candidate) select(candidate);
            event.currentTarget.value = "";
          }}
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
