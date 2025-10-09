def detect_file_type(file_path):
    with open(file_path, 'rb') as f:
        header = f.read(10)

    ext = file_path.lower().split('.')[-1]

    if ext == "docx" and header.startswith(b'PK'):
        return "docx"
    elif ext == "pdf" and header.startswith(b'%PDF'):
        return "pdf"
    elif ext in ["jpg", "jpeg"] and header[0:2] == b'\xFF\xD8':
        return "jpg"
    elif ext == "png" and header.startswith(b'\x89PNG'):
        return "jpg"  
    else:
        return "unknown"
    