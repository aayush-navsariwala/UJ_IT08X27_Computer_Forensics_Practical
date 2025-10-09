def detect_file_type(file_path):
    with open(file_path, 'rb') as f:
        header = f.read(10)

    if file_path.endswith(".docx") and header.startswith(b'PK'):
        return "docx"
    elif file_path.endswith(".pdf") and header.startswith(b'%PDF'):
        return "pdf"
    elif file_path.endswith(".jpg") and header[0:2] == b'\xFF\xD8':
        return "jpg"
    elif file_path.endswith(".png") and header.startswith(b'\x89PNG'):
        return "jpg"  
    else:
        return "unknown"
    