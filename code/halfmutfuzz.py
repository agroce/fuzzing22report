import glob
import os
import random
import signal
import shutil
import subprocess
import sys
import time

dnull = open(os.devnull, 'w')

in_d = sys.argv[1]
out_d = sys.argv[2]
timeout = float(sys.argv[3])

run_time = 300

start = time.time()

mutants = glob.glob("mutants/*.c")
random.shuffle(mutants)


half_timeout = timeout / 2.0

os.mkdir(out_d)

N = 0
for M in mutants:
    N += 1
    elapsed = time.time() - start
    if elapsed > half_timeout:
        print("TIME'S UP!")
        break
    print(N, round(elapsed, 2), "MUTANT:", M)
    shutil.copy(M, "fuzzgoat.c")
    subprocess.call(["make clean; make"], shell=True, stdout=dnull, stderr=dnull)
    cmd = "afl-fuzz -i " + in_d + " -o " + out_d + "/" + str(N) + "  -d ./fuzzgoat @@"
    start_P = time.time()
    P = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid, stdout=dnull, stderr=dnull)
    while (P.poll() is None) and ((time.time() - start_P) < run_time):
        time.sleep(0.5)
    if P.poll() is None:
        os.killpg(os.getpgid(P.pid), signal.SIGTERM)
    else:
        print("Failed fuzz!")

shutil.copy("original_fuzzgoat.c", "fuzzgoat.c")
subprocess.call(["make clean; make"], shell=True, stdout=dnull, stderr=dnull)

s_scan = time.time()
os.mkdir(out_d + ".corpus")
C = 0
check_files = glob.glob(out_d + "/*/queue/id*")
check_files.extend(glob.glob(out_d + "/*/crashes/id*"))
for t in check_files:
    r = subprocess.call(["ulimit -t 1; ./fuzzgoat " + t], shell=True, stdout=dnull, stderr=dnull)
    if r not in [0, 1]:
        print(t, "CRASHES")
    else:
        shutil.copy(t, out_d + ".corpus/" + "test." + str(C))
        C += 1
print("SCANNING TOOK", time.time()-s_scan, "SECONDS")

cmd = "afl-fuzz -i " + out_d + ".corpus" + " -o " + out_d + ".FINAL -d ./fuzzgoat @@"
P = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
elapsed = time.time()-start
time.sleep(timeout-elapsed)
os.killpg(os.getpgid(P.pid), signal.SIGTERM)

