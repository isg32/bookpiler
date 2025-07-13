import os
import re
from PyPDF2 import PdfMerger
import fitz  # PyMuPDF

# --- Configuration ---
DATA_DIR = "./data"
TEMP_DIR = "./temp"
GENERATED_DIR = "./generated"

# --- Create directories if they don't exist ---
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

# --- 1. Parse Files and Pair Them ---
# Structure: { (class, subject, chapter): {'questions': 'path', 'explanations': 'path'} }
file_pairs = {}

print("Scanning data directory for PDF files...")
for root, _, files in os.walk(DATA_DIR):
    for file_name in files:
        if file_name.endswith(".pdf"):
            # This regex allows for optional 'st', 'nd', 'rd', 'th' after the class number
            match = re.match(r"Class (\d+)(?:st|nd|rd|th)? - (.*?) - (.*?) - (Questions|Explanations)\.pdf", file_name)
            if match:
                class_num = match.group(1)
                subject = match.group(2).strip()
                chapter_name = match.group(3).strip()
                file_type = match.group(4).lower()

                key = (class_num, subject, chapter_name)
                if key not in file_pairs:
                    file_pairs[key] = {}
                file_pairs[key][file_type] = os.path.join(root, file_name)
            else:
                print(f"Skipping unrecognized file: {file_name}")

# --- 2. Merge Pairs into Temporary PDFs and Extract First Line ---
# Structure: [(sort_key, path_to_merged_pdf, class_num, subject), ...]
temp_merged_pdfs_info = []

print("\nMerging question/explanation pairs and extracting first lines...")
for (class_num, subject, chapter_name), paths in file_pairs.items():
    questions_pdf_path = paths.get('questions')
    explanations_pdf_path = paths.get('explanations')

    if not questions_pdf_path or not explanations_pdf_path:
        print(f"Skipping incomplete pair for {class_num} - {subject} - {chapter_name}: Missing {'questions' if not questions_pdf_path else 'explanations'} PDF.")
        continue

    output_temp_pdf_name = f"Class {class_num} - {subject} - {chapter_name} - merged.pdf"
    output_temp_pdf_path = os.path.join(TEMP_DIR, output_temp_pdf_name)

    merger = PdfMerger()
    try:
        merger.append(questions_pdf_path)
        merger.append(explanations_pdf_path)

        with open(output_temp_pdf_path, "wb") as f:
            merger.write(f)
        print(f"  Merged '{os.path.basename(questions_pdf_path)}' and '{os.path.basename(explanations_pdf_path)}' into '{os.path.basename(output_temp_pdf_path)}'")

        # --- Extract the first line using PyMuPDF ---
        first_line_content = ""
        try:
            with fitz.open(output_temp_pdf_path) as doc:
                if doc.page_count > 0:
                    page = doc.load_page(0)
                    text_blocks = page.get_text("blocks")
                    if text_blocks:
                        # Sort blocks by their y0 coordinate (top position) to get them in reading order
                        sorted_blocks = sorted(text_blocks, key=lambda block: block[1])
                        for block in sorted_blocks:
                            text = block[4].strip()
                            if text:
                                # Take the first non-empty line of the first significant text block
                                first_line_content = text.split('\n')[0].strip()
                                break
            if not first_line_content:
                print(f"    Warning: Could not extract first line from {os.path.basename(output_temp_pdf_path)}. Using chapter name for sorting.")
                first_line_content = chapter_name # Fallback
            else:
                print(f"    Extracted first line: '{first_line_content}'")

        except Exception as e:
            print(f"    Error extracting first line from {os.path.basename(output_temp_pdf_path)}: {e}. Using chapter name for sorting.")
            first_line_content = chapter_name # Fallback

        temp_merged_pdfs_info.append((first_line_content, output_temp_pdf_path, class_num, subject))

    except Exception as e:
        print(f"  Error merging PDFs for {class_num} - {subject} - {chapter_name}: {e}")
    finally:
        merger.close()

# --- 3. Group and Sort Merged PDFs for Final Compilation ---
# Structure: { (class, subject): [(sort_key, path_to_merged_pdf), ...] }
compiled_books_map = {}

for sort_key, pdf_path, class_num, subject in temp_merged_pdfs_info:
    book_key = (class_num, subject)
    if book_key not in compiled_books_map:
        compiled_books_map[book_key] = []
    compiled_books_map[book_key].append((sort_key, pdf_path))

print("\nSorting merged PDFs for final compilation...")
for (class_num, subject), pdf_list in compiled_books_map.items():
    # Define a custom sort function
    def custom_sort(item):
        key = item[0] # This is the first line content
        # Make the key lowercase and remove extra spaces for consistent matching
        normalized_key = re.sub(r'\s+', ' ', key.lower()).strip()

        # Regex to find chapter number:
        # - (?:chapter|ch|unit|lesson)\s* could match "chapter", "ch", "unit", "lesson" (case-insensitive)
        # - (\d+) captures one or more digits (the chapter number)
        # - (?:[.\s-]+)? allows for optional dot, space, or hyphen after the number (e.g., "Chapter 1." or "Ch 2 -")
        chapter_match = re.search(r"(?:chapter|ch|unit|lesson)\s*(\d+)(?:[.\s-]+)?", normalized_key)
        
        if chapter_match:
            try:
                chapter_number = int(chapter_match.group(1))
                return (0, chapter_number) # Sort by chapter number (priority 0)
            except ValueError:
                # Fallback if the extracted number isn't a valid integer
                pass # Continue to the next sorting rule

        # If no numerical chapter found, sort by normalized string (alphabetical, case-insensitive)
        return (1, normalized_key) # Sort by name (priority 1), case-insensitive


    pdf_list.sort(key=custom_sort)
    print(f"  Sorted chapters for Class {class_num} - {subject}")
    # Optional: Print sorted order for debugging
    # for s_key, p_path in pdf_list:
    #     print(f"    - '{s_key}' from {os.path.basename(p_path)}")


# --- 4. Final Compilation into Book-Compiled.pdf ---
print("\nCompiling final books...")
for (class_num, subject), sorted_pdf_info in compiled_books_map.items():
    final_output_pdf_name = f"Class {class_num} - {subject} - Book-Compiled.pdf"
    final_output_pdf_path = os.path.join(GENERATED_DIR, final_output_pdf_name)

    final_merger = PdfMerger()
    pdfs_to_compile = [item[1] for item in sorted_pdf_info]

    try:
        if pdfs_to_compile: # Ensure there are PDFs to merge
            for pdf_path in pdfs_to_compile:
                final_merger.append(pdf_path)

            with open(final_output_pdf_path, "wb") as f:
                final_merger.write(f)
            print(f"  Successfully compiled '{final_output_pdf_path}'")
        else:
            print(f"  No PDFs to compile for Class {class_num} - {subject}.")
    except Exception as e:
        print(f"  Error compiling final book '{final_output_pdf_path}': {e}")
    finally:
        final_merger.close()

# --- Cleanup Temporary Files ---
print("\nCleaning up temporary files...")
try:
    if os.path.exists(TEMP_DIR):
        for file_name in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(TEMP_DIR) # Remove the directory if empty
        print("Temporary directory and files removed.")
    else:
        print("Temporary directory not found, no cleanup needed.")
except OSError as e:
    print(f"Error during temporary file cleanup: {e}")

print("\nProcess complete! Check the 'generated' directory for your compiled books.")