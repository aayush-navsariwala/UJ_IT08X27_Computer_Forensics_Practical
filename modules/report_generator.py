import os
from datetime import datetime

def generate_report(file_path, metadata, anomalies):
    filename = os.path.basename(file_path)
    report_lines = []

    print("\n=== METADATA REPORT ===")
    report_lines.append(f"File: {filename}")
    report_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    report_lines.append("📄 Extracted Metadata:")
    for key, value in metadata.items():
        report_lines.append(f"  - {key.capitalize()}: {value}")
    report_lines.append("")

    report_lines.append("⚠️ Detected Anomalies:")
    if anomalies:
        for anomaly in anomalies:
            report_lines.append(f"  - {anomaly}")
    else:
        report_lines.append("  - None detected.")
    report_lines.append("")

    risk_score = min(len(anomalies) * 20, 100)
    report_lines.append(f"🔒 Risk Score: {risk_score}/100")
    if risk_score >= 80:
        report_lines.append("→ High likelihood of tampering or metadata manipulation.")
    elif risk_score >= 40:
        report_lines.append("→ Moderate likelihood. Recommend further investigation.")
    else:
        report_lines.append("→ Low likelihood of tampering.")

    report_output = "\n".join(report_lines)
    print(report_output)

    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"reports/forensic_report_{os.path.splitext(filename)[0]}_{timestamp}.txt"

    with open(report_file, 'w') as f:
        f.write(report_output)

    print(f"\n📁 Report saved to: {report_file}")