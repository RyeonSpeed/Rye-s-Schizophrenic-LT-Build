import subprocess
import os

if __name__ == '__main__':
    os.chdir('./the_lost_players')
    fname = 'the_lost_players.exe'
    subprocess.Popen(fname, shell=True)