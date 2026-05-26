"""
Build script: reads Vocabulary Excel file and generates vocab-flashcards.html
with all words embedded.

Usage:
    python build-flashcards.py
    python build-flashcards.py --xlsx "path/to/file.xlsm"
"""

import json
import re
import sys
import argparse
from pathlib import Path

def load_words(xlsx_path):
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas is required. Install with: pip install pandas openpyxl")
        sys.exit(1)

    df = pd.read_excel(xlsx_path, sheet_name='Vocab')
    words = []
    for _, row in df.iterrows():
        word = str(row.get('Word (image)', '')).strip()
        if not word or word == 'nan':
            continue
        definition = str(row.get('Definition (image)', '')).strip()
        if definition == 'nan':
            definition = ''
        example = str(row.get('Example Sentence (mix)', '')).strip()
        if example == 'nan':
            example = ''
        # Clean up word: remove trailing part-of-speech markers like "(v.)", "(n.)"
        pos_match = re.search(r'\s*\(([a-z./]+)\)\s*$', word, re.IGNORECASE)
        pos = ''
        if pos_match:
            pos = pos_match.group(1)
            word = word[:pos_match.start()].strip()
        words.append({
            'word': word,
            'pos': pos,
            'pronunciation': '',
            'definition': definition,
            'example': example,
        })
    return words

def load_pdf_words(json_path, existing_words):
    """Load words extracted from handwritten PDF scans, skipping duplicates."""
    if not json_path.exists():
        return []
    with open(json_path, 'r', encoding='utf-8') as f:
        pdf_words = json.load(f)
    existing_lower = set(w['word'].strip().lower() for w in existing_words)
    new_words = []
    seen = set()
    for w in pdf_words:
        key = w['word'].strip().lower()
        if key not in existing_lower and key not in seen:
            new_words.append({
                'word': w['word'].strip(),
                'pos': w.get('pos', ''),
                'pronunciation': '',
                'definition': w.get('definition', ''),
                'example': w.get('example', ''),
            })
            seen.add(key)
    return new_words

def build_html(words, template_path, output_path):
    template = template_path.read_text(encoding='utf-8')
    # Find and replace the VOCAB array
    pattern = r'const VOCAB = \[.*?\];'
    vocab_json = json.dumps(words, ensure_ascii=False, indent=2)
    # Convert JSON array to JS: remove quotes from keys
    js_array = vocab_json
    for key in ['word', 'pos', 'pronunciation', 'definition', 'example']:
        js_array = js_array.replace(f'"{key}":', f'{key}:')
    replacement = f'const VOCAB = {js_array};'
    result = re.sub(pattern, replacement, template, flags=re.DOTALL)
    output_path.write_text(result, encoding='utf-8')
    return len(words)

def main():
    parser = argparse.ArgumentParser(description='Build vocab flashcard HTML from Excel')
    parser.add_argument('--xlsx', default=None, help='Path to Excel file')
    parser.add_argument('--template', default=None, help='Path to HTML template')
    parser.add_argument('--output', default=None, help='Output HTML file path')
    args = parser.parse_args()

    base = Path(__file__).parent
    xlsx_path = Path(args.xlsx) if args.xlsx else base / 'data' / 'Vocabulary 2024.xlsm'
    template_path = Path(args.template) if args.template else base / 'vocab-flashcards.html'
    output_path = Path(args.output) if args.output else base / 'vocab-flashcards.html'

    if not xlsx_path.exists():
        print(f"Error: Excel file not found: {xlsx_path}")
        sys.exit(1)
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}")
        sys.exit(1)

    print(f"Reading words from: {xlsx_path}")
    words = load_words(xlsx_path)
    print(f"Found {len(words)} words from Excel")

    pdf_json = base / 'data' / 'pdf_words.json'
    pdf_words = load_pdf_words(pdf_json, words)
    if pdf_words:
        words.extend(pdf_words)
        print(f"Added {len(pdf_words)} new words from PDF scans")
    print(f"Total: {len(words)} words")

    count = build_html(words, template_path, output_path)
    print(f"Built {output_path} with {count} words")
    size_kb = output_path.stat().st_size / 1024
    print(f"File size: {size_kb:.0f} KB")

if __name__ == '__main__':
    main()
