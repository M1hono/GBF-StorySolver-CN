"""
Voice line extractor for GBF Wiki.

Output structure follows the page's TOC (Table of Contents) hierarchy:
    characters/{character}/voice/raw/
    └── (files named by TOC sections)

The structure is NOT hardcoded - it's dynamically extracted from each page's TOC.
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright, Page


def _slugify(text: str) -> str:
    """Convert text to safe filename."""
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[\s-]+', '_', slug)
    return slug.strip('_')


class VoiceExtractor:
    """Extract voice lines from GBF Wiki character pages."""
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
    
    def extract(self, character_slug: str, character_dir: str) -> Dict[str, Any]:
        """
        Extract voice lines from a character's voice page.
        Structure is dynamically determined from the page's TOC.
        
        Args:
            character_slug: Wiki character slug (e.g., "Vajra", "Galleon_(Summer)")
            character_dir: Character root directory (e.g., "characters/vajra")
        
        Returns:
            {success, sections, files, toc, error?}
        """
        result = {
            "success": False, 
            "character": character_slug,
            "sections": [],
            "files": [],
            "toc": [],
        }
        
        base = Path(character_dir) / "voice" / "raw" / _slugify(character_slug)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout)
            
            try:
                url = f"https://gbf.wiki/{character_slug}/Voice"
                print(f"Navigating to: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)
                time.sleep(2)
                
                # 1. Parse TOC to understand page structure
                toc = self._parse_toc(page)
                result["toc"] = toc
                print(f"Found {len(toc)} TOC entries")
                
                # 2. Extract sections with their content
                sections = self._extract_sections(page, toc)
                result["sections"] = sections
                
                # 3. Save files based on TOC structure
                if sections:
                    files = self._save_sections(sections, base, character_slug, url)
                    result["files"] = files
                    result["success"] = True
                
            except Exception as e:
                result["error"] = str(e)
                import traceback
                traceback.print_exc()
            finally:
                browser.close()
        
        return result
    
    def _parse_toc(self, page: Page) -> List[Dict]:
        """
        Parse the Table of Contents to understand page structure.
        
        Returns:
            [{id, title, level, parent?}, ...]
        """
        return page.evaluate(r'''
            () => {
                const toc = [];
                const tocEl = document.querySelector('#toc, .toc, nav.mw-body-content');
                if (!tocEl) return toc;
                
                const items = tocEl.querySelectorAll('li');
                for (const item of items) {
                    const link = item.querySelector('a');
                    if (!link) continue;
                    
                    const href = link.getAttribute('href') || '';
                    const id = href.replace('#', '');
                    
                    // Extract number and title
                    const numEl = link.querySelector('.tocnumber');
                    const textEl = link.querySelector('.toctext');
                    const num = numEl?.textContent?.trim() || '';
                    const title = textEl?.textContent?.trim() || link.textContent?.trim() || '';
                    
                    // Determine level from number (1.1 = level 2, etc.)
                    const dots = (num.match(/\./g) || []).length;
                    const level = dots + 1;
                    
                    toc.push({ id, title, level, num });
                }
                
                return toc;
            }
        ''')
    
    def _extract_sections(self, page: Page, toc: List[Dict]) -> List[Dict]:
        """
        Extract content for each TOC section.
        
        Returns:
            [{id, title, level, tables: [{type, rows}], ...}, ...]
        """
        return page.evaluate(r'''
            (toc) => {
                const sections = [];
                
                for (const entry of toc) {
                    const heading = document.getElementById(entry.id);
                    if (!heading) continue;
                    
                    const section = {
                        id: entry.id,
                        title: entry.title,
                        level: entry.level,
                        num: entry.num,
                        tables: []
                    };
                    
                    // Find tables between this heading and the next heading
                    let node = heading.closest('h2, h3, h4')?.nextElementSibling;
                    const stopAtLevels = ['H2', 'H3', 'H4'];
                    
                    while (node) {
                        // Stop if we hit another heading
                        if (stopAtLevels.includes(node.tagName)) break;
                        
                        // Look for tables
                        const table = node.matches('table.wikitable') ? node : 
                                     node.querySelector?.('table.wikitable');
                        
                        if (table) {
                            const tableData = extractTable(table, entry.title);
                            if (tableData.rows.length > 0) {
                                section.tables.push(tableData);
                            }
                        }
                        
                        node = node.nextElementSibling;
                    }
                    
                    sections.push(section);
                }
                
                return sections;
                
                function extractTable(table, sectionTitle) {
                    const header = table.querySelector('th')?.textContent?.trim() || '';
                    const isChainBurst = header.includes('Chain') || sectionTitle === 'Chain Burst';
                    const type = isChainBurst ? 'chain_burst' :
                                header.includes('Menu') ? 'menu' : 
                                header.includes('Battle') ? 'battle' :
                                header.includes('Home') ? 'home' : 'other';
                    
                    const rows = [];
                    const trs = Array.from(table.querySelectorAll('tr'));
                    
                    // Track rowspan values for inherited cells
                    let inheritedElement = '';
                    let elementRowsLeft = 0;
                    let inheritedLabel = '';
                    let labelRowsLeft = 0;
                    
                    for (const tr of trs) {
                        const cells = Array.from(tr.querySelectorAll('td'));
                        if (cells.length < 1) continue;
                        
                        // Skip header rows (rows with only th elements, or mixed th+td header rows)
                        if (tr.querySelector('th') && cells.length === 0) continue;
                        // Skip if first cell is a header cell
                        const firstIsHeader = tr.querySelector('th:first-child');
                        if (firstIsHeader && cells.length <= 1) continue;
                        
                        // Find audio link
                        const audioLink = tr.querySelector('a[href*=".mp3"]');
                        const audio = audioLink?.href || '';
                        
                        let label = '';
                        let japanese = '';
                        let english = '';
                        let notes = '';
                        let element = '';  // For chain burst
                        let chain = '';    // For chain burst
                        
                        // ===== CHAIN BURST SPECIAL HANDLING =====
                        if (isChainBurst) {
                            // Chain Burst structure: Element(rowspan) | Chain | JP | EN | Notes | Play
                            // OR: Chain Start row: JP | EN | Notes | Play (fewer columns)
                            
                            // Skip "Applicable Characters" row (has character links/images)
                            if (tr.querySelector('a[href*="/Anila"], a[href*="/Andira"], a[href*="/Mahira"]')) {
                                continue;
                            }
                            
                            let colIdx = 0;
                            
                            // Check if we're inheriting element from rowspan
                            if (elementRowsLeft > 0) {
                                element = inheritedElement;
                                elementRowsLeft--;
                            } else if (cells[0]) {
                                // First cell might be Element with rowspan
                                const rowspan = parseInt(cells[0].getAttribute('rowspan')) || 1;
                                const cellText = cells[0].textContent?.trim() || '';
                                
                                // Is it an element name? (Fire, Water, Earth, Wind, Light, Dark)
                                if (['Fire', 'Water', 'Earth', 'Wind', 'Light', 'Dark'].includes(cellText)) {
                                    element = cellText;
                                    if (rowspan > 1) {
                                        inheritedElement = element;
                                        elementRowsLeft = rowspan - 1;
                                    }
                                    colIdx = 1;
                                } else {
                                    // Not an element - might be Chain Start or continuation
                                    element = '';
                                }
                            }
                            
                            // Next cell should be Chain (2/3/4) or JP text
                            if (cells[colIdx]) {
                                const cellText = cells[colIdx].textContent?.trim() || '';
                                if (['2', '3', '4'].includes(cellText)) {
                                    chain = cellText;
                                    colIdx++;
                                }
                            }
                            
                            // Build label from element + chain
                            if (element && chain) {
                                label = `${element} ${chain}-Chain`;
                            } else if (element) {
                                label = element;
                            } else if (chain) {
                                label = `${chain}-Chain`;
                            } else {
                                label = 'Chain Start';
                            }
                            
                            // Remaining cells: JP | EN | Notes | Play
                            japanese = cells[colIdx]?.textContent?.trim() || '';
                            english = cells[colIdx + 1]?.textContent?.trim() || '';
                            notes = cells[colIdx + 2]?.textContent?.trim() || '';
                            
                        } else {
                            // ===== STANDARD TABLE HANDLING =====
                            // Handle rowspan for label inheritance (multi-voice entries)
                            let colIdx = 0;
                            
                            if (labelRowsLeft > 0) {
                                label = inheritedLabel;
                                labelRowsLeft--;
                            } else if (cells[0]) {
                                const rowspan = parseInt(cells[0].getAttribute('rowspan')) || 1;
                                const cellText = cells[0].textContent?.trim() || '';
                                
                                // Check if it looks like a label (short, English-ish)
                                const looksLikeLabel = cellText.length < 50 && 
                                    !/^[\u3040-\u30ff\u4e00-\u9fff]/.test(cellText);
                                
                                if (looksLikeLabel || cells.length >= 5) {
                                    label = cellText;
                                    if (rowspan > 1) {
                                        inheritedLabel = label;
                                        labelRowsLeft = rowspan - 1;
                                    }
                                    colIdx = 1;
                                }
                            }
                            
                            // Extract remaining columns based on cell count
                            const remaining = cells.length - colIdx;
                            
                            if (remaining >= 4) {
                                // Label | JP | EN | Notes | Play
                                japanese = cells[colIdx]?.textContent?.trim() || '';
                                english = cells[colIdx + 1]?.textContent?.trim() || '';
                                notes = cells[colIdx + 2]?.textContent?.trim() || '';
                            } else if (remaining >= 3) {
                                // JP | EN | Notes or JP | EN | Play
                                japanese = cells[colIdx]?.textContent?.trim() || '';
                                english = cells[colIdx + 1]?.textContent?.trim() || '';
                                // Check if 3rd col is notes or audio
                                const thirdText = cells[colIdx + 2]?.textContent?.trim() || '';
                                if (!cells[colIdx + 2]?.querySelector('a[href*=".mp3"]')) {
                                    notes = thirdText;
                                }
                            } else if (remaining >= 2) {
                                // JP | EN or Label | JP
                                const c0 = cells[colIdx]?.textContent?.trim() || '';
                                const c1 = cells[colIdx + 1]?.textContent?.trim() || '';
                                if (/[\u3040-\u30ff]/.test(c0)) {
                                    japanese = c0;
                                    english = c1;
                                } else if (colIdx === 0) {
                                    // Still at first cell, might be label
                                    label = c0;
                                    japanese = c1;
                                } else {
                                    japanese = c0;
                                    english = c1;
                                }
                            } else if (remaining >= 1) {
                                japanese = cells[colIdx]?.textContent?.trim() || '';
                            }
                        }
                        
                        // Keep row if it has meaningful content
                        if (audio || label || japanese || english) {
                            rows.push({ label, japanese, english, notes, audio });
                        }
                    }
                    
                    return { type, header, rows };
                }
            }
        ''', toc)
    
    def _save_sections(
        self, 
        sections: List[Dict], 
        base: Path, 
        character: str, 
        source_url: str
    ) -> List[str]:
        """
        Save sections as markdown files following TOC hierarchy.
        
        Level 1 sections (h2) become top-level files.
        Level 2+ sections (h3, h4) become files in parent folders.
        """
        files = []
        base.mkdir(parents=True, exist_ok=True)
        
        current_parent = None
        
        for section in sections:
            if not section.get('tables') or all(len(t.get('rows', [])) == 0 for t in section['tables']):
                # Track parent for hierarchy, even if empty
                if section['level'] == 1:
                    current_parent = _slugify(section['title'])
                continue
            
            # Determine output path based on level
            if section['level'] == 1:
                current_parent = _slugify(section['title'])
                filepath = base / f"{_slugify(section['title'])}.md"
            else:
                # Child section - put in parent folder
                if current_parent:
                    folder = base / current_parent
                    folder.mkdir(parents=True, exist_ok=True)
                    filepath = folder / f"{_slugify(section['title'])}.md"
                else:
                    filepath = base / f"{_slugify(section['title'])}.md"
            
            # Build markdown - use specialized builder for Chain Burst
            is_chain_burst = section.get('title', '').lower() == 'chain burst' or \
                            any(t.get('type') == 'chain_burst' for t in section.get('tables', []))
            
            if is_chain_burst:
                content = self._build_chain_burst_markdown(section, character, source_url)
            else:
                content = self._build_markdown(section, character, source_url)
            
            filepath.write_text(content, encoding='utf-8')
            files.append(str(filepath))
            print(f"  Saved: {filepath.relative_to(base)}")
        
        return files
    
    def _build_markdown(self, section: Dict, character: str, source_url: str) -> str:
        """Build markdown content for a section with Chinese placeholder column."""
        lines = [
            f"# {character} - {section['title']}\n\n",
            f"数据源：`{source_url}#{section['id']}`\n\n",
        ]
        
        for table in section.get('tables', []):
            if not table.get('rows'):
                continue
            
            # Table header - always include Chinese column for translation
            lines.append("| Label | Japanese | Chinese | English | Notes | Audio |\n")
            lines.append("| --- | --- | --- | --- | --- | --- |\n")
            
            for row in table['rows']:
                label = self._escape_cell(row.get('label', ''))
                jp = self._escape_cell(row.get('japanese', ''))
                en = self._escape_cell(row.get('english', ''))
                notes = self._escape_cell(row.get('notes', ''))
                audio = f"[mp3]({row['audio']})" if row.get('audio') else ""
                
                # Chinese column is always empty - for later translation
                chinese = ""
                
                lines.append(f"| {label} | {jp} | {chinese} | {en} | {notes} | {audio} |\n")
            
            lines.append("\n")
        
        return ''.join(lines)
    
    def _build_chain_burst_markdown(self, section: Dict, character: str, source_url: str) -> str:
        """Build markdown for Chain Burst section with proper structure."""
        lines = [
            f"# {character} - {section['title']}\n\n",
            f"数据源：`{source_url}#{section['id']}`\n\n",
        ]
        
        for table in section.get('tables', []):
            if not table.get('rows'):
                continue
            
            # Group by element for better readability
            lines.append("| Label | Japanese | Chinese | English | Audio |\n")
            lines.append("| --- | --- | --- | --- | --- |\n")
            
            for row in table['rows']:
                label = self._escape_cell(row.get('label', ''))
                jp = self._escape_cell(row.get('japanese', ''))
                en = self._escape_cell(row.get('english', ''))
                audio = f"[mp3]({row['audio']})" if row.get('audio') else ""
                chinese = ""
                
                lines.append(f"| {label} | {jp} | {chinese} | {en} | {audio} |\n")
            
            lines.append("\n")
        
        return ''.join(lines)
    
    def _escape_cell(self, text: str) -> str:
        """Escape text for markdown table cell."""
        if not text:
            return ""
        return text.replace('|', '\\|').replace('\n', ' ').strip()


def extract_voice(character: str, character_dir: str, headless: bool = False) -> Dict:
    """
    Convenience function to extract voice for a character.
    
    Args:
        character: Character slug (e.g., "Vajra", "Galleon_(Summer)")
        character_dir: Character root dir (e.g., "characters/vajra")
        headless: Run browser in headless mode
    
    Returns:
        Extraction result dict with TOC-based structure
    """
    ext = VoiceExtractor(headless=headless)
    return ext.extract(character, character_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python voice.py <character_slug> <character_dir>")
        print("Example: python voice.py Vajra characters/vajra")
        print("         python voice.py Galleon_(Summer) characters/galleon_summer")
        print()
        print("Output structure is DYNAMIC based on the page's Table of Contents.")
        sys.exit(1)
    
    result = extract_voice(sys.argv[1], sys.argv[2])
    
    print(f"\n{'='*50}")
    print(f"Result: {'Success' if result['success'] else 'Failed'}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"\nTOC entries: {len(result.get('toc', []))}")
    for entry in result.get('toc', []):
        indent = '  ' * (entry.get('level', 1) - 1)
        print(f"  {indent}{entry.get('num', '')} {entry.get('title', '')}")
    print(f"\nFiles created: {len(result.get('files', []))}")
    for f in result.get('files', []):
        print(f"  - {f}")
