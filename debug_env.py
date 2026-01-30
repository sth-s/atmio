import os
import sys

def debug_env_file():
    env_path = os.path.abspath(".env")
    print(f"Checking file: {env_path}")
    
    if not os.path.exists(env_path):
        print("File does NOT exist.")
        return

    # File Stats
    stats = os.stat(env_path)
    print(f"File Size: {stats.st_size} bytes")
    
    # Raw Content Check
    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()
            print(f"Line count: {len(lines)}")
            
            for i, line in enumerate(lines):
                if "OPENROUTER_API_KEY" in line:
                    key_part = line.split("=", 1)[1].strip()
                    print(f"Line {i+1} matches OPENROUTER_API_KEY")
                    print(f"Raw Value Length: {len(key_part)}")
                    print(f"Raw Value Start: {key_part[:10]}...")
                    if len(key_part) < 20:
                        print("WARNING: Key looks too short (placeholder?)")
                    else:
                        print("Key length looks plausible.")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    debug_env_file()
