from pathlib import Path
files = ['999_1.txt','999_2.txt','999_6.txt','999_10.txt','999_50.txt','999_32.txt']
base = Path('gutenberg_books/plain_text')
for f in files:
    text = (base / f).read_text(encoding='utf-8', errors='replace')
    print(f'=== {f} ===')
    print(text[:600])
    print()
