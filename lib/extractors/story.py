"""
Story extractor for GBF Wiki.

Output structure:
    characters/{character}/story/{event_slug}/
    ├── raw/
    │   ├── 01_opening.md
    │   ├── 02_ch_1_-_ep_1.md
    │   ├── 03_ch_1_-_ep_2.md
    │   └── ...
    └── trans/
        ├── cast.md           # Character portraits (required)
        └── ...
"""

import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright, Page


class StoryExtractor:
    """Extract story chapters from GBF Wiki event pages."""
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
    
    def extract(self, event_slug: str, character_dir: str, event_folder: str = None) -> Dict[str, Any]:
        """
        Extract all story chapters from an event.
        
        Args:
            event_slug: Wiki event slug (e.g., "Auld_Lang_Fry_PREMIUM")
            character_dir: Character root directory (e.g., "characters/vajra")
            event_folder: Optional custom folder name (defaults to slugified event_slug)
        
        Returns:
            {success, chapters, output_dir, error?}
        """
        folder_name = event_folder or event_slug.lower().replace(' ', '_')
        output_dir = Path(character_dir) / "story" / folder_name / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            "success": False, 
            "chapters": [], 
            "event": event_slug,
            "output_dir": str(output_dir),
        }
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout)
            
            try:
                url = f"https://gbf.wiki/{event_slug}/Story"
                print(f"Navigating to: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)
                time.sleep(3)
                
                chapters = self._extract_all_content(page, output_dir)
                result["chapters"] = chapters
                result["success"] = len(chapters) > 0
                
            except Exception as e:
                result["error"] = str(e)
                print(f"Error: {e}")
            finally:
                browser.close()
        
        return result
    
    def _extract_all_content(self, page: Page, output_dir: Path) -> List[str]:
        """Extract all story content using JavaScript to handle nested tabs."""
        
        # Use JavaScript to get all tab panel IDs and their content
        content_data = page.evaluate(r'''
            () => {
                const results = [];
                const panels = document.querySelectorAll('[role="tabpanel"]');
                
                for (const panel of panels) {
                    const panelId = panel.id;
                    
                    // Skip if it contains nested tablist (it's a container, not content)
                    const hasNestedTablist = panel.querySelector('[role="tablist"]');
                    if (hasNestedTablist) continue;
                    
                    // Skip spoiler
                    if (panelId.toLowerCase().includes('spoiler')) continue;
                    
                    // Get title from h3
                    const h3 = panel.querySelector('h3 .mw-headline');
                    const title = h3 ? h3.textContent.trim() : panelId;
                    
                    // Get all dialogue and narration
                    const lines = [];
                    
                    // Title
                    lines.push('# ' + title);
                    lines.push('');
                    
                    // Find summary (first div with width style)
                    const summaryDiv = panel.querySelector('div[style*="width"]');
                    if (summaryDiv) {
                        const summaryText = summaryDiv.textContent.trim();
                        if (summaryText) {
                            lines.push('*' + summaryText + '*');
                            lines.push('');
                        }
                    }
                    
                    // Get ALL elements in document order using TreeWalker
                    const walker = document.createTreeWalker(
                        panel,
                        NodeFilter.SHOW_ELEMENT,
                        {
                            acceptNode: function(node) {
                                // Accept EM (narration) and DIV with direct strong child (dialogue)
                                if (node.tagName === 'EM') return NodeFilter.FILTER_ACCEPT;
                                if (node.tagName === 'DIV' && node.querySelector(':scope > strong')) {
                                    return NodeFilter.FILTER_ACCEPT;
                                }
                                return NodeFilter.FILTER_SKIP;
                            }
                        },
                        false
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.tagName === 'EM') {
                            // Narration
                            const text = node.textContent.trim();
                            if (text && !node.querySelector('strong')) {
                                lines.push('*' + text + '*');
                                lines.push('');
                            }
                        } else if (node.tagName === 'DIV') {
                            // Dialogue
                            const strong = node.querySelector(':scope > strong');
                            if (strong) {
                                const speaker = strong.textContent.replace(/[：:]/g, '').trim();
                                const fullText = node.textContent.trim();
                                const dialogue = fullText.slice(strong.textContent.length).trim();
                                if (speaker && dialogue && !dialogue.startsWith('Choose')) {
                                    lines.push('**' + speaker + ':** ' + dialogue);
                                    lines.push('');
                                }
                            }
                        }
                    }
                    
                    if (lines.length > 2) {
                        results.push({
                            id: panelId,
                            title: title,
                            content: lines.join('\n')
                        });
                    }
                }
                
                return results;
            }
        ''')
        
        print(f"Found {len(content_data)} content panels")
        
        chapters = []
        for i, data in enumerate(content_data, 1):
            filename = f"{i:02d}_{self._slugify(data['title'])}.md"
            filepath = output_dir / filename
            filepath.write_text(data['content'], encoding='utf-8')
            chapters.append(filename)
            print(f"  -> {filename} ({len(data['content'])} chars)")
        
        return chapters
    
    def _slugify(self, text: str) -> str:
        """Convert text to safe filename."""
        # Keep only alphanumeric, spaces, and hyphens
        safe = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in text)
        # Replace spaces with underscores and collapse multiple underscores
        safe = safe.lower().replace(' ', '_').replace('-', '_')
        while '__' in safe:
            safe = safe.replace('__', '_')
        # Truncate to reasonable length
        return safe[:80].strip('_')


def extract_story(event_slug: str, character_dir: str, event_folder: str = None, 
                  headless: bool = False) -> Dict:
    """
    Convenience function to extract story chapters.
    
    Args:
        event_slug: Wiki event slug (e.g., "Auld_Lang_Fry_PREMIUM")
        character_dir: Character root dir (e.g., "characters/vajra")
        event_folder: Optional custom folder name
        headless: Run browser in headless mode
    
    Returns:
        Extraction result dict
    """
    ext = StoryExtractor(headless=headless)
    return ext.extract(event_slug, character_dir, event_folder)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python story.py <event_slug> <character_dir> [event_folder]")
        print("Example: python story.py Auld_Lang_Fry_PREMIUM characters/vajra")
        print()
        print("Output: story/{event_folder}/raw/*.md")
        sys.exit(1)
    
    event_slug = sys.argv[1]
    character_dir = sys.argv[2]
    event_folder = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = extract_story(event_slug, character_dir, event_folder)
    
    print(f"\nResult: {'Success' if result['success'] else 'Failed'}")
    print(f"Output: {result.get('output_dir')}")
    print(f"Chapters: {result['chapters']}")
