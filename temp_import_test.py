import time, sys, os
t0 = time.time()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print(f"{time.time()-t0:.1f}s: import main...")
from api.main import app
print(f"{time.time()-t0:.1f}s: done, id={id(app)}")
