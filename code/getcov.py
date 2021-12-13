import glob
import subprocess
import sys

g = sys.argv[1:]

sigs = []

dirs = []
for d in g:
    dirs.extend(glob.glob(d))

subprocess.call(["rm -rf *.gcda"], shell=True)
    
for f in dirs:
    with open("out", 'w') as outf:
        r = subprocess.call(["ulimit -t 1; ./fuzzgoat_cov " + f], shell=True, stderr=outf,stdout=outf)

with open("gcov.out", 'w') as outf:
    subprocess.call(["gcov -b fuzzgoat.c main.c"], shell=True, stdout=outf, stderr=outf)
with open("gcov.out", 'w') as outf:
    line_tot = 0.0
    line_exec_tot = 0.0
    branch_tot = 0.0
    branch_taken_tot = 0.0
    for line in outf:
        if "Lines executed" in line:
            ls = line.split()
            lc = int(ls[-1])
            line_tot += lc
            percent = float(ls.split(":")[1].split("%")[0])
            line_exec_tot += percent * lc
        if "Taken at least once" in line:
            ls = line.split()
            lc = int(ls[-1])
            branch_tot += lc
            percent = float(ls.split(":")[1].split("%")[0])
            branch_taken_tot += percent * lc
print("Line cov:", line_exec_tot / line_tot)
print("Branch cov:", branch_taken_tot / branch_tot)
            
            



