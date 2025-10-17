import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.file_loader import detect_file_type
from modules import metadata_docx, metadata_pdf, metadata_jpg
from modules.anomaly_checker import check_anomalies
from modules.report_generator import generate_report

class ForensicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NavDocTrail")

        self.root.geometry("700x500")

        self.upload_btn = tk.Button(root, text="Select Document", command=self.upload_file, font=("Arial", 12))
        self.upload_btn.pack(pady=10)

        self.output_area = scrolledtext.ScrolledText(root, width=85, height=25, font=("Consolas", 10))
        self.output_area.pack(pady=10)

    def upload_file(self):
        filepath = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[
                ("Supported Files", "*.docx *.pdf *.jpg *.jpeg *.png"),
                ("All Files", "*.*")
            ]
        )

        if not filepath:
            return

        self.output_area.delete("1.0", tk.END)
        self.output_area.insert(tk.END, f"🔍 Scanning file: {filepath}\n\n")

        file_type = detect_file_type(filepath)

        if file_type == "docx":
            metadata = metadata_docx.extract_metadata(filepath)
        elif file_type == "pdf":
            metadata = metadata_pdf.extract_metadata(filepath)
        elif file_type == "jpg":
            metadata = metadata_jpg.extract_metadata(filepath)
        else:
            messagebox.showerror("Unsupported Format", "This file type is not supported.")
            return

        anomalies = check_anomalies(metadata)

        self.output_area.insert(tk.END, "Extracted Metadata:\n")
        for key, value in metadata.items():
            self.output_area.insert(tk.END, f"  - {key.capitalize()}: {value}\n")

        self.output_area.insert(tk.END, "\nDetected Anomalies:\n")
        if anomalies:
            for issue in anomalies:
                self.output_area.insert(tk.END, f"  - {issue}\n")
        else:
            self.output_area.insert(tk.END, "  - None detected.\n")

        risk_score = min(len(anomalies) * 20, 100)
        self.output_area.insert(tk.END, f"\nRisk Score: {risk_score}/100\n")
        if risk_score >= 80:
            self.output_area.insert(tk.END, "→ High likelihood of tampering or metadata manipulation.\n")
        elif risk_score >= 40:
            self.output_area.insert(tk.END, "→ Moderate likelihood. Recommend further investigation.\n")
        else:
            self.output_area.insert(tk.END, "→ Low likelihood of tampering.\n")

        generate_report(filepath, metadata, anomalies)

        self.output_area.insert(tk.END, "\n📁 Full report saved in the /reports folder.\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = ForensicApp(root)
    root.mainloop()