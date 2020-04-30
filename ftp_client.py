import os
import shutil
import time
from ftplib import FTP
import sys
from utils.file import get_size

import requests

if hasattr(sys, 'frozen'):
    os.environ['PATH'] = sys._MEIPASS + ";" + os.environ['PATH']
from PyQt5.QtCore import QStringListModel, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QCursor, QStandardItemModel, QStandardItem

from ui import main
from PyQt5.QtWidgets import QApplication, QMainWindow, QAbstractItemView, QMenu, QMessageBox, QHeaderView
from utils.file_manage import FileManage
from log import logger

file = FileManage(current_dir='C:\\')
file_ico = '📄'
dir_ico = '📂'

def error_msg():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    return '{} 出了点问题，详情请见日志'.format(current_time)


class Downloadthread(QThread):
    """
    下载线程，用于下载文件或目录
    """
    _signal = pyqtSignal(int)

    def __init__(self, ftpclient, server_filename, server_dir, local_dir, overwrite=False):
        super(Downloadthread, self).__init__()
        self.step = 0
        self.ftpclient=ftpclient
        self.server_filename=server_filename
        self.server_dir=server_dir
        self.local_dir=local_dir
        self.overwrite=overwrite

    def __del__(self):
        self.wait()

    def ftp_download(self, ftpclient, server_filename, server_dir, local_dir, overwrite=False):
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
        self._signal.emit(0)
        #ftpclient.listView_local_display(file)
        #ftpclient.log_list.setText('下载完成')

    def run(self):
        """
        线程运行
        :return:
        """
        self.ftp_download_dir(self.ftpclient,self.server_filename,self.server_dir,self.local_dir,self.overwrite)


class Uploadthread(QThread):
    """
    上传线程，用于本地上传文件/目录
    """
    _signal = pyqtSignal(int)
    _signal_bar = pyqtSignal(int)

    def __init__(self, ftpclient, local_filename, local_dir, server_dir, overwrite=False):
        super(Uploadthread, self).__init__()
        self.step = 0
        self.size = get_size(os.path.join(local_dir, local_filename))
        self.ftpclient=ftpclient
        self.local_filename=local_filename
        self.server_dir=server_dir
        self.local_dir=local_dir
        self.overwrite=overwrite

    def __del__(self):
        self.wait()

    def ftp_upload(self, ftpclient, local_filename, local_dir, server_dir, overwrite=False):
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
        self._signal.emit(0)

    def run(self):
        """
        线程运行
        :return:
        """
        self.ftp_upload_dir(self.ftpclient,self.local_filename,self.local_dir,self.server_dir,self.overwrite)


class FtpClient(main.Ui_MainWindow):
    def __init__(self, window):
        super(FtpClient, self).__init__()
        self.size=0
        self.setupUi(window)
        self.ftp = FTP()
        self.ftp.encoding = 'utf-8'
        self.slm = QStringListModel()
        self.listView_local.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView_local.setModel(self.slm)
        self.listView_local_display(file=file)

        self.slm_server = QStringListModel()
        self.listView_server.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView_server.setModel(self.slm_server)

        self.tlm = QStandardItemModel()
        self.tlm.setHorizontalHeaderLabels(['名称', 'PID', '内存占用'])
        self.tableView_process.setModel(self.tlm)
        self.tableView_process.horizontalHeader().setStretchLastSection(True)
        self.tableView_process.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


        self.listView_local.doubleClicked.connect(self.listView_local_doubleClicked)
        self.listView_local.setContextMenuPolicy(3)
        self.listView_local.customContextMenuRequested[QPoint].connect(self.listView_local_menu)
        self.listView_server.setContextMenuPolicy(3)
        self.listView_server.customContextMenuRequested[QPoint].connect(self.listView_server_menu)
        self.tableView_process.setContextMenuPolicy(3)
        self.tableView_process.customContextMenuRequested[QPoint].connect(self.tableView_process_menu)

        self.listView_server.doubleClicked.connect(self.listView_server_doubleClicked)
        self.button_local_up.clicked.connect(self.button_local_up_clicked)
        self.button_server_up.clicked.connect(self.button_server_up_clicked)
        self.button_connect.clicked.connect(self.button_connect_clicked)
        self.button_left.clicked.connect(self.thread_download)
        self.button_right.clicked.connect(self.thread_upload)
        self.button_refrush.clicked.connect(self.button_refrush_clicked)
        self.button_open_process.clicked.connect(self.button_open_process_clicked)
        self.button_changeC.clicked.connect(self.button_changeC_clicked)
        self.button_changeD.clicked.connect(self.button_changeD_clicked)
        self.local_dir.returnPressed.connect(self.local_dir_returnPressed)

    # 功能函数
    def refrush_process(self):
        """
        刷新远程进程
        :return:
        """
        r = requests.get('http://{ip}:{port}/process_list'.format(ip = self.address,port = 5001))
        process_list = r.json()
        for x in range(len(process_list)):
            for y in range(3):
                item = QStandardItem(process_list[x][y])
                self.tlm.setItem(x,y,item)

    def server_file_type(self, current_filename):
        """
        Ftp当前目录下的文件类型 dir或file
        :param filename: Ftp当前目录下的文件名
        :return: dir或file
        """
        for file in self.ftp.mlsd(facts=['type']):
            filename = file[0]
            file_type = file[1]['type']
            if filename==current_filename:
                return file_type



    # todo:隐藏文件显示可以控制
    def listView_local_display(self, file=file):
        """
        本地文件框刷新显示
        :param file: 文件对象实例
        :return:
        """
        file.update_list()
        file_list = ['{} {}'.format(dir_ico, dir) for dir in file.sub_directory_list] + \
                    ['{} {}'.format(file_ico, filename) for filename in file.sub_file_list]
        file_list = [file for file in file_list if not file.split(' ',1)[1].startswith('.')]
        self.slm.setStringList(file_list)

        self.local_dir.setText(file.current_dir)

    def listView_server_display(self):
        """
        远程文件框刷新显示
        :return:
        """
        self.server_list = []
        for file in self.ftp.mlsd(facts=['type']):
            filename = file[0]
            file_type = file[1]['type']
            if file_type == 'dir':
                self.server_list.append('{} {}'.format(dir_ico, filename))
            elif file_type == 'file':
                self.server_list.append('{} {}'.format(file_ico, filename))
        self.server_list.sort()
        self.server_list = [file for file in self.server_list if not file.split(' ',1)[1].startswith('.')]
        self.slm_server.setStringList(self.server_list)
        self.server_dir.setText(self.ftp.pwd())

    def local_selected_file(self):
        """
        本地选中的文件名
        :return:
        """
        filename = self.listView_local.currentIndex().data()
        if filename.startswith('{} '.format(file_ico)):
            filename = filename.split(' ', 1)[1]
            return filename

    def local_selected_dir(self):
        """
        本地选中的目录名
        :return:
        """
        filename = self.listView_local.currentIndex().data()
        if filename.startswith('{} '.format(dir_ico)):
            filename = filename.split(' ', 1)[1]
            return filename

    def local_selected_type(self):
        """
        本地选中的类型，dir或file
        :return:
        """
        filename = self.listView_local.currentIndex().data()
        if filename:
            if filename.startswith(dir_ico):
                return 'dir'
            elif filename.startswith(file_ico):
                return 'file'
        else:
            self.log_list.setText('当前未选中文件')

    def server_selected_file(self):
        """
        远程选中的文件名
        :return:
        """
        filename = self.listView_server.currentIndex().data()
        if filename.startswith('{} '.format(file_ico)):
            filename = filename.split(' ', 1)[1]
            return filename

    def server_selected_dir(self):
        """
        远程选中的目录名
        :return:
        """
        filename = self.listView_server.currentIndex().data()
        if filename.startswith('{} '.format(dir_ico)):
            filename = filename.split(' ', 1)[1]
            return filename

    def server_selected_type(self):
        """
        远程选中的文件类型，dir或file
        :return:
        """
        filename = self.listView_server.currentIndex().data()
        if filename.startswith(dir_ico):
            return 'dir'
        elif filename.startswith(file_ico):
            return 'file'


    '''
    def _ftp_upload_dir(self, target_dir, local_dir, server_dir):
        self.ftp.cwd(server_dir)
        local_path = os.path.join(local_dir, target_dir)
        if os.path.isfile(local_path):
            self.ftp_upload(target_dir, local_dir, server_dir)
        elif os.path.isdir(local_dir):
            self.ftp.mkd(target_dir)
            self.ftp.cwd(target_dir)
            for filename in os.listdir(os.path.join(local_dir, target_dir)):
                print('上传{}'.format(filename))
                self._ftp_upload_dir(filename,
                                      os.path.join(local_dir,target_dir),
                                      os.path.join(server_dir, target_dir))

    def ftp_upload_dir(self, target_dir, local_dir, server_dir):
        server_dir_tmp = self.ftp.pwd()
        self._ftp_upload_dir(target_dir, local_dir, server_dir)
        self.ftp.cwd(server_dir_tmp)

    def ftp_upload(self, local_filename, local_dir, server_dir, overwrite=False):
        if not overwrite:
            server_filename = local_filename
            while '{} {}'.format(file_ico, server_filename) in self.server_list:
                server_filename = server_filename + '.bak'
        else:
            server_filename = local_filename
        fp = open(os.path.join(local_dir, local_filename), "rb")
        buf_size = 1024
        self.ftp.storbinary("STOR {}".format(os.path.join(server_dir, server_filename)), fp, buf_size)
        fp.close()
    '''


    def _delete_path(self, target_dir, server_dir):
        """
        删除一个目录及其中全部的文件
        由于FTP只能删除空目录，要递归删除
        :param path:
        :return:
        """
        print('{}--{}'.format(server_dir, target_dir))
        #print('{}/{}'.format(server_dir, target_dir))
        self.ftp.cwd('{}/{}'.format(server_dir, target_dir))
        for file in self.ftp.mlsd(facts=['type']):
            filename = file[0]
            file_type = file[1]['type']
            if file_type == "dir":
                self._delete_path(filename, '{}/{}'.format(server_dir, target_dir))
            elif file_type == 'file':
                self.ftp.delete(filename)
        self.ftp.rmd('{}/{}'.format(server_dir, target_dir))

    def delAllfile(self, target_dir, server_dir):
        """
        递归删除服务器的某个文件或目录
        :param target_dir: 要删除的目录
        :param server_dir: 服务器当前所在目录
        :return:
        """
        server_dir_tmp = self.ftp.pwd()
        self._delete_path(target_dir, server_dir)
        self.ftp.cwd(server_dir_tmp)

    def edit_server_file(self, filename): #todo: fix
        local_tmp_dir = r'C:\tmp'
        if not os.path.isdir(local_tmp_dir):
            os.mkdir(local_tmp_dir)
        self.ftp_download(filename, self.ftp.pwd(), local_tmp_dir, overwrite = True)
        os.system('notepad.exe "{}"'.format(os.path.join(local_tmp_dir,filename)))
        # 编辑结束
        self.ftp_upload(filename, local_tmp_dir, self.ftp.pwd(), overwrite=True)
        os.remove(os.path.join(local_tmp_dir,filename))
        print('done')

    # 事件函数
    def local_dir_returnPressed(self):
        """
        本地地址栏按回车键
        :return:
        """
        try:
            file.enter(self.local_dir.text())
            self.listView_local_display(file)
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def button_changeC_clicked(self):
        """
        远程按下切换C盘
        :return:
        """
        try:
            self.ftp.close()
            self.ftp.connect(self.address, self.port)
            self.ftp.login('C', '12345')
            self.listView_server_display()
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def button_changeD_clicked(self):
        """
        远程按下切换D盘
        :return:
        """
        try:
            self.ftp.close()
            self.ftp.connect(self.address, self.port)
            self.ftp.login('D', '12345')
            self.listView_server_display()
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def listView_local_doubleClicked(self, data):
        """
        本地文件双击
        :param data:
        :return:
        """
        try:
            if self.local_selected_type() == 'dir':
                file.enter_from_current(self.local_selected_dir())
                self.listView_local_display(file)
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def listView_server_doubleClicked(self, data):
        """
        远程文件双击
        :param data:
        :return:
        """
        try:
            selected_type = self.server_selected_type()
            if selected_type == 'dir':
                directory = self.server_selected_dir()
                self.ftp.cwd(directory)
                self.listView_server_display()
            elif selected_type == 'file':
                filename = self.server_selected_file()
                self.edit_server_file(filename)

        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def button_local_up_clicked(self):
        """
        本地按下向上
        :return:
        """
        try:
            file.enter_parent()
            self.listView_local_display(file)
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def button_server_up_clicked(self):
        """
        远程按下向上
        :return:
        """
        try:
            self.ftp.cwd('..')
            self.listView_server_display()
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def button_connect_clicked(self):
        """
        连接按钮点击
        :return:
        """
        try:
            self.ftp.connect(self.lineEdit_address.text(), int(self.lineEdit_port.text()))
            self.ftp.login('C', '12345')
            self.listView_server_display()
            self.log_list.setText('连接成功')
            self.address = self.lineEdit_address.text()
            self.port = int(self.lineEdit_port.text())
        except Exception as e:
            self.log_list.setText('连接失败')
            logger.error(e, exc_info=True)

    def button_refrush_clicked(self):
        """
        进程刷新按钮点击
        :return:
        """
        try:
            self.refrush_process()
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def button_open_process_clicked(self):
        """
        打开进程按钮点击
        :return:
        """
        try:
            data = {
                'path': self.lineEdit_open_process.text()
            }
            r = requests.post('http://{ip}:{port}/open_process'.format(ip = self.address,port = 5001), json=data)
            self.log_list.setText(r.text)
            self.refrush_process()
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def listView_local_menu(self, point):
        """
        本地文件右键菜单
        :param point:
        :return:
        """
        try:
            def action_delete_handler():
                try:
                    selected_type = self.local_selected_type()
                    if selected_type == 'file':
                        filename = self.local_selected_file()
                        print(os.path.join(file.current_dir, filename))
                        os.remove(os.path.join(file.current_dir, filename))
                    elif selected_type == 'dir':
                        directory = self.local_selected_dir()
                        shutil.rmtree(os.path.join(file.current_dir, directory))
                    self.listView_local_display(file)
                except Exception as e:
                    self.log_list.setText(error_msg())
                    logger.error(e, exc_info=True)

            popMenu = QMenu()
            action_delete = popMenu.addAction("删除")
            action_delete.triggered.connect(action_delete_handler)
            popMenu.exec_(QCursor.pos())
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def listView_server_menu(self, point):
        """
        远程文件右键菜单
        :param point:
        :return:
        """
        try:
            def action_delete_handler():
                try:
                    selected_type = self.server_selected_type()
                    if selected_type == 'file':
                        filename = self.server_selected_file()
                        self.ftp.delete(filename)
                    elif selected_type == 'dir':
                        directory = self.server_selected_dir()
                        self.delAllfile(directory, self.ftp.pwd())
                    self.listView_server_display()
                except Exception as e:
                    self.log_list.setText(error_msg())
                    logger.error(e, exc_info=True)
            popMenu = QMenu()
            action_delete = popMenu.addAction("删除")
            action_delete.triggered.connect(action_delete_handler)
            popMenu.exec_(QCursor.pos())
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def tableView_process_menu(self, point):
        """
        进程右键菜单
        :param point:
        :return:
        """
        try:
            def action_close_handler():
                try:
                    row = self.tableView_process.currentIndex().row()
                    name=self.tlm.item(row,0).text()
                    r = requests.get('http://{ip}:{port}/kill_process/{name}'.format(ip=self.address, port=5001, name=name))
                    self.log_list.setText(r.text)
                    self.refrush_process()
                except Exception as e:
                    self.log_list.setText(error_msg())
                    logger.error(e, exc_info=True)
            popMenu = QMenu()
            action_delete = popMenu.addAction("关闭")
            action_delete.triggered.connect(action_close_handler)
            popMenu.exec_(QCursor.pos())
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def thread_download(self):
        """
        下载按钮点击（开启线程）
        :return:
        """
        try:
            # download
            if self.server_selected_type() == 'file':
                if os.path.isfile(os.path.join(file.current_dir, self.server_selected_file())):
                    reply = QMessageBox.warning(MainWindow,
                                                "文件名重复",
                                                "文件名重复，确定要覆盖吗？",
                                                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                    if reply == QMessageBox.Yes:
                        self.download_thread = Downloadthread(self, self.server_selected_file(), self.ftp.pwd(), file.current_dir, overwrite=True)
                    elif reply == QMessageBox.No:
                        self.download_thread = Downloadthread(self, self.server_selected_file(), self.ftp.pwd(),
                                                              file.current_dir)
                else:
                    self.download_thread = Downloadthread(self, self.server_selected_file(), self.ftp.pwd(),
                                                          file.current_dir)
            else:
                if os.path.isdir(os.path.join(file.current_dir, self.server_selected_dir())):
                    reply = QMessageBox.warning(MainWindow,
                                                "文件夹重复",
                                                "文件夹重复！操作不允许",
                                                QMessageBox.Cancel)
                    return
                self.download_thread = Downloadthread(self, self.server_selected_dir(), self.ftp.pwd(),
                                                      file.current_dir)
            self.download_thread._signal.connect(self.callback_download)  # 进程连接回传到GUI的事件
            self.download_thread.start()
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def thread_upload(self, data):
        """
        上传按钮点击（开启线程）
        :param data:
        :return:
        """
        try:
            # upload
            self.log_list.setText('正在计算大小......')
            if self.local_selected_type() == 'file':
                if '{} {}'.format(file_ico, self.local_selected_file()) in self.server_list:
                    reply = QMessageBox.warning(MainWindow,
                                                "文件名重复",
                                                "文件名重复，确定要覆盖吗？",
                                                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                    if reply == QMessageBox.Yes:
                        self.upload_thread = Uploadthread(self, self.local_selected_file(),file.current_dir,
                                                              self.ftp.pwd(),overwrite=True)
                    elif reply == QMessageBox.No:
                        self.upload_thread = Uploadthread(self, self.local_selected_file(), file.current_dir,
                                                            self.ftp.pwd())
                else:
                    self.upload_thread = Uploadthread(self, self.local_selected_file(), file.current_dir,
                                                        self.ftp.pwd())
            else:
                if '{} {}'.format(dir_ico, self.local_selected_dir()) in self.server_list:
                    reply = QMessageBox.warning(MainWindow,
                                                "文件夹重复",
                                                "文件夹重复！操作不允许",
                                                QMessageBox.Cancel)
                    return
                self.upload_thread = Uploadthread(self, self.local_selected_dir(), file.current_dir,
                                                    self.ftp.pwd())
            self.upload_thread._signal.connect(self.callback_upload)  # 进程连接回传到GUI的事件
            self.upload_thread._signal_bar.connect(self.callback_upload_bar)
            self.upload_thread.start()
        except Exception as e:
            self.log_list.setText(error_msg())
            logger.error(e, exc_info=True)

    def callback_download(self, msg):
        """
        下载数据回传
        :param msg: 下载了多少MB
        :return:
        """
        if msg==0:
            self.log_list.setText('下载完成')
            self.listView_local_display()
        else:
            self.log_list.setText('已下载{}MB'.format(msg))
        print(msg)

    def callback_upload(self, msg):
        """
        上传数据回传
        :param msg: 上传了多少MB
        :return:
        """
        if msg==0:
            self.log_list.setText('上传完成')
            self.progressBar.setValue(0)
            self.listView_server_display()
        else:
            self.log_list.setText('已上传{}MB'.format(msg))

    def callback_upload_bar(self,msg):
        """
        进度条进度回传
        :param msg: 进度条百分比数字
        :return:
        """
        print(msg)
        self.progressBar.setValue(msg)

app = QApplication(sys.argv)
MainWindow = QMainWindow()
ui = FtpClient(MainWindow)
MainWindow.show()
sys.exit(app.exec_())


# ftp.set_debuglevel(2)
# ftp.cwd(r'C:\Users\Fan\Desktop\test')
# print(ftp.nlst())
# print(ftp.retrlines('LIST'))
# with open('test.txt', 'wb') as f:
#    ftp.retrbinary('RETR test.txt', f.write)
# ftp.quit()
