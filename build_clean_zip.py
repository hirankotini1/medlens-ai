"""
MedLens AI — Clean ZIP Package Builder for Development & Sharing
Creates a clean, robust, cross-platform zip archive tailored for development on any machine.

Excludes:
- .git repository
- .gradle and build artifacts (Android compilation cache)
- __pycache__ and *.pyc files
- local.properties (allows Android Studio on friend's PC to auto-detect their own SDK path)
- nested .zip files
- .idea and IDE temporary files
- obsolete database backups in backups/ (keeps active live pathology.db)
"""

import os
import zipfile
import sys

def build_zip():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_filename = os.path.join(base_dir, 'MedLens_AI_Shareable.zip')

    if os.path.exists(zip_filename):
        try:
            os.remove(zip_filename)
        except Exception:
            pass

    EXCLUDE_DIRS = {'.git', '__pycache__', '.pytest_cache', '.gradle', 'build', '.idea', 'backups'}
    EXCLUDE_EXTS = {'.pyc', '.pyo', '.pyd'}
    EXCLUDE_FILES = {'MedLens_AI_Submission.zip', 'MedLens_AI_Shareable.zip', 'local.properties'}

    print(f"[1/3] Packaging MedLens AI project from: {base_dir}")
    added_count = 0

    with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(base_dir):
            # Exclude unwanted directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                if file in EXCLUDE_FILES or any(file.endswith(ext) for ext in EXCLUDE_EXTS):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir)

                # Normalized forward-slash path within the zip
                archive_name = os.path.join('MedLens_AI', rel_path).replace('\\', '/')
                zf.write(full_path, archive_name)
                added_count += 1

    size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
    print(f"[2/3] Packaged {added_count} development files ({size_mb:.2f} MB)")

    print("[3/3] Verifying zip integrity with full decompression test...")
    with zipfile.ZipFile(zip_filename, 'r') as zf:
        corrupted = zf.testzip()
        if corrupted:
            print(f"ERROR: Corrupted entry found: {corrupted}")
            sys.exit(1)
        else:
            print("SUCCESS: Zip archive passed all integrity checks (0 errors).")

    print(f"\n=======================================================")
    print(f"FINAL SHAREABLE ZIP CREATED SUCCESSFULLY:")
    print(f"{zip_filename}")
    print(f"Size: {size_mb:.2f} MB ({added_count} files)")
    print(f"=======================================================")

if __name__ == '__main__':
    build_zip()
