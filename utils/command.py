import os
import subprocess
import threading
from multiprocessing import Process
import re


class Command():
    @staticmethod
    def command(cmd):
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.stdout.read().decode('gbk')
        # for i in iter(p.stdout.readline, ''):
        #     if len(i) < 1:
        #         break
        #     out = i.decode('gbk').strip()
        #     print(out)
        for i in iter(p.stderr.readline, ''):
            if len(i) < 1:
                break
            err = i.decode('gbk').strip()
            raise OSError(err)
        return out

    @classmethod
    def command_background(cls, cmd):
        t = threading.Thread(target=cls.command, args=(cmd,))
        t.setDaemon(True)
        t.start()

    @classmethod
    def kill_process(cls, pro_name):
        return cls.command('taskkill /F /IM {}'.format(pro_name))

    @classmethod
    def open_process_front(cls, path):
        try:
            os.startfile(path)
        except Exception as e:
            print(e)

    @classmethod
    def open_process(cls, path):
        Process(target=cls.open_process_front, args=(path,)).start()

    @classmethod
    def tasklist(cls):
        tasks = []
        tasklist = Command.command('tasklist /NH').split('\n')
        for line in tasklist:
            m = re.match(r'(.+?) +(\d+) \w+ +\d+ +([\d,]+ K)', line)
            if m:
                tasks.append((m.group(1), m.group(2), m.group(3)))
        tasks = sorted(tasks,key=lambda x:int(x[2].split(' ')[0].replace(',','')), reverse=True)
        return tasks



if __name__=='__main__':
    print(Command.tasklist())