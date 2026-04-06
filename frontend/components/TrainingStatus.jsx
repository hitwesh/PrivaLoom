const statusItems = [
  "Model initialized",
  "GPU check complete",
  "Awaiting training data",
];

export default function TrainingStatus() {
  return (
    <section className="card">
      <h3>Training Status</h3>
      <ul>
        {statusItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
