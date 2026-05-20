import sys
import re
import os

def update_index_html(current_dir="client-apps/v-current"):
    if not os.path.exists("index.html"):
        print("index.html not found.")
        return

    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()

    # Mapping of element IDs to filenames
    mappings = {
        "download-windows": "SFLN-Client-windows-latest.exe",
        "download-linux": "SFLN-Client-ubuntu-latest",
        "download-macos": "SFLN-Client-macos-latest",
        "download-win-server": "SFLN-Server-windows-latest-CUI.exe",
        "download-linux-server": "SFLN-Server-ubuntu-latest-CUI",
        "download-android": "SFLN-Android-Bundle.apk"
    }

    updated_count = 0
    for element_id, filename in mappings.items():
        filepath = f"{current_dir}/{filename}"

        # Regex to find href="..." followed or preceded by id="..." (or vice versa)
        # Using a more robust pattern to match the correct <a> tag by ID
        pattern = rf'(<a\s+[^>]*id="{element_id}"[^>]*href=")([^"]*)(")'
        new_tag_start = rf'\1{filepath}\3'

        if re.search(pattern, content):
            content = re.sub(pattern, new_tag_start, content)
            print(f"Updated {element_id} -> {filepath}")
            updated_count += 1
        else:
            # Try alternate attribute order
            pattern_alt = rf'(<a\s+[^>]*href=")([^"]*)("[^>]*id="{element_id}")'
            if re.search(pattern_alt, content):
                content = re.sub(pattern_alt, rf'\1{filepath}\3', content)
                print(f"Updated {element_id} (alt) -> {filepath}")
                updated_count += 1
            else:
                print(f"Warning: Could not find element with id='{element_id}' in index.html")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Update complete. {updated_count} links modified.")

if __name__ == "__main__":
    update_index_html()
