import os
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.ns import qn
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from PIL import Image

DATA_DIR = './data'
ASSET_DIR = './asset'

HEADER_LOGO = os.path.join(ASSET_DIR, 'amarujalalogo.png')
HEADER_BORDER = os.path.join(ASSET_DIR, 'header-border.png')
FOOTER_BORDER = os.path.join(ASSET_DIR, 'footer-border.png')

def add_header_footer(section, header_text):
    # Add header image (logo)
    header = section.header
    header_paragraph = header.paragraphs[0]
    run = header_paragraph.add_run()
    run.add_picture(HEADER_LOGO, width=Inches(1))
    header_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Add header text
    header_paragraph.add_run("   " + header_text).bold = True

    # Add footer
    footer = section.footer
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.text = "Page "
    footer_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

def parse_structure():
    book = {}
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith('.txt'):
                parts = file.split(' - ')
                if len(parts) != 4:
                    continue  # skip invalid files
                class_info = parts[0].strip()
                subject = parts[1].strip()
                chapter_name = parts[2].strip()
                typ = parts[3].replace('.txt', '').strip()

                key = (class_info, subject, chapter_name)
                if key not in book:
                    book[key] = {'explanation': None, 'questions': None}

                full_path = os.path.join(root, file)
                if 'Explanation' in typ:
                    book[key]['explanation'] = full_path
                elif 'Question' in typ:
                    book[key]['questions'] = full_path
    return book

def extract_chapter_title(questions_file):
    with open(questions_file, 'r', encoding='utf-8') as f:
        return f.readline().strip()

def add_separator(doc):
    para = doc.add_paragraph()
    run = para.add_run("—" * 50)
    para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

def add_content(doc, title, explanation_file, questions_file):
    # Chapter title
    doc.add_heading(title, level=1)

    add_separator(doc)

    # Explanations
    if explanation_file:
        with open(explanation_file, 'r', encoding='utf-8') as f:
            doc.add_heading("Explanations", level=2)
            for line in f:
                doc.add_paragraph(line.strip())

    # Questions
    if questions_file:
        with open(questions_file, 'r', encoding='utf-8') as f:
            doc.add_heading("Questions", level=2)
            lines = f.readlines()[1:]  # Skip first line (chapter title)
            for line in lines:
                doc.add_paragraph(line.strip())

def create_book(book_data):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    sorted_chapters = sorted(book_data.items(), key=lambda x: x[0][2])  # sort by chapter name

    for i, ((class_info, subject, chapter_name), files) in enumerate(sorted_chapters):
        section = doc.add_section() if i > 0 else doc.sections[0]

        chapter_title = extract_chapter_title(files['questions']) if files['questions'] else chapter_name
        header_text = f"{class_info}, {subject} - {chapter_title}"
        add_header_footer(section, header_text)

        add_content(doc, chapter_title, files['explanation'], files['questions'])

    output_file = f"{DATA_DIR}/../Compiled_Book.docx"
    doc.save(output_file)
    print(f"✅ Book saved as: {output_file}")

if __name__ == "__main__":
    book_data = parse_structure()
    create_book(book_data)
