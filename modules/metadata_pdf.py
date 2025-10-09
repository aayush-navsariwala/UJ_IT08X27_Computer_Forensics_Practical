def extract_metadata(file_path):
    metadata = {
        "file_type": "pdf",
        "author": "Unknown",
        "created": "Unknown",
        "modified": "Unknown",
        "producer": "Unknown",
        "title": "Unknown"
    }

    try:
        with open(file_path, 'rb') as f:
            content = f.read().decode('latin-1', errors='ignore')  

        if "/Author" in content:
            start = content.find("/Author")
            end = content.find("\n", start)
            metadata["author"] = content[start:end].split("(")[-1].split(")")[0].strip()

        if "/Title" in content:
            start = content.find("/Title")
            end = content.find("\n", start)
            metadata["title"] = content[start:end].split("(")[-1].split(")")[0].strip()

        if "/Producer" in content:
            start = content.find("/Producer")
            end = content.find("\n", start)
            metadata["producer"] = content[start:end].split("(")[-1].split(")")[0].strip()

        if "/CreationDate" in content:
            start = content.find("/CreationDate")
            end = content.find("\n", start)
            metadata["created"] = content[start:end].split("(")[-1].split(")")[0].strip()

        if "/ModDate" in content:
            start = content.find("/ModDate")
            end = content.find("\n", start)
            metadata["modified"] = content[start:end].split("(")[-1].split(")")[0].strip()

    except Exception as e:
        print(f"[Error] Could not extract PDF metadata: {e}")

    return metadata