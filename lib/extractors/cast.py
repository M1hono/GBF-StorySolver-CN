"""
Cast extractor for GBF Wiki.

Output:
    characters/{character}/story/{event}/trans/cast.md

Cast is REQUIRED for every story event in the trans/ folder.
"""

import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright, Page


class CastExtractor:
    """Extract cast information from GBF Wiki story pages."""
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self._translator = None
    
    @property
    def translator(self):
        """Lazy load translator."""
        if self._translator is None:
            try:
                from ..translators.blhxfy import translator
                self._translator = translator
            except ImportError:
                try:
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent))
                    from translators.blhxfy import translator
                    self._translator = translator
                except ImportError:
                    self._translator = None
        return self._translator
    
    def extract(self, event_slug: str, character_dir: str, event_folder: str = None) -> Dict[str, Any]:
        """
        Extract cast from an event story page.
        
        Args:
            event_slug: Wiki event slug (e.g., "Auld_Lang_Fry_PREMIUM")
            character_dir: Character root directory (e.g., "characters/vajra")
            event_folder: Optional custom folder name (defaults to slugified event_slug)
        
        Returns:
            {success, cast, output_path, error?}
        """
        # Determine output path
        folder_name = event_folder or event_slug.lower().replace(' ', '_')
        output_path = Path(character_dir) / "story" / folder_name / "trans" / "cast.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = {
            "success": False, 
            "cast": [], 
            "event": event_slug,
            "output_path": str(output_path),
        }
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout)
            
            try:
                url = f"https://gbf.wiki/{event_slug}/Story"
                print(f"Navigating to: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)
                time.sleep(5)
                
                try:
                    page.wait_for_selector('img[src*="Npc_"]', timeout=15000)
                except:
                    print("Warning: Cast images may not be loaded")
                
                cast = self._extract_cast(page)
                result["cast"] = cast
                
                if cast:
                    self._save_cast_md(cast, output_path, event_slug, url)
                    result["success"] = True
                
            except Exception as e:
                result["error"] = str(e)
                print(f"Error: {e}")
            finally:
                browser.close()
        
        return result
    
    def _extract_cast(self, page: Page) -> List[Dict]:
        """Extract cast data from the page."""
        return page.evaluate(r'''
            () => {
                const cast = [];
                const links = document.querySelectorAll('a[href^="/"]');
                
                for (const link of links) {
                    const img = link.querySelector('img');
                    if (!img) continue;
                    
                    const name = link.getAttribute('title') || '';
                    let src = img.src || '';
                    const href = link.getAttribute('href') || '';
                    
                    // Only main portraits (Npc_m_), not zoom images
                    if (!src.includes('Npc_m_') || !name) continue;
                    if (cast.find(c => c.name === name)) continue;
                    
                    // Normalize to 200px
                    src = src.replace(/\/\d+px-/, '/200px-');
                    
                    cast.push({
                        name: name,
                        image_url: src,
                        wiki_url: href.startsWith('/') ? 'https://gbf.wiki' + href : href
                    });
                }
                return cast;
            }
        ''')
    
    def _save_cast_md(self, cast: List[Dict], output_path: Path, 
                      event_slug: str, source_url: str):
        """Save cast to markdown file."""
        lines = [
            f"# {event_slug.replace('_', ' ')} - Cast Portraits\n\n",
            f"数据源：`{source_url}`\n\n",
            "| 角色（英 / 中） | 头像 |\n",
            "| --- | --- |\n",
        ]
        
        for c in cast:
            name = c['name']
            img = c['image_url']
            wiki_url = c['wiki_url']
            
            cn = None
            if self.translator:
                cn = self.translator.smart_lookup(name)
            
            if cn:
                display = f"[{name} / {cn}]({wiki_url})"
            else:
                display = f"[{name}]({wiki_url})"
            
            lines.append(f"| {display} | ![{name}]({img}) |\n")
        
        output_path.write_text(''.join(lines), encoding='utf-8')
        print(f"Saved: {output_path}")


def extract_cast(event_slug: str, character_dir: str, event_folder: str = None,
                 headless: bool = False) -> Dict:
    """
    Convenience function to extract cast.
    
    Args:
        event_slug: Wiki event slug
        character_dir: Character root dir (e.g., "characters/vajra")
        event_folder: Optional custom folder name
        headless: Run browser in headless mode
    
    Returns:
        Extraction result dict
    """
    ext = CastExtractor(headless=headless)
    return ext.extract(event_slug, character_dir, event_folder)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python cast.py <event_slug> <character_dir> [event_folder]")
        print("Example: python cast.py Auld_Lang_Fry_PREMIUM characters/vajra")
        print()
        print("Output: story/{event_folder}/trans/cast.md")
        sys.exit(1)
    
    event_slug = sys.argv[1]
    character_dir = sys.argv[2]
    event_folder = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = extract_cast(event_slug, character_dir, event_folder)
    
    print(f"\nResult: {'Success' if result['success'] else 'Failed'}")
    print(f"Output: {result.get('output_path')}")
    print(f"Cast: {len(result['cast'])} characters")
