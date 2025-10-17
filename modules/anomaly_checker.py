from datetime import datetime

def check_anomalies(metadata):
    # List to store detected anomalies
    anomalies = []

    # Check for required fields
    required_fields = ["created", "modified", "author", "application", "datetime"]
    for field in required_fields:
        # If field exists but is empty, unknown or none
        if field in metadata and metadata[field] in ["", "Unknown", None]:
            anomalies.append(f"Missing or empty field: {field}")

    # Validate timestamp order
    if "created" in metadata and "modified" in metadata:
        try:
            created = extract_datetime(metadata["created"])
            modified = extract_datetime(metadata["modified"])
            # If both timestamps are found
            if created and modified and modified < created:
                anomalies.append("Modified date is earlier than creation date.")
        except:
            pass

    # Same timestamps may suggest metadata overwriting 
    if "created" in metadata and "modified" in metadata:
        if metadata["created"] == metadata["modified"]:
            anomalies.append("Created and modified timestamps are identical. Possible timestamp overwrite.")

    # Check for inconsistencies in application and producer of file 
    if "application" in metadata and "producer" in metadata:
        app = metadata["application"].lower()
        prod = metadata["producer"].lower()
        if app != "unknown" and prod != "unknown" and app not in prod and prod not in app:
            anomalies.append("Mismatch between editing software and producer.")

    return anomalies

# Find datetime format in metadata
def extract_datetime(raw):
    try:
        if raw.startswith("D:"):
            return datetime.strptime(raw[2:16], "%Y%m%d%H%M%S")
        elif "T" in raw:
            return datetime.strptime(raw.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        elif ":" in raw and " " in raw:
            return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
    except:
        return None