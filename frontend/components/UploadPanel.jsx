import { useState } from "react";

export default function UploadPanel() {
  const [fileName, setFileName] = useState("");

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    setFileName(file ? file.name : "");
  };

  return (
    <section className="panel card-surface">
      <div className="panel-head">
        <h3>Dataset Intake</h3>
        <span className="panel-kicker">Secure</span>
      </div>

      <label className="file-picker">
        <span>{fileName ? "Replace dataset file" : "Select dataset file"}</span>
        <input type="file" onChange={handleFileChange} />
      </label>

      <p className="muted-text">
        {fileName
          ? `Selected file: ${fileName}`
          : "CSV, JSONL, or TXT files are accepted for local training."}
      </p>
    </section>
  );
}
