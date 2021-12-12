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
        r = subprocess.call(["ulimit -t 1; ./fuzzgoat_ASAN " + f], shell=True, stderr=outf,stdout=outf)
    with open("out", "rb") as outf:
        sig = ""
        for line in outf:
            line = str(line, encoding="utf-8", errors='ignore')
            if "fuzzgoat" in line:
                sig += line.split(" in ")[1]
        if (sig not in sigs) and (sig != ""):
            print("NEW SIG:")
            print(sig)
            print("="*80)
            sigs.append(sig)
print(len(sigs))
