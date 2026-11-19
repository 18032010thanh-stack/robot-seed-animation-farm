import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import pipeline

class TestChunks(unittest.TestCase):
    def test_all_chunks(self):
        c=pipeline.config()
        got=[pipeline.bounds(c,i) for i in range(1,19)]
        self.assertEqual(got[0],(1,150))
        self.assertEqual(got[-1],(2551,2700))
        self.assertEqual([b[1]-b[0]+1 for b in got],[150]*18)
        self.assertEqual(pipeline.bounds(c,1,30),(1,30))
    def test_invalid(self):
        c=pipeline.config()
        with self.assertRaises(ValueError): pipeline.bounds(c,0)
        with self.assertRaises(ValueError): pipeline.bounds(c,19)
if __name__=="__main__": unittest.main()
