"""
Download FrameNet 1.7 via NLTK.

Author: Anonymous Authors
"""

import sys


def main():
    try:
        import nltk
    except ImportError:
        print("Install nltk: pip install nltk")
        return 1

    print("Downloading FrameNet 1.7 via NLTK...")
    nltk.download("framenet_v17", quiet=False)
    from nltk.corpus import framenet as fn
    print(f"[OK] FrameNet loaded: {len(fn.frames())} frames")
    return 0

if __name__ == "__main__":
    sys.exit(main())
