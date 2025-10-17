import os
import sys

# Project root (parent of this file's dir)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)  # Ensure local modules import

from modules.metadata_jpg import extract_metadata  # JPEG EXIF extractor

# Supported JPEG extensions (case-sensitive list for speed)
SUPPORTED_EXTS = {".jpg", ".jpeg", ".JPG", ".JPEG"}

def scan_folder(folder):
    files = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path) and os.path.splitext(name)[1] in SUPPORTED_EXTS:
            files.append(path)
    return sorted(files)

def summarize_flags(meta: dict):
    has_any_exif = any(
        meta.get(k, "Unknown") != "Unknown"
        for k in ("make", "camera_model", "software", "datetime", "datetime_digitized", "exif_version")
    )
    gps_present = (meta.get("gps_latitude") not in (None, "Unknown") and
                   meta.get("gps_longitude") not in (None, "Unknown"))
    stripped_like = (
        meta.get("created_by") == "Unknown (Possibly Metadata-Stripped Image)" and
        meta.get("modified_by") == "Unknown (Possibly Metadata-Stripped Image)"
    )
    missing_time = meta.get("datetime", "Unknown") == "Unknown"
    size_known = (str(meta.get("width")) not in ("None", "Unknown")
                  and str(meta.get("height")) not in ("None", "Unknown"))

    return {
        "has_any_exif": has_any_exif,
        "gps_present": gps_present,
        "stripped_like": stripped_like,
        "missing_time": missing_time,
        "size_known": size_known,
    }

def print_report(path, meta, flags):
    print("=" * 80)
    print(f"File: {path}")
    print("- Extracted Metadata -")
    ordered_keys = [
        "make", "camera_model", "software",
        "datetime", "datetime_digitized", "exif_version",
        "width", "height",
        "gps_latitude", "gps_longitude",
        "created_by", "modified_by",
        "title", "author", "description"
    ]
    for k in ordered_keys:
        if k in meta:
            print(f"  {k:18s}: {meta[k]}")

    print("- Quick Checks -")
    print(f"  Any EXIF present     : {flags['has_any_exif']}")
    print(f"  GPS present          : {flags['gps_present']}")
    print(f"  Looks stripped       : {flags['stripped_like']}")
    print(f"  Missing capture time : {flags['missing_time']}")
    print(f"  Dimensions known     : {flags['size_known']}")

    # Optional notes based on flags
    notes = []
    if flags["stripped_like"]:
        notes.append("Possible metadata-stripped image (e.g., social media or messaging app).")
    if not flags["size_known"]:
        notes.append("Image dimensions not found in EXIF (may still be derivable from JPEG SOF).")
    if flags["missing_time"]:
        notes.append("No DateTimeOriginal/DateTime found. Some phones/apps omit this.")
    if notes:
        print("- Notes -")
        for n in notes:
            print(f"  - {n}")

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT_ROOT, "test_documents")
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        sys.exit(1)

    files = scan_folder(folder)
    if not files:
        print(f"No JPEG files found in: {folder}")
        sys.exit(0)

    print(f"Scanning {len(files)} file(s) in: {folder}\n")

    for path in files:
        try:
            meta = extract_metadata(path)  # Parse EXIF/fields
        except Exception as e:
            print("=" * 80)
            print(f"File: {path}")
            print(f"[ERROR] extract_metadata raised an exception: {e}")
            continue

        flags = summarize_flags(meta)     # Quick booleans
        print_report(path, meta, flags)   # Human-readable output

    print("\nDone.")

if __name__ == "__main__":
    main()
