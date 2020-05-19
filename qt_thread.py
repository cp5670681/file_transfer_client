import json
import os
import time

from PyQt5.QtCore import pyqtSignal, QThread

from utils.constant import file_ico
from utils.file import get_size


class Downloadthread(QThread):
    """
    下载线程，用于下载文件或目录
    """
    _signal = pyqtSignal(int)
    _signal_message_box = pyqtSignal(str)

    def __init__(self, ftpclient, server_filenames, server_dir, local_dir, overwrite=True):
        super(Downloadthread, self).__init__()
        self.step = 0
        self.ftpclient=ftpclient
        self.server_filenames=server_filenames
        self.server_dir=server_dir
        self.local_dir=local_dir
        self.overwrite=overwrite

    def __del__(self):
        self.wait()

    def ftp_download(self, ftpclient, server_filename, server_dir, local_dir, overwrite=True):
        """
        Ftp单文件下载
        :param ftpclient: ftpclient实例
        :param server_filename: 要下载的文件名
        :param server_dir: 所在服务器目录
        :param local_dir: 所在本地目录
        :param overwrite: 当文件存在时，是否重写文件
        :return:
        """
        buf_size = 1024
        M=1024*1024
        def write(data):
            self.step+=buf_size
            if self.step%M==0:
                self._signal.emit(self.step/M)
            fp.write(data)

        if not overwrite:
            local_filename = server_filename
            while os.path.isfile(os.path.join(local_dir, local_filename)):
                local_filename = local_filename + '.bak'
        else:
            local_filename = server_filename
        fp = open(os.path.join(local_dir, local_filename), "wb")
        ftpclient.ftp.retrbinary('RETR {}'.format(os.path.join(server_dir, server_filename)), write, buf_size)
        fp.close()

    def _ftp_download_dir(self, ftpclient, target_dir, server_dir, local_dir,overwrite):
        """
        递归下载目录里所有文件
        :param ftpclient: ftpclient实例
        :param target_dir: 要下载的目录（或文件）
        :param server_dir: 所在服务器目录
        :param local_dir: 所在本地目录
        :param overwrite: 当文件存在时，是否重写文件
        :return:
        """
        # self.log_list.setText(self.log_list.toPlainText() + '\n' + target_dir)
        ftpclient.ftp.cwd(server_dir)
        target_type = ftpclient.server_file_type(target_dir)
        if target_type == 'file':
            self.ftp_download(ftpclient, target_dir, server_dir, local_dir,overwrite)
        elif target_type == 'dir':
            os.mkdir(os.path.join(local_dir, target_dir))
            ftpclient.ftp.cwd(target_dir)
            for file in ftpclient.ftp.mlsd(facts=['type']):
                filename = file[0]
                file_type = file[1]['type']
                self._ftp_download_dir(ftpclient, filename,
                                      os.path.join(server_dir,target_dir),
                                      os.path.join(local_dir, target_dir),overwrite)

    def ftp_download_dir(self, ftpclient, target_dir, server_dir, local_dir,overwrite):
        """
        递归下载目录里所有文件，把恢复服务器目录，发送完成信号
        :param ftpclient: ftpclient实例
        :param target_dir: 要下载的目录（或文件）
        :param server_dir: 所在服务器目录
        :param local_dir: 所在本地目录
        :param overwrite: 当文件存在时，是否重写文件
        :return:
        """
        server_dir_tmp = ftpclient.ftp.pwd()
        self._ftp_download_dir(ftpclient, target_dir, server_dir, local_dir,overwrite)
        ftpclient.ftp.cwd(server_dir_tmp)

    def ftp_download_dirs(self, ftpclient, target_dir_list, server_dir, local_dir,overwrite):
        try:
            for target_dir in target_dir_list:
                self.ftp_download_dir(ftpclient, target_dir, server_dir, local_dir, overwrite)
                time.sleep(0.1)
                ftpclient.listView_local_display()
            self._signal.emit(0)
        except PermissionError as e:
            data={
                'title':'权限不足',
                'msg': str(e)
            }
            self._signal_message_box.emit(json.dumps(data))
        except Exception as e:
            data = {
                'title': '错误',
                'msg': str(e)
            }
            self._signal_message_box.emit(json.dumps(data))


    def run(self):
        """
        线程运行
        :return:s
        """
        self.ftp_download_dirs(self.ftpclient,self.server_filenames,self.server_dir,self.local_dir,self.overwrite)


class Uploadthread(QThread):
    """
    上传线程，用于本地上传文件/目录
    """
    _signal = pyqtSignal(int)
    _signal_bar = pyqtSignal(int)
    _signal_message_box = pyqtSignal(str)

    def __init__(self, ftpclient, local_filenames, local_dir, server_dir, overwrite=True):
        super(Uploadthread, self).__init__()
        self.step = 0
        self.size = 0
        for file in local_filenames:
            self.size += get_size(os.path.join(local_dir, file))
        self.ftpclient=ftpclient
        self.local_filenames=local_filenames
        self.server_dir=server_dir
        self.local_dir=local_dir
        self.overwrite=overwrite

    def __del__(self):
        self.wait()

    def ftp_upload(self, ftpclient, local_filename, local_dir, server_dir, overwrite=True):
        """
        ftp上传单文件
        :param ftpclient: ftpclient实例
        :param local_filename: 要上传的文件名
        :param server_dir: 所在服务器目录
        :param local_dir: 所在本地目录
        :param overwrite: 当文件存在时，是否重写文件
        :return:
        """
        buf_size = 1024
        M = 1024 * 1024
        def upload_file_cb(block):
            self.step += buf_size
            if self.step % M == 0:
                self._signal.emit(self.step / M)
                percentage = int(self.step/self.size*100)
                self._signal_bar.emit(percentage)


        if not overwrite:
            server_filename = local_filename
            while '{} {}'.format(file_ico, server_filename) in ftpclient.server_list:
                server_filename = server_filename + '.bak'
        else:
            server_filename = local_filename
        fp = open(os.path.join(local_dir, local_filename), "rb")
        ftpclient.ftp.storbinary("STOR {}".format(os.path.join(server_dir, server_filename)), fp, buf_size, callback = upload_file_cb)
        fp.close()

    def _ftp_upload_dir(self,ftpclient, target_dir, local_dir, server_dir, overwrite):
        """
        递归上传文件或目录
        :param ftpclient: ftpclient实例
        :param target_dir: 要上传的文件/目录
        :param server_dir: 所在服务器目录
        :param local_dir: 所在本地目录
        :param overwrite: 当文件存在时，是否重写文件
        :return:
        """
        ftpclient.ftp.cwd(server_dir)
        local_path = os.path.join(local_dir, target_dir)
        if os.path.isfile(local_path):
            self.ftp_upload(ftpclient,target_dir, local_dir, server_dir, overwrite)
        elif os.path.isdir(local_dir):
            ftpclient.ftp.mkd(target_dir)
            ftpclient.ftp.cwd(target_dir)
            for filename in os.listdir(os.path.join(local_dir, target_dir)):
                print('上传{}'.format(filename))
                self._ftp_upload_dir(ftpclient, filename,
                                      os.path.join(local_dir,target_dir),
                                      os.path.join(server_dir, target_dir),overwrite)

    def ftp_upload_dir(self,ftpclient, target_dir, local_dir, server_dir,overwrite):
        """
        递归上传文件或目录，把服务器目录还原，并发送成功信号
        :param ftpclient: ftpclient实例
        :param target_dir: 要上传的文件/目录
        :param server_dir: 所在服务器目录
        :param local_dir: 所在本地目录
        :param overwrite: 当文件存在时，是否重写文件
        :return:
        """
        server_dir_tmp = ftpclient.ftp.pwd()
        self._ftp_upload_dir(ftpclient,target_dir, local_dir, server_dir,overwrite)
        ftpclient.ftp.cwd(server_dir_tmp)


    def ftp_upload_dirs(self,ftpclient, target_dir_list, local_dir, server_dir,overwrite):
        try:
            for target_dir in target_dir_list:
                print('下载{}'.format(target_dir))
                self.ftp_upload_dir(ftpclient, target_dir, local_dir, server_dir, overwrite)
                time.sleep(0.1)
                ftpclient.listView_server_display()
            self._signal.emit(0)
        except Exception as e:
            data={
                'title':'错误',
                'msg': str(e)
            }
            self._signal_message_box.emit(json.dumps(data))

    def run(self):
        """
        线程运行
        :return:
        """
        self.ftp_upload_dirs(self.ftpclient,self.local_filenames,self.local_dir,self.server_dir,self.overwrite)