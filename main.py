import os
from modules.file_loader import detect_file_type
from modules import metadata_docx, metadata_pdf, metadata_jpg, metadata_png
from modules.anomaly_checker import check_anomalies
from modules.report_generator import generate_report

def main():
    print("=== Digital Metadata Forensics Tool ===")
    file_path = input("Enter the path to the file you want to scan: ")

    if not os.path.exists(file_path):
        print("Error: File not found.")
        return

    file_type = detect_file_type(file_path)

    if file_type == "docx":
        metadata = metadata_docx.extract_metadata(file_path)
    elif file_type == "pdf":
        metadata = metadata_pdf.extract_metadata(file_path)
    elif file_type == "jpg":
        metadata = metadata_jpg.extract_metadata(file_path)
    elif file_type == "png":
        metadata = metadata_png.extract_metadata(file_path)
    else:
        print("Unsupported file type.")
        return

    anomalies = check_anomalies(metadata)
    generate_report(file_path, metadata, anomalies)

if __name__ == "__main__":
    main()
    