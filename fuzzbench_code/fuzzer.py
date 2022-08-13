# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Integration code for AFLplusplus fuzzer."""

# This optimized afl++ variant should always be run together with
# "aflplusplus" to show the difference - a default configured afl++ vs.
# a hand-crafted optimized one. afl++ is configured not to enable the good
# stuff by default to be as close to vanilla afl as possible.
# But this means that the good stuff is hidden away in this benchmark
# otherwise.

import glob
import os
from pathlib import Path
import random
import shutil
import filecmp
from time import time
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer

import signal
from contextlib import contextmanager

class TimeoutException(Exception): pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def build():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    out = os.getenv("OUT")
    src = os.getenv("SRC")
    storage_dir = "/storage"
    os.mkdir(storage_dir)
    mutate_dir = f"{storage_dir}/mutant_files"
    os.mkdir(mutate_dir)
    mutate_bins = f"{storage_dir}/mutant_bins"
    os.mkdir(mutate_bins)
    mutate_scripts = f"{storage_dir}/mutant_scripts"
    os.mkdir(mutate_scripts)

    orig_fuzz_target = os.getenv("FUZZ_TARGET")
    aflplusplus_fuzzer.build()
    shutil.copy(f"{out}/{orig_fuzz_target}", f"{mutate_bins}/{orig_fuzz_target}")
    benchmark = os.getenv("BENCHMARK")
    os.system(f"cp {src}/build.sh {mutate_scripts}/orig_build.sh")
    os.system(f"sed -i 's/git checkout/#git checkout/g' {src}/build.sh")
    os.system(f"cp {src}/build.sh {mutate_scripts}/mutate_build.sh")

    SOURCE_EXTENSIONS = [".cc"] #[".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"]
    NUM_MUTANTS = 1 #(23 / 2) * 60 / 5 # 23 hours - half fuzzing mutants * 60 (convert to mins) / 5 mins/mutant
    # Use heuristic to try to find benchmark directory, otherwise look for all files in the current directory.
    subdirs = [name for name in os.listdir(src) if os.path.isdir(os.path.join(src, name))]
    benchmark_src_dir = src
    for directory in subdirs:
        if directory in benchmark:
            benchmark_src_dir = os.path.join(src, directory)
            break

    source_files = []
    for extension in SOURCE_EXTENSIONS:  
        source_files += glob.glob(f"{benchmark_src_dir}/**/*{extension}", recursive=True)

    mutants = []
    for source_file in source_files:
        source_dir = os.path.dirname(source_file).split(src, 1)[1]
        Path(f"{mutate_dir}/{source_dir}").mkdir(parents=True, exist_ok=True)
        os.system(f"mutate {source_file} --mutantDir {mutate_dir}/{source_dir} --noCheck > /dev/null")
        source_base = os.path.basename(source_file).split(".")[0]
        mutants_glob = glob.glob(f"{mutate_dir}/{source_dir}/{source_base}.mutant.*")
        mutants += [f"{source_dir}/{mutant.split('/')[-1]}"[1:] for mutant in mutants_glob]

    random.shuffle(mutants)    
    with open(f"{mutate_dir}/mutants.txt", "w") as f:
        f.writelines("%s\n" % l for l in mutants)

    NUM_PRIORITIZED = min(NUM_MUTANTS * 100, len(mutants))

    os.system(f"prioritize_mutants {mutate_dir}/mutants.txt {mutate_dir}/prioritize_mutants_sorted.txt {NUM_PRIORITIZED} --sourceDir {src} --mutantDir {mutate_dir} > {mutate_dir}/prioritize_mutants.txt")
    prioritized_list = []
    with open(f"{mutate_dir}/prioritize_mutants_sorted.txt", "r") as f:
        prioritized_list = f.read().splitlines()

    num_non_buggy = 1
    ind = 0
    while num_non_buggy <= NUM_MUTANTS:
        mutant = prioritized_list[ind] # mutants[ind] 
        suffix = "." + mutant.split(".")[-1]
        mpart = ".mutant." + mutant.split(".mutant.")[1]
        source_file = f"{src}/{mutant.replace(mpart, suffix)}"
        print(source_file)
        print(f"{mutate_dir}/{mutant}")
        os.system(f"cp {source_file} {mutate_dir}/orig")
        os.system(f"cp {mutate_dir}/{mutant} {source_file}")
        try:
            new_fuzz_target = f"{os.getenv('FUZZ_TARGET')}.{num_non_buggy}"
            os.system(f"rm -rf {out}/*")
            aflplusplus_fuzzer.build()
            if not filecmp.cmp(f'{mutate_bins}/{orig_fuzz_target}', f'{out}/{orig_fuzz_target}', shallow=False):
                shutil.copy(f"{out}/{orig_fuzz_target}", f"{mutate_bins}/{new_fuzz_target}")
                num_non_buggy += 1
        except Exception as e:
            print(e)
            pass
        os.system(f"cp {mutate_dir}/orig {source_file}")
        ind += 1
    
    os.system(f"cp {mutate_scripts}/orig_build.sh {src}/build.sh")
    os.system(f"rm -rf {out}/*")
    aflplusplus_fuzzer.build()
    os.system(f"cp {mutate_bins}/* {out}/")




def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    TIMEOUT = 500
    mutants = glob.glob(f"{target_binary}.*")
    input_corpus_dir = "/storage/input_corpus"
    os.mkdir("/storage")
    os.mkdir(input_corpus_dir)
    os.environ['AFL_SKIP_CRASHES'] = "1"

    for mutant in mutants:
        os.system(f"cp -r {input_corpus_dir}/* {input_corpus}/*")
        try:
            with time_limit(TIMEOUT):
                aflplusplus_fuzzer.fuzz(input_corpus,
                                        output_corpus,
                                        mutant)
        except TimeoutException as e:
            pass
        os.system(f"cp -r {output_corpus}/* {input_corpus_dir}/*")

    os.system(f"cp -r {input_corpus_dir}/* {input_corpus}/*")
    aflplusplus_fuzzer.fuzz(input_corpus, output_corpus, target_binary)