import os
import logging
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Setup logger
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("Bookpiler")

# Config
DATA_DIR = './data'
ASSET_DIR = './asset'
HEADER_LOGO = os.path.join(ASSET_DIR, 'amarujalalogo.png')

ALLOWED_EXT = ['.txt', '.pdf']

# Helpers
def read_file_text(path):
    if path.endswith('.txt'):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    elif path.endswith('.pdf'):
        doc = fitz.open(path)
        return "\n".join([page.get_text() for page in doc])
    return ""

def extract_chapter_title_from_text(text):
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

def insert_page_number(paragraph):
    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar')  # field begin
    fldChar1.set(qn('w:fldCharType'), 'begin')

    instrText = OxmlElement('w:instrText')  # actual field code
    instrText.text = 'PAGE'

    fldChar2 = OxmlElement('w:fldChar')  # separate
    fldChar2.set(qn('w:fldCharType'), 'separate')

    fldChar3 = OxmlElement('w:fldChar')  # field end
    fldChar3.set(qn('w:fldCharType'), 'end')

    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

def add_header_footer(section, header_text):
    logger.info(f"Setting header/footer: {header_text}")
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False

    # Clear and add header
    header_para = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
    header_para.clear()
    run = header_para.add_run()
    if os.path.exists(HEADER_LOGO):
        try:
            run.add_picture(HEADER_LOGO, width=Inches(1), height=Cm(1.2))
        except Exception as e:
            logger.warning(f"Logo insert failed: {e}")
    header_para.add_run(f"   {header_text}").bold = True
    header_para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Clear and add footer with page number
    footer_para = section.footer.paragraphs[0] if section.footer.paragraphs else section.footer.add_paragraph()
    footer_para.clear()
    insert_page_number(footer_para)
    footer_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

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
            try:
                parts = file.split(' - ')
                chapter_key = parts[2].strip()
            except:
                logger.warning(f"Invalid file name format: {file}")
                continue

            if 'explanation' in lower_file:
                book.setdefault(class_folder, {}).setdefault(chapter_key, {})['explanation'] = full_path
            elif 'question' in lower_file:
                book.setdefault(class_folder, {}).setdefault(chapter_key, {})['questions'] = full_path

    total_chapters = sum(len(v) for v in book.values())
    logger.info(f"✅ Found {total_chapters} chapters across {len(book)} folders.")
    return book

def create_book(book_data):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    first_section = True

    for folder, chapters in book_data.items():
        class_info_parts = folder.split()
        class_name = class_info_parts[1]
        subject = class_info_parts[2]

        for chapter_key in sorted(chapters):
            chapter_files = chapters[chapter_key]
            explanation_text = read_file_text(chapter_files.get('explanation', ''))
            questions_text = read_file_text(chapter_files.get('questions', ''))

            chapter_title = extract_chapter_title_from_text(questions_text or explanation_text or chapter_key)
            logger.info(f"Writing chapter: {chapter_title}")

            section = doc.sections[0] if first_section else doc.add_section()
            first_section = False

            header_text = f"Class {class_name}, {subject} - {chapter_title}"
            add_header_footer(section, header_text)

            doc.add_page_break()
            doc.add_heading(chapter_title, level=1)
            add_separator(doc)

            if explanation_text:
                doc.add_heading("Explanations", level=2)
                render_text_block(doc, explanation_text)

            if questions_text:
                doc.add_heading("Questions", level=2)
                lines = questions_text.strip().splitlines()
                if lines and lines[0].lower().startswith("chapter"):
                    lines = lines[1:]
                render_text_block(doc, "\n".join(lines))

    output_file = "./Compiled_Book.docx"
    logger.info(f"Saving to: {output_file}")
    doc.save(output_file)
    logger.info("✅ Book compiled successfully.")

# Run
if __name__ == "__main__":
    logger.info("📘 Bookpiler started")
    book_data = parse_structure()
    create_book(book_data)
    logger.info("📗 Done.")
