def extract_metadata(file_path):
    metadata = {
        "file_type": "pdf",
        "author": "Unknown",
        "created": "Unknown",
        "modified": "Unknown",
        "producer": "Unknown",
        "title": "Unknown",
        "created_by": "Unknown",
        "modified_by": "Unknown"
    }

    try:
        with open(file_path, 'rb') as f:
            content = f.read().decode('latin-1', errors='ignore')

        fields = ["/Author", "/Title", "/Producer", "/CreationDate", "/ModDate"]
        for field in fields:
            if field in content:
                start = content.find(field)
                end = content.find("\n", start)
                line = content[start:end]
                value = line.split("(")[-1].split(")")[0].strip()

                if "/Author" in field:
                    metadata["author"] = value
                elif "/Title" in field:
                    metadata["title"] = value
                elif "/Producer" in field:
                    metadata["producer"] = value
                elif "/CreationDate" in field:
                    metadata["created"] = value
                elif "/ModDate" in field:
                    metadata["modified"] = value

        if metadata["producer"] != "Unknown":
            metadata["created_by"] = metadata["producer"]
            metadata["modified_by"] = metadata["producer"]

            if "word" in metadata["producer"].lower():
                metadata["created_by"] = "Microsoft Word"
            elif "acrobat" in metadata["producer"].lower():
                metadata["modified_by"] = "Adobe Acrobat"
            elif "libreoffice" in metadata["producer"].lower():
                metadata["modified_by"] = "LibreOffice PDF Exporter"

    except Exception as e:
        print(f"[Error] Could not extract PDF metadata: {e}")

    return metadata