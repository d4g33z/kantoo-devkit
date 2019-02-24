
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU General Public License v2
import subprocess
import signal
import sys
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


def run_print_output_error(cmd):
    o, e, rc = run_cmd(cmd)
    if o or e:
        print('\ncommand: {}'.format(cmd))
    if o:
        print('output:\n{}'.format(o.strip()))
    if e:
        print('\nerror:\n{}'.format(e.strip()))
    return o, e, rc


