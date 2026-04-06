import { useState } from "react";

export default function UploadPanel() {
  const [fileName, setFileName] = useState("");

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    setFileName(file ? file.name : "");
  };

  return (
    <section className="card">
      <h3>Upload Dataset</h3>
      <input type="file" onChange={handleFileChange} />
      <p>{fileName ? `Selected: ${fileName}` : "No file selected"}</p>
    </section>
  );
}
