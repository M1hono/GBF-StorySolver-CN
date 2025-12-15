"""
Lore extractor for GBF Wiki.

Output structure:
    characters/{character}/lore/raw/
    ├── profile/
    │   ├── english.md
    │   └── japanese.md
    ├── fate_episodes/
    │   ├── intro.md
    │   └── ... (story format)
    ├── special_cutscenes/
    │   ├── happy_birthday.md
    │   └── ... (story format)
    └── side_scrolling/
        └── quotes.md
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright, Page


def _slugify(text: str) -> str:
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[\s-]+', '_', slug)
    return slug.strip('_') or 'unnamed'


# Helper JS to find visible panel in tabber
FIND_VISIBLE_PANEL_JS = '''
(tabber) => {
    const section = tabber.querySelector(':scope > section');
    if (!section) return null;
    const panels = section.querySelectorAll(':scope > [role="tabpanel"]');
    for (const p of panels) {
        if (getComputedStyle(p).display !== 'none') return p;
    }
    return null;
}
'''


class LoreExtractor:
    def __init__(self, headless: bool = False, timeout: int = 60000):
        self.headless = headless
        self.timeout = timeout
    
    def extract(self, character_slug: str, character_dir: str) -> Dict[str, Any]:
        result = {"success": False, "files": [], "structure": {}, "character": character_slug}
        base = Path(character_dir) / "lore" / "raw"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout)
            
            try:
                url = f"https://gbf.wiki/{character_slug}/Lore"
                print(f"Navigating to: {url}")
                page.goto(url, wait_until="networkidle", timeout=90000)
                time.sleep(2)
                
                files = []
                structure = {}
                
                # 1. Profile
                print("\n[1/4] Profile...")
                pf = self._extract_profile(page, base, character_slug, url)
                files.extend(pf)
                structure["profile"] = [Path(f).name for f in pf]
                
                # 2. Special Cutscenes
                print("\n[2/4] Special Cutscenes...")
                sc = self._extract_section_tabs(page, base / "special_cutscenes", 
                                                 character_slug, url, "Special Cutscenes")
                files.extend(sc)
                structure["special_cutscenes"] = [Path(f).name for f in sc]
                
                # 3. Fate Episodes  
                print("\n[3/4] Fate Episodes...")
                fe = self._extract_section_tabs(page, base / "fate_episodes",
                                                 character_slug, url, "Fate Episodes")
                files.extend(fe)
                structure["fate_episodes"] = [Path(f).name for f in fe]
                
                # 4. Side-scrolling
                print("\n[4/4] Side-scrolling Quotes...")
                sq = self._extract_side_scrolling(page, base, character_slug, url)
                if sq:
                    files.append(sq)
                    structure["side_scrolling"] = [Path(sq).name]
                
                result["files"] = files
                result["structure"] = structure
                result["success"] = len(files) > 0
                
            except Exception as e:
                result["error"] = str(e)
                import traceback
                traceback.print_exc()
            finally:
                browser.close()
        
        return result
    
    def _extract_profile(self, page: Page, base: Path, char: str, url: str) -> List[str]:
        """Extract Official Profile tabs (English/Japanese only)."""
        files = []
        out_dir = base / "profile"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Get tab names from the header
        tabs = page.evaluate('''() => {
            const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes('Official Profile'));
            if (!h2) return [];
            let el = h2.nextElementSibling;
            while (el && !el.classList.contains('tabber')) el = el.nextElementSibling;
            if (!el) return [];
            const header = el.querySelector(':scope > header');
            if (!header) return [];
            return [...header.querySelectorAll('[role="tab"]')].map(t => t.textContent.trim());
        }''')
        
        for tab_name in tabs:
            if not tab_name:
                continue
            
            # Click tab
            page.evaluate('''(tabName) => {
                const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes('Official Profile'));
                if (!h2) return;
                let el = h2.nextElementSibling;
                while (el && !el.classList.contains('tabber')) el = el.nextElementSibling;
                if (!el) return;
                const header = el.querySelector(':scope > header');
                if (!header) return;
                const tab = [...header.querySelectorAll('[role="tab"]')].find(t => t.textContent.trim() === tabName);
                if (tab) tab.click();
            }''', tab_name)
            time.sleep(0.3)
            
            # Extract profile data from visible panel
            data = page.evaluate('''() => {
                const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes('Official Profile'));
                if (!h2) return null;
                let el = h2.nextElementSibling;
                while (el && !el.classList.contains('tabber')) el = el.nextElementSibling;
                if (!el) return null;
                
                const section = el.querySelector(':scope > section');
                if (!section) return null;
                const panels = section.querySelectorAll(':scope > [role="tabpanel"]');
                let panel = null;
                for (const p of panels) {
                    if (getComputedStyle(p).display !== 'none') { panel = p; break; }
                }
                if (!panel) return null;
                
                const table = panel.querySelector('table');
                if (!table) return null;
                const rows = [];
                table.querySelectorAll('tr').forEach(tr => {
                    const th = tr.querySelector('th, td:first-child');
                    const td = tr.querySelector('td:last-child');
                    if (th && td && th !== td) {
                        rows.push({ key: th.textContent.trim(), value: td.textContent.trim() });
                    }
                });
                return rows;
            }''')
            
            if not data:
                continue
            
            out_file = out_dir / f"{_slugify(tab_name)}.md"
            lines = [f"# {char} - Profile ({tab_name})\n\n", f"数据源：`{url}#Official_Profile`\n\n"]
            for row in data:
                lines.append(f"**{row['key']}**: {row['value']}\n\n")
            out_file.write_text(''.join(lines), encoding='utf-8')
            files.append(str(out_file))
            print(f"  {out_file.name}")
        
        return files
    
    def _extract_section_tabs(self, page: Page, out_dir: Path, char: str, url: str, section: str) -> List[str]:
        """Extract tabbed section (Special Cutscenes or Fate Episodes)."""
        files = []
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Get tab names
        tabs = page.evaluate('''(section) => {
            const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes(section));
            if (!h2) return [];
            let el = h2.nextElementSibling;
            while (el && !el.classList.contains('tabber')) el = el.nextElementSibling;
            if (!el) return [];
            const header = el.querySelector(':scope > header');
            if (!header) return [];
            return [...header.querySelectorAll('[role="tab"]')].map(t => t.textContent.trim());
        }''', section)
        
        for tab_name in tabs:
            if not tab_name or 'Spoiler' in tab_name:
                continue
            
            # Click tab
            page.evaluate('''(args) => {
                const [section, tabName] = args;
                const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes(section));
                if (!h2) return;
                let el = h2.nextElementSibling;
                while (el && !el.classList.contains('tabber')) el = el.nextElementSibling;
                if (!el) return;
                const header = el.querySelector(':scope > header');
                if (!header) return;
                const tab = [...header.querySelectorAll('[role="tab"]')].find(t => t.textContent.trim() === tabName);
                if (tab) tab.click();
            }''', [section, tab_name])
            time.sleep(0.5)
            
            # Extract content
            content = page.evaluate('''(section) => {
                const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes(section));
                if (!h2) return null;
                let el = h2.nextElementSibling;
                while (el && !el.classList.contains('tabber')) el = el.nextElementSibling;
                if (!el) return null;
                
                const sec = el.querySelector(':scope > section');
                if (!sec) return null;
                const panels = sec.querySelectorAll(':scope > [role="tabpanel"]');
                let panel = null;
                for (const p of panels) {
                    if (getComputedStyle(p).display !== 'none') { panel = p; break; }
                }
                if (!panel || panel.textContent.includes('Spoiler Alert')) return null;
                
                const lines = [];
                
                // Check for table (Special Cutscenes style - uses mix of th/td)
                const table = panel.querySelector('table');
                if (table) {
                    table.querySelectorAll('tr').forEach(tr => {
                        const cells = tr.querySelectorAll('td, th');
                        if (cells.length >= 3) {
                            // Last cell is the Text column
                            const lastCell = cells[cells.length - 1];
                            const text = lastCell.textContent.trim();
                            if (text && !text.includes('Spoiler') && text !== 'Text' && !text.includes('Cutscenes')) {
                                lines.push(text);
                            }
                        }
                    });
                } else {
                    // Story format (Fate Episodes)
                    panel.childNodes.forEach(node => {
                        if (node.nodeType !== 1) return;
                        const el = node;
                        const tag = el.tagName;
                        
                        if (tag === 'H3') {
                            lines.push('## ' + el.textContent.trim());
                        } else if (tag === 'EM' || tag === 'I') {
                            lines.push('*' + el.textContent.trim() + '*');
                        } else if (el.querySelector && el.querySelector('strong')) {
                            const strong = el.querySelector('strong');
                            const speaker = strong.textContent.trim();
                            const full = el.textContent.trim();
                            const dialogue = full.replace(speaker, '').trim();
                            if (speaker && dialogue) {
                                lines.push('**' + speaker + '** ' + dialogue);
                            }
                        } else if (tag === 'UL' || tag === 'OL') {
                            el.querySelectorAll('li').forEach(li => {
                                lines.push('- ' + li.textContent.trim());
                            });
                        }
                    });
                }
                
                return lines.length > 0 ? lines : null;
            }''', section)
            
            if not content:
                continue
            
            out_file = out_dir / f"{_slugify(tab_name)}.md"
            lines = [f"# {char} - {tab_name}\n\n", f"数据源：`{url}#{section.replace(' ', '_')}`\n\n"]
            for line in content:
                lines.append(f"{line}\n\n")
            out_file.write_text(''.join(lines), encoding='utf-8')
            files.append(str(out_file))
            print(f"  {out_file.name}")
        
        return files
    
    def _extract_side_scrolling(self, page: Page, base: Path, char: str, url: str) -> Optional[str]:
        """Extract Side-scrolling Quotes."""
        out_dir = base / "side_scrolling"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        quotes = page.evaluate('''() => {
            const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes('Side-scrolling'));
            if (!h2) return [];
            let el = h2.nextElementSibling;
            while (el && el.tagName !== 'TABLE') el = el.nextElementSibling;
            if (!el) return [];
            const rows = [];
            el.querySelectorAll('tr').forEach(tr => {
                const cells = tr.querySelectorAll('td');
                if (cells.length >= 2) {
                    rows.push({ jp: cells[0].textContent.trim(), en: cells[1].textContent.trim() });
                }
            });
            return rows;
        }''')
        
        if not quotes:
            print("  No quotes found")
            return None
        
        out_file = out_dir / "quotes.md"
        lines = [
            f"# {char} - Side-scrolling Quotes\n\n",
            f"数据源：`{url}#Side-scrolling_Quotes`\n\n",
            "| Japanese | Chinese | English |\n",
            "| --- | --- | --- |\n",
        ]
        for q in quotes:
            lines.append(f"| {q['jp']} |  | {q['en']} |\n")
        out_file.write_text(''.join(lines), encoding='utf-8')
        print(f"  {out_file.name}")
        return str(out_file)


def extract_lore(character: str, character_dir: str, headless: bool = False) -> Dict:
    return LoreExtractor(headless=headless).extract(character, character_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python lore.py <character> <dir>")
        sys.exit(1)
    result = extract_lore(sys.argv[1], sys.argv[2])
    print(f"\nSuccess: {result['success']}, Files: {len(result['files'])}")
