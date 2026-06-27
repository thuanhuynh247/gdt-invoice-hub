# -*- coding: utf-8 -*-
import os
import re
import urllib.parse
from datetime import datetime
import sqlite3
import requests
from bs4 import BeautifulSoup

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.db")

def get_db_connection():
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH)

def extract_effective_date(text: str) -> str:
    """
    Search for common Vietnamese patterns describing the effective date of a law/regulation.
    e.g., 'hiệu lực thi hành từ ngày 01/01/2026', 'có hiệu lực từ ngày 01 tháng 07 năm 2025'.
    """
    # Pattern 1: ngày DD/MM/YYYY
    pattern1 = re.search(r'(?:hiệu lực|áp dụng)(?: thi hành)?(?: kể)? từ ngày\s+(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', text, re.IGNORECASE)
    if pattern1:
        d, m, y = pattern1.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    # Pattern 2: ngày DD tháng MM năm YYYY
    pattern2 = re.search(r'(?:hiệu lực|áp dụng)(?: thi hành)?(?: kể)? từ ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', text, re.IGNORECASE)
    if pattern2:
        d, m, y = pattern2.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    # Default to current date if not found
    return datetime.now().strftime("%Y-%m-%d")

def clean_html_to_text(html_content: str) -> str:
    """
    Parse raw HTML content and return cleaned text, stripping headers, footers, script, and style tags.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script, style, nav, footer, ads
    for s in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
        s.decompose()
        
    # Extract paragraphs and headers
    content_parts = []
    
    # Check for common main content containers on Vietnamese news/law sites
    main_content = soup.find(class_=re.compile(r'(content|detail|article|post-body|main-text|document)', re.I))
    container = main_content if main_content else soup.body
    
    if container:
        for element in container.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li']):
            text = element.get_text().strip()
            if text and len(text) > 10:
                # Clean multiple spaces/tabs
                text = re.sub(r'\s+', ' ', text)
                content_parts.append(text)
    else:
        # Fallback to simple body text extraction
        text = soup.get_text()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        content_parts = [re.sub(r'\s+', ' ', line) for line in lines if len(line) > 15]
        
    return "\n".join(content_parts)

def fetch_and_clean_url(url: str) -> tuple[str, str]:
    """
    Fetch raw HTML from a Vietnamese tax URL and extract clean text and title.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Try fetching content
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    
    # Ensure correct encoding (detect if Vietnamese characters are mangled)
    if response.encoding == 'ISO-8859-1':
        response.encoding = response.apparent_encoding
        
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Get Title
    title = ""
    if soup.title:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text().strip()
    if not title:
        title = urllib.parse.urlparse(url).netloc
        
    full_text = clean_html_to_text(response.text)
    return title, full_text

def chunk_text(text: str, max_words: int = 180) -> list[str]:
    """
    Split long text into chunks of roughly max_words.
    """
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        words = para.split(" ")
        # If adding this paragraph exceeds max_words and we already have some words, output current chunk
        if current_word_count + len(words) > max_words and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [para]
            current_word_count = len(words)
        else:
            current_chunk.append(para)
            current_word_count += len(words)
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

def ingest_crawled_content(url: str, custom_title: str, text: str, effective_date: str = None) -> dict:
    """
    Ingest crawled tax text into SQLite FTS5 database.
    """
    if not text or not text.strip():
        return {"success": False, "error": "No text content found to ingest."}
        
    # Auto-extract date if not provided
    if not effective_date:
        effective_date = extract_effective_date(text)
        
    doc_source = custom_title.strip() if custom_title else "Crawled Document"
    if not doc_source.endswith(".pdf") and not doc_source.endswith(".html"):
        # Append source type for display
        doc_source = f"{doc_source} (Web)"
        
    chunks = chunk_text(text, max_words=200)
    if not chunks:
        return {"success": False, "error": "Extracted text was too short to chunk."}
        
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Could not connect to database."}
        
    try:
        cursor = conn.cursor()
        
        # Ensure tables exist (just in case)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tax_regulation_chunk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_source TEXT,
                page_number INTEGER,
                effective_date TEXT,
                chunk_content TEXT,
                created_at TEXT
            );
        """)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tax_regulation_fts USING fts5(
                chunk_id UNINDEXED,
                chunk_content,
                document_source,
                page_number
            );
        """)
        conn.commit()
        
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inserted_count = 0
        
        # Insert chunks
        for idx, chunk_content in enumerate(chunks):
            page_number = idx + 1
            
            cursor.execute("""
                INSERT INTO tax_regulation_chunk (document_source, page_number, effective_date, chunk_content, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (doc_source, page_number, effective_date, chunk_content, now_str))
            
            cid = cursor.lastrowid
            
            # Insert to FTS5 virtual table
            cursor.execute("""
                INSERT INTO tax_regulation_fts (chunk_id, chunk_content, document_source, page_number)
                VALUES (?, ?, ?, ?)
            """, (cid, chunk_content, doc_source, page_number))
            
            inserted_count += 1
            
        conn.commit()
        return {
            "success": True,
            "document_source": doc_source,
            "chunks_count": inserted_count,
            "effective_date": effective_date
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
