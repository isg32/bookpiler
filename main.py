import os
import logging
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

# ---------------------------
# Setup logger
# ---------------------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("Bookpiler")

# ---------------------------
# Configs
# ---------------------------
DATA_DIR = './data'
ASSET_DIR = './asset'
HEADER_LOGO = os.path.join(ASSET_DIR, 'amarujalalogo.png')
HEADER_BORDER = os.path.join(ASSET_DIR, 'header-border.png')
FOOTER_BORDER = os.path.join(ASSET_DIR, 'footer-border.png')

ALLOWED_EXT = ['.txt', '.pdf']

# ---------------------------
# Helpers
# ---------------------------
def read_file_text(path):
    if path.endswith('.txt'):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    elif path.endswith('.pdf'):
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    return ""

def extract_chapter_title(text):
    lines = text.strip().splitlines()
    for line in lines:
        if line.lower().startswith("chapter"):
            return line.strip()
    return "Untitled Chapter"

def render_text_block(doc, text):
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('[image:') and line.endswith(']'):
            img_path = line[7:-1].strip()
            if os.path.exists(img_path):
                logger.info(f"Adding image: {img_path}")
                doc.add_picture(img_path, width=Inches(4.5))
            else:
                logger.warning(f"Image not found: {img_path}")
        else:
            doc.add_paragraph(line)

def add_separator(doc):
    para = doc.add_paragraph()
    run = para.add_run("―" * 60)
    para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

def add_header_footer(section, header_text):
    logger.info(f"Setting header/footer for section: {header_text}")

    # Disable "Link to Previous"
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    # Clear existing header
    for para in section.header.paragraphs:
        para.clear()

    # Add new header content
    header_para = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
    run = header_para.add_run()
    if os.path.exists(HEADER_LOGO):
        run.add_picture(HEADER_LOGO, width=Inches(1))
    header_para.add_run(f"   {header_text}").bold = True
    header_para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Clear existing footer
    for para in section.footer.paragraphs:
        para.clear()

    # Add new footer content
    footer_para = section.footer.paragraphs[0] if section.footer.paragraphs else section.footer.add_paragraph()
    footer_para.text = "Page "
    footer_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

# ---------------------------
# Core Parser
# ---------------------------
def parse_structure():
    logger.info("Scanning data directory...")
    book = {}

    for class_folder in os.listdir(DATA_DIR):
        class_path = os.path.join(DATA_DIR, class_folder)
        if not os.path.isdir(class_path):
            continue

        files = [f for f in os.listdir(class_path) if os.path.splitext(f)[1].lower() in ALLOWED_EXT]

        for file in files:
            lower_file = file.lower()
            full_path = os.path.join(class_path, file)

            if 'explanation' in lower_file:
                key = file.split(' - ')[2].strip()  # chapter name part
                book.setdefault(class_folder, {}).setdefault(key, {})['explanation'] = full_path
            elif 'question' in lower_file:
                key = file.split(' - ')[2].strip()
                book.setdefault(class_folder, {}).setdefault(key, {})['questions'] = full_path

    logger.info(f"✅ Found {sum(len(v) for v in book.values())} chapters across {len(book)} class-subject folders.")
    return book

# ---------------------------
# Create the book
# ---------------------------
def create_book(book_data):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    for folder, chapters in book_data.items():
        class_info_parts = folder.split()
        class_name = class_info_parts[1]
        subject = class_info_parts[2]

        for chapter_key in sorted(chapters):
            chapter_files = chapters[chapter_key]
            explanation_text = read_file_text(chapter_files.get('explanation', ''))
            questions_text = read_file_text(chapter_files.get('questions', ''))

            title = extract_chapter_title(questions_text or explanation_text or chapter_key)
            logger.info(f"Writing chapter: {title}")

            section = doc.add_section() if doc.sections else doc.sections[0]
            header_text = f"Class {class_name}, {subject} - {title}"
            add_header_footer(section, header_text)

            doc.add_page_break()
            doc.add_heading(title, level=1)
            add_separator(doc)

            if explanation_text:
                doc.add_heading("Explanations", level=2)
                render_text_block(doc, explanation_text)

            if questions_text:
                doc.add_heading("Questions", level=2)
                lines = questions_text.splitlines()
                # Remove first line if it's chapter title
                if lines and lines[0].lower().startswith("chapter"):
                    lines = lines[1:]
                render_text_block(doc, "\n".join(lines))

    output_file = "./Compiled_Book.docx"
    logger.info(f"Saving book to {output_file}")
    doc.save(output_file)
    logger.info("✅ Book compiled successfully.")

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    logger.info("📘 Bookpiler started")
    book_data = parse_structure()
    create_book(book_data)
    logger.info("📗 Done.")
