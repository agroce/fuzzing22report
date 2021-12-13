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

mutants = []
for line in open("prioritized.txt", 'r'):
    mutants.append("mutants/" + line.split()[0])

shutil.copy("original_fuzzgoat.c", "fuzzgoat.c")
subprocess.call(["make clean; make"], shell=True, stdout=dnull, stderr=dnull)

cmd = "afl-fuzz -i " + in_d + " -o " + out_d + ".initial -d ./fuzzgoat @@"
P = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid, stdout=dnull, stderr=dnull)
time.sleep(run_time)
os.killpg(os.getpgid(P.pid), signal.SIGTERM)

os.mkdir(out_d)

os.mkdir(out_d + ".corpus")
subprocess.call(["cp " + out_d + ".initial/queue/id* " + out_d + ".corpus"], shell=True)
subprocess.call(["cp " + out_d + ".initial/crashes/id* " + out_d + ".corpus"], shell=True)

N = 0
for M in mutants:
    N += 1
    elapsed = time.time() - start
    if elapsed > (timeout / 2.0):
        print("TIME'S UP FOR MUTANTS!")
        break
    print(N, round(elapsed, 2), "MUTANT:", M)
    print("CORPUS SIZE:", len(glob.glob(out_d + ".corpus/id*")))
    shutil.copy(M, "fuzzgoat.c")
    subprocess.call(["make clean; make"], shell=True, stdout=dnull, stderr=dnull)
    s_scan = time.time()
    try:
        shutil.rmtree(out_d + ".filtcorpus")
    except:
        pass 
    os.mkdir(out_d + ".filtcorpus")
    C = 0
    check_files = glob.glob(out_d + ".corpus/*")
    for t in check_files:
        r = subprocess.call(["ulimit -t 1; ./fuzzgoat " + t], shell=True, stdout=dnull, stderr=dnull)
        if r in [0, 1]:
            shutil.copy(t, out_d + ".filtcorpus/" + "test." + str(C))
        C += 1
    print("SCANNING TOOK", time.time()-s_scan, "SECONDS")
    
    cmd = "afl-fuzz -i " + out_d + ".filtcorpus  -o " + out_d + "/" + str(N) + "  -d ./fuzzgoat @@"
    start_P = time.time()
    P = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid, stdout=dnull, stderr=dnull)
    while (P.poll() is None) and ((time.time() - start_P) < run_time):
        time.sleep(0.5)
    if P.poll() is None:
        os.killpg(os.getpgid(P.pid), signal.SIGTERM)
        collect = glob.glob(out_d + "/" + str(N) + "/queue/id*")
        collect.extend(glob.glob(out_d + "/" + str(N) + "/crashes/id*"))
        for f in collect:
            if ("orig:") not in f:
                shutil.copy(f, out_d + ".corpus")
    else:
        print("failed fuzz, skipping collecting data")

shutil.copy("original_fuzzgoat.c", "fuzzgoat.c")
subprocess.call(["make clean; make"], shell=True, stdout=dnull, stderr=dnull)

s_scan = time.time()
try:
    shutil.rmtree(out_d + ".filtcorpus")
except:
    pass
os.mkdir(out_d + ".filtcorpus")
C = 0
check_files = glob.glob(out_d + ".corpus/*")
for t in check_files:
    r = subprocess.call(["ulimit -t 1; ./fuzzgoat " +  t], shell=True, stdout=dnull, stderr=dnull)
    if r in [0, 1]:
        shutil.copy(t, out_d + ".filtcorpus/" + "test." + str(C))
        C += 1
print("SCANNING TOOK", time.time()-s_scan, "SECONDS")


cmd = "afl-fuzz -i " + out_d + ".filtcorpus" + " -o " + out_d + ".FINAL -d ./fuzzgoat @@"
P = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
elapsed = time.time()-start
time.sleep(timeout-elapsed)
os.killpg(os.getpgid(P.pid), signal.SIGTERM)
