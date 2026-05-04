"""
Download NELL beliefs from HuggingFace.

Uses the datasets library to download rtw-cmu/nell.
The data is cached by HuggingFace under ~/.cache/huggingface/.

Author: Anonymous Authors
"""

import sys

def main():
    try:
        from datasets import load_dataset
    except ImportError:
        print("Install datasets: pip install datasets")
        return 1

    print("Downloading NELL beliefs from HuggingFace (rtw-cmu/nell)...")
    print("This may take several minutes on first run.")
    ds = load_dataset("rtw-cmu/nell", "nell_belief", split="train")
    print(f"[OK] NELL loaded: {len(ds)} beliefs")
    return 0

if __name__ == "__main__":
    sys.exit(main())
