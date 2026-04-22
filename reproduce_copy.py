import shutil
import os
import pathlib
import tempfile

def test_copytree():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = pathlib.Path(tmpdir) / "src"
        src.mkdir()
        (src / "test.txt").write_text("hello")
        
        dst = pathlib.Path(tmpdir) / "dst"
        
        print(f"Copying {src} to {dst}")
        try:
            shutil.copytree(src, dst)
            print("shutil.copytree success")
        except Exception as e:
            print(f"shutil.copytree failed: {e}")

if __name__ == "__main__":
    test_copytree()
