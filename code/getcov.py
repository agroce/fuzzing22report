import glob
import subprocess
import sys

g = sys.argv[1:]

sigs = []

dirs = []
for d in g:
    dirs.extend(glob.glob(d))

for f in dirs:
    with open("out", 'w') as outf:
        r = subprocess.call(["ulimit -t 1; ./fuzzgoat_cov " + f], shell=True, stderr=outf,stdout=outf)

