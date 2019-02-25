
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2
import subprocess
import signal
import sys
import fnmatch
import os

def restore_signals():
        signals = ('SIGPIPE', 'SIGXFZ', 'SIGXFSZ')
        for sig in signals:
            if hasattr(signal, sig):
                signal.signal(getattr(signal, sig), signal.SIG_DFL)

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               preexec_fn=restore_signals)

    stdout, stderr = process.communicate()
    returncode = process.returncode
    return stdout, stderr, returncode


def run_term_on_error(cmd):
    o, e, rc = run_cmd(cmd)
    if e:
        sys.exit('\nCommand:\n{}\n\nterminated with error:\n{}'.format(cmd, e.strip()))
    return o, e, rc

def run_and_watch(cmd):
    process = subprocess.Popen(cmd, shell=True,
                               stdout=sys.stdout, stderr=subprocess.PIPE,
                               preexec_fn=restore_signals)

    stderr = process.communicate()
    returncode = process.returncode
    return stderr, returncode


def run_print_output_error(cmd):
    o, e, rc = run_cmd(cmd)
    if o or e:
        print('\ncommand: {}'.format(cmd))
    if o:
        print('output:\n{}'.format(o.strip()))
    if e:
        print('\nerror:\n{}'.format(e.strip()))
    return o, e, rc

def make_built_pkgs(dir_to_walk):
    #built_pkgs=\$(find /root/packages -name "*.tbz2" | xargs)
    built_pks = ""

    for dirpath, dirnames, filenames in os.walk(dir_to_walk):
        for filename in filenames:
            if fnmatch.fnmatch(filename, "*.tbz2"): # Match search string
                built_pks += (os.path.join(dirpath, filename) + " ")
    return built_pks

