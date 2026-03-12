# scripts/check_new_content.py
import json
from pathlib import Path
import sys
from datetime import datetime  # Add this line

def count_new_content():
    """Returns number of new posts since last build"""
    last_build_file = Path('data/last_build_state.json')
    current_posts = list(Path('_posts').glob('*.md'))
    
    if not last_build_file.exists():
        # First run, count all as new
        return len(current_posts)
    
    last_state = json.loads(last_build_file.read_text())
    last_count = last_state.get('post_count', 0)
    last_files = set(last_state.get('post_files', []))
    
    current_files = set(str(p) for p in current_posts)
    new_files = current_files - last_files
    
    # Save current state
    last_build_file.write_text(json.dumps({
        'post_count': len(current_posts),
        'post_files': list(current_files),
        'last_check': str(datetime.now())
    }))
    
    return len(new_files)

if __name__ == "__main__":
    count = count_new_content()
    print(count)  # This will be captured by GitHub Actions
    sys.exit(0 if count > 0 else 1)
