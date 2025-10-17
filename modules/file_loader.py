def detect_file_type(file_path):
    # Identify file format if extension has been altered
    with open(file_path, 'rb') as f:
        header = f.read(10)

    # Splits . if filename contains more than the extension only
    ext = file_path.lower().split('.')[-1]

    # docx office open XML files are ZIP-based and start with pk
    if ext == "docx" and header.startswith(b'PK'):
        return "docx"
    # PDF start with %PDF
    elif ext == "pdf" and header.startswith(b'%PDF'):
        return "pdf"
    # JPG start with binary marker FF D
    elif ext in ["jpg", "jpeg"] and header[0:2] == b'\xFF\xD8':
        return "jpg"
    # PNG start with 89 50 4E 47
    elif ext == "png" and header.startswith(b'\x89PNG'):
        return "png"  
    else:
        return "unknown"
    
    # Markers extracted from https://stackoverflow.com/questions/78135164/whats-the-meaning-of-the-characters-in-the-jpeg-binary-byte-stream-opened-in-py#:~:text=A%20valid%20JPEG%20file%20must,will%20have%20a%20thumbnail%20embedded.