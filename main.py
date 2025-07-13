import os
import re
from PyPDF2 import PdfMerger
import fitz # PyMuPDF
from datetime import datetime

# --- Configuration ---
DATA_DIR = "./data"
TEMP_DIR = "./temp"
GENERATED_DIR = "./generated"
INDEX_BG_PATH = "./assets/index.png" # Path to your index page background image
WATERMARK_PATH = "./assets/amjlogo.jpg" # Path to your watermark image
LOGO_PATH = "./assets/logo.png" # Path to your header logo image

# --- Create directories if they don't exist ---
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOGO_PATH), exist_ok=True)
os.makedirs(os.path.dirname(INDEX_BG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(WATERMARK_PATH), exist_ok=True)

# --- Function to generate an index page PDF ---
def generate_index_page(subject, class_num, output_path):
    """
    Generates a single-page PDF with an index background, subject name, and class.
    """
    doc = fitz.open()
    try:
        if not os.path.exists(INDEX_BG_PATH):
            print(f"  Warning: Index background image not found at '{INDEX_BG_PATH}'. Generating blank index page.")
            page = doc.new_page(width=595, height=842) # A4 size default if no image
        else:
            pix = fitz.Pixmap(INDEX_BG_PATH)
            page = doc.new_page(width=595, height=842)
            page.insert_image(page.rect, pixmap=pix)
            pix = None # Release pixmap

        # Add Subject Name in the middle
        subject_text = subject.upper()
        estimated_font_size = 90 # Example size, adjust as needed
        
        # Calculate optimal font size to fit the subject name within a reasonable width
        max_width = page.rect.width * 0.8 # 80% of page width
        while fitz.get_text_length(subject_text, fontname="Helvetica-Bold", fontsize=estimated_font_size) > max_width and estimated_font_size > 10:
            estimated_font_size -= 1

        text_bbox_y_center = page.rect.height / 2.6
        # Using insert_textbox for better control over alignment and wrapping if text is long
        page.insert_textbox(
            (page.rect.width * 0.1, text_bbox_y_center - estimated_font_size, page.rect.width * 0.9, text_bbox_y_center + estimated_font_size),
            subject_text,
            fontname="Helvetica-Bold",
            fontsize=estimated_font_size,
            color=(0.9333333333333333, 0.6392156862745098, 0.2549019607843137), # Yellow color (RGB)
            align=fitz.TEXT_ALIGN_CENTER # 'align' is valid for insert_textbox
        )

        # Add Class at the bottom
        class_text = f"{class_num}"
        class_font_size = 50 # Example size
        
        # Manually calculate x for centering insert_text as 'align' is not supported
        text_length = fitz.get_text_length(class_text, fontname="Helvetica", fontsize=class_font_size)
        x_centered = (page.rect.width - text_length) / 1.55
        
        page.insert_text(
            (x_centered, page.rect.height - 38), # Position near bottom center
            class_text,
            fontname="Helvetica",
            fontsize=class_font_size,
            color=(1, 1, 1) # Black color
        )
        
        doc.save(output_path)
        print(f"  Generated index page for '{subject}' (Class {class_num}) at '{output_path}'.")
    except Exception as e:
        print(f"  Error generating index page: {e}")
    finally:
        if doc:
            doc.close()


# --- Function to apply all PDF overlays (Header/Footer/Watermark) ---
def apply_pdf_overlays(pdf_path, output_pdf_path, class_num, subject, is_index_page=False):
    """
    Applies header (logo, class/subject/year), a fully opaque footer with page numbers,
    and a faded watermark to each page of a PDF.
    The is_index_page flag prevents headers/footers on the index page.
    """
    doc = None
    output_doc = None
    watermark_pix = None
    logo_pix = None
    try:
        doc = fitz.open(pdf_path)
        output_doc = fitz.open() # Create a new PDF for output

        current_year = datetime.now().year
        total_pages = doc.page_count # Get total page count

        # Load watermark image
        if os.path.exists(WATERMARK_PATH):
            try:
                watermark_pix_orig = fitz.Pixmap(WATERMARK_PATH)
                # Convert to RGBA if not already (for alpha manipulation)
                if watermark_pix_orig.n < 4:
                    watermark_pix = fitz.Pixmap(fitz.csRGBA, watermark_pix_orig)
                else:
                    watermark_pix = fitz.Pixmap(watermark_pix_orig)
                
                # Apply transparency directly to the pixmap's alpha channel
                # Desired opacity (0.0 to 1.0)
                desired_alpha = 0.15 
                for i in range(watermark_pix.height):
                    for j in range(watermark_pix.width):
                        # Get RGBA pixel (last element is alpha)
                        r, g, b, a = watermark_pix.pixel(j, i)
                        # Set new alpha value
                        watermark_pix.set_pixel(j, i, (r, g, b, int(a * desired_alpha)))

                print(f"  Loaded and prepared faded watermark from: {WATERMARK_PATH}")
                watermark_pix_orig = None # Release original
            except Exception as e:
                print(f"  Warning: Could not load or process watermark image '{WATERMARK_PATH}': {e}")
                watermark_pix = None
        else:
            print(f"  Warning: Watermark file not found at '{WATERMARK_PATH}'. No watermark will be applied.")

        # Load header logo if it exists
        if os.path.exists(LOGO_PATH):
            try:
                logo_pix = fitz.Pixmap(LOGO_PATH)
            except Exception as e:
                print(f"  Warning: Could not load header logo image '{LOGO_PATH}': {e}")
                logo_pix = None
        else:
            print(f"  Warning: Header logo file not found at '{LOGO_PATH}'. Header will not include logo.")


        for i, page in enumerate(doc):
            # Create a new blank page to draw on, preserving original content
            new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # Draw original page content onto the new page
            # Set overlay=False here to ensure original content is drawn first.
            new_page.show_pdf_page(page.rect, doc, page.number, overlay=False)


            # --- Apply Faded Watermark ---
            if watermark_pix:
                wm_aspect = watermark_pix.width / watermark_pix.height
                page_aspect = new_page.rect.width / new_page.rect.height

                # Calculate dimensions to fit the watermark image centered on the page while maintaining aspect ratio
                if wm_aspect > page_aspect: # Watermark is wider relative to height than page
                    display_width = new_page.rect.width
                    display_height = display_width / wm_aspect
                else: # Watermark is taller relative to width than page
                    display_height = new_page.rect.height
                    display_width = display_height * wm_aspect
                
                # Center the watermark
                wm_x = (new_page.rect.width - display_width) / 2
                wm_y = (new_page.rect.height - display_height) / 2
                
                # Insert the modified pixmap. 'overlay=False' ensures it's behind text.
                new_page.insert_image(
                    fitz.Rect(wm_x, wm_y, wm_x + display_width, wm_y + display_height),
                    pixmap=watermark_pix,
                    overlay=False # Still important to draw behind existing content
                )

            # --- Apply Header and Footer ONLY if NOT the index page ---
            if not is_index_page:
                # Define strip dimensions
                header_strip_height = 30 
                footer_strip_height = 60 # Doubled footer height (original was 30)
                
                # Header rectangle (at the top)
                header_rect = fitz.Rect(0, 0, new_page.rect.width, header_strip_height)
                new_page.draw_rect(header_rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9)) # Light grey background

                # Footer rectangle (at the bottom)
                footer_rect = fitz.Rect(0, new_page.rect.height - footer_strip_height, new_page.rect.width, new_page.rect.height)
                # Make footer fully opaque (fill color with alpha=1.0)
                new_page.draw_rect(footer_rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9), fill_opacity=1.0) 

                # --- Header Content ---
                header_text = f"Class {class_num} - {subject} - {current_year}"
                text_x = 10 # Starting X position for text
                logo_width = 0 # To track logo width for text placement

                if logo_pix:
                    # Scale logo to fit strip height, maintaining aspect ratio
                    logo_display_height = header_strip_height - 10 # Some padding
                    logo_display_width = (logo_pix.width / logo_pix.height) * logo_display_height
                    
                    # Ensure logo is not too wide
                    if logo_display_width > new_page.rect.width / 4: # Limit logo width to 1/4 of page
                        logo_display_width = new_page.rect.width / 4
                        logo_display_height = (logo_pix.height / logo_pix.width) * logo_display_width

                    logo_rect = fitz.Rect(5, 5, 5 + logo_display_width, 5 + logo_display_height)
                    new_page.insert_image(logo_rect, pixmap=logo_pix)
                    logo_width = logo_rect.width + 10 # Add some padding after logo
                    text_x = logo_width # Start text after logo

                new_page.insert_text(
                    (text_x, 20), # Y position within header strip
                    header_text,
                    fontname="Helvetica-Bold",
                    fontsize=10,
                    color=(0, 0, 0) # Black text
                )

                # --- Footer Content (Page Numbers) ---
                # Page numbers will be centered
                page_number_text = f"Page {i + 1} of {total_pages}"
                page_number_font_size = 10 # Standard font size for page numbers
                page_number_color = (0, 0, 0) # Black text

                # Calculate position for centered text within the footer
                pn_text_length = fitz.get_text_length(page_number_text, fontname="Helvetica", fontsize=page_number_font_size)
                pn_x_centered = (new_page.rect.width - pn_text_length) / 2
                pn_y = new_page.rect.height - (footer_strip_height / 2) + (page_number_font_size / 2) - 3 # Center vertically

                new_page.insert_text(
                    (pn_x_centered, pn_y),
                    page_number_text,
                    fontname="Helvetica", # Using standard Helvetica for page numbers
                    fontsize=page_number_font_size,
                    color=page_number_color
                )

        output_doc.save(output_pdf_path)
        print(f"  Successfully applied overlays (watermark, header strip, fully opaque footer with page numbers) to '{os.path.basename(pdf_path)}' and saved to '{os.path.basename(output_pdf_path)}'.")
    except Exception as e:
        print(f"  Error applying overlays to '{os.path.basename(pdf_path)}': {e}")
    finally:
        if doc:
            doc.close()
        if output_doc:
            output_doc.close()
        # Release pixmaps explicitly
        if watermark_pix:
            watermark_pix = None
        if logo_pix:
            logo_pix = None


# --- 1. Parse Files and Pair Them ---
# Structure: { (class, subject, chapter): {'questions': 'path', 'explanations': 'path'} }
file_pairs = {}

print("Scanning data directory for PDF files...")
for root, _, files in os.walk(DATA_DIR):
    for file_name in files:
        if file_name.endswith(".pdf"):
            # This regex allows for optional 'st', 'nd', 'rd', 'th' after the class number
            # Added (?:\s*)? before \.pdf to handle optional spaces before extension
            match = re.match(r"Class (\d+)(?:st|nd|rd|th)? - (.*?) - (.*?) - (Questions|Explanations)(?:\s*)?\.pdf", file_name)
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
    doc_temp_pdf = None # Initialize for PyMuPDF document
    try:
        merger.append(questions_pdf_path)
        merger.append(explanations_pdf_path)

        with open(output_temp_pdf_path, "wb") as f:
            merger.write(f)
        print(f"  Merged '{os.path.basename(questions_pdf_path)}' and '{os.path.basename(explanations_pdf_path)}' into '{os.path.basename(output_temp_pdf_path)}'")

        # --- Extract the first line using PyMuPDF ---
        first_line_content = ""
        try:
            doc_temp_pdf = fitz.open(output_temp_pdf_path)
            if doc_temp_pdf.page_count > 0:
                page = doc_temp_pdf.load_page(0)
                text_blocks = page.get_text("blocks")
                if text_blocks:
                    sorted_blocks = sorted(text_blocks, key=lambda block: block[1])
                    for block in sorted_blocks:
                        text = block[4].strip()
                        if text:
                            first_line_content = text.split('\n')[0].strip()
                            break
            if not first_line_content:
                print(f"    Warning: Could not extract first line from {os.path.basename(output_temp_pdf_path)}. Using chapter name for sorting.")
                first_line_content = chapter_name
            else:
                print(f"    Extracted first line: '{first_line_content}'")

        except Exception as e:
            print(f"    Error extracting first line from {os.path.basename(output_temp_pdf_path)}: {e}. Using chapter name for sorting.")
            first_line_content = chapter_name
        finally:
            if doc_temp_pdf: # Ensure PyMuPDF document is closed
                doc_temp_pdf.close()

        temp_merged_pdfs_info.append((first_line_content, output_temp_pdf_path, class_num, subject))

    except Exception as e:
        print(f"  Error merging PDFs for {class_num} - {subject} - {chapter_name}: {e}")
    finally:
        merger.close() # Ensure PdfMerger is closed

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
        chapter_match = re.search(r"(?:chapter|ch|unit|lesson)\s*(\d+)(?:[.\s-]+)?", normalized_key)
        
        if chapter_match:
            try:
                chapter_number = int(chapter_match.group(1))
                return (0, chapter_number) # Sort by chapter number (priority 0)
            except ValueError:
                pass # Continue to the next sorting rule

        # If no numerical chapter found, sort by normalized string (alphabetical, case-insensitive)
        return (1, normalized_key) # Sort by name (priority 1), case-insensitive

    pdf_list.sort(key=custom_sort)
    print(f"  Sorted chapters for Class {class_num} - {subject}")


# --- 4. Final Compilation into Book-Compiled.pdf with All Overlays ---
print("\nCompiling final books with index page, overlays (watermark, headers/footers)...")
for (class_num, subject), sorted_pdf_info in compiled_books_map.items():
    final_output_pdf_name = f"Class {class_num} - {subject} - Book-Compiled.pdf"
    final_output_pdf_path_initial_merge = os.path.join(TEMP_DIR, f"temp_initial_merged_{class_num}_{subject}.pdf") # Temp path before overlays
    final_output_pdf_path_final = os.path.join(GENERATED_DIR, final_output_pdf_name) # Final path

    # Create a temporary merger for the index page and content *without* overlays
    merger_without_overlays = PdfMerger()
    
    # 1. Add Index Page
    index_page_path = os.path.join(TEMP_DIR, f"index_page_{class_num}_{subject}.pdf")
    generate_index_page(subject, class_num, index_page_path)
    if os.path.exists(index_page_path):
        merger_without_overlays.append(index_page_path)

    # 2. Add main content PDFs
    pdfs_to_compile = [item[1] for item in sorted_pdf_info]
    try:
        if not pdfs_to_compile:
            print(f"  No content PDFs to compile for Class {class_num} - {subject}. Skipping book creation.")
            merger_without_overlays.close() # Close merger if nothing to compile
            continue

        for pdf_path in pdfs_to_compile:
            merger_without_overlays.append(pdf_path)

        # Save the initially merged PDF (with index, content) to a temp file
        with open(final_output_pdf_path_initial_merge, "wb") as f:
            merger_without_overlays.write(f)
        print(f"  Initial merge complete for '{os.path.basename(final_output_pdf_name)}'.")

        # Now, open the initially merged PDF and apply overlays selectively
        doc_with_index = fitz.open(final_output_pdf_path_initial_merge)
        final_doc_with_overlays = fitz.open()

        for i, page in enumerate(doc_with_index):
            new_page = final_doc_with_overlays.new_page(width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(page.rect, doc_with_index, page.number, overlay=False)

            # Apply watermark to all pages
            # Load watermark image (re-load if needed, or pass it from outside loop)
            watermark_pix = None
            if os.path.exists(WATERMARK_PATH):
                try:
                    watermark_pix_orig = fitz.Pixmap(WATERMARK_PATH)
                    if watermark_pix_orig.n < 4:
                        watermark_pix = fitz.Pixmap(fitz.csRGBA, watermark_pix_orig)
                    else:
                        watermark_pix = fitz.Pixmap(watermark_pix_orig)
                    desired_alpha = 0.15
                    for row in range(watermark_pix.height):
                        for col in range(watermark_pix.width):
                            r, g, b, a = watermark_pix.pixel(col, row)
                            watermark_pix.set_pixel(col, row, (r, g, b, int(a * desired_alpha)))
                    watermark_pix_orig = None
                except Exception as e:
                    print(f"  Warning: Could not load or process watermark image for individual page: {e}")
                    watermark_pix = None
            
            if watermark_pix:
                wm_aspect = watermark_pix.width / watermark_pix.height
                page_aspect = new_page.rect.width / new_page.rect.height

                if wm_aspect > page_aspect:
                    display_width = new_page.rect.width
                    display_height = display_width / wm_aspect
                else:
                    display_height = new_page.rect.height
                    display_width = display_height * wm_aspect
                
                wm_x = (new_page.rect.width - display_width) / 2
                wm_y = (new_page.rect.height - display_height) / 2
                
                new_page.insert_image(
                    fitz.Rect(wm_x, wm_y, wm_x + display_width, wm_y + display_height),
                    pixmap=watermark_pix,
                    overlay=False
                )
                watermark_pix = None # Release pixmap after use for each page


            # Apply headers and footers only if it's NOT the first page (index page)
            if i > 0: # i=0 is the index page
                header_strip_height = 50
                footer_strip_height = 60

                header_rect = fitz.Rect(0, 0, new_page.rect.width, header_strip_height)
                new_page.draw_rect(header_rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))

                footer_rect = fitz.Rect(0, new_page.rect.height - footer_strip_height, new_page.rect.width, new_page.rect.height)
                new_page.draw_rect(footer_rect, color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9), fill_opacity=1.0)

                # Header Content
                current_year = datetime.now().year
                header_text = f"Class {class_num} - {subject} - {current_year}"
                text_x = 10
                logo_width = 0

                logo_pix = None
                if os.path.exists(LOGO_PATH):
                    try:
                        logo_pix = fitz.Pixmap(LOGO_PATH)
                    except Exception as e:
                        print(f"  Warning: Could not load header logo image for individual page: {e}")
                        logo_pix = None
                
                if logo_pix:
                    logo_display_height = header_strip_height + 1
                    logo_display_width = (logo_pix.width / logo_pix.height) * logo_display_height
                    if logo_display_width > new_page.rect.width / 4:
                        logo_display_width = new_page.rect.width / 4
                        logo_display_height = (logo_pix.height / logo_pix.width) * logo_display_width
                    logo_rect = fitz.Rect(0, 0, 0 + logo_display_width, 0 + logo_display_height)
                    new_page.insert_image(logo_rect, pixmap=logo_pix)
                    logo_width = logo_rect.width + 10
                    text_x = logo_width
                    logo_pix = None # Release pixmap

                new_page.insert_text(
                    (text_x + 10, 28),
                    header_text,
                    fontname="Helvetica-Bold",
                    fontsize=20,
                    color=(0, 0, 0)
                )

                # Footer Content (Page Numbers)
                page_number_text = f"Page {i + 1} of {doc_with_index.page_count}" # Adjust total pages
                page_number_font_size = 10
                page_number_color = (0, 0, 0)

                pn_text_length = fitz.get_text_length(page_number_text, fontname="Helvetica", fontsize=page_number_font_size)
                pn_x_centered = (new_page.rect.width - pn_text_length) / 2
                pn_y = new_page.rect.height - (footer_strip_height / 2) + (page_number_font_size / 2) - 3

                new_page.insert_text(
                    (pn_x_centered, pn_y),
                    page_number_text,
                    fontname="Helvetica",
                    fontsize=page_number_font_size,
                    color=page_number_color
                )
        
        final_doc_with_overlays.save(final_output_pdf_path_final)
        print(f"  Successfully compiled final book '{final_output_pdf_path_final}' with index and selective overlays.")

    except Exception as e:
        print(f"  Error processing book '{final_output_pdf_name}': {e}")
    finally:
        merger_without_overlays.close()
        if doc_with_index:
            doc_with_index.close()
        if final_doc_with_overlays:
            final_doc_with_overlays.close()


# --- Cleanup Temporary Files ---
print("\nCleaning up temporary files...")
try:
    if os.path.exists(TEMP_DIR):
        for file_name in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
        # Check if directory is empty before trying to remove it
        if not os.listdir(TEMP_DIR):
            os.rmdir(TEMP_DIR)
        print("Temporary directory and files removed.")
    else:
        print("Temporary directory not found, no cleanup needed.")
except OSError as e:
    print(f"Error during temporary file cleanup: {e}")

print("\nProcess complete! Check the 'generated' directory for your compiled books.")