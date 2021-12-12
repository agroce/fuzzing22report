import os
import signal
import subprocess
import sys
import time

dnull = open(os.devnull, 'w')

in_d = sys.argv[1]
out_d = sys.argv[2]
timeout = float(sys.argv[3])

cmd = "afl-fuzz -i " + in_d + " -o " + out_d + " -d ./fuzzgoat @@"
P = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
time.sleep(timeout)
os.killpg(os.getpgid(P.pid), signal.SIGTERM)
