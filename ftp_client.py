import json
import sys
import os
if hasattr(sys, 'frozen'):
    os.environ['PATH'] = sys._MEIPASS + ";" + os.environ['PATH']
import shutil
import time
from ftplib import FTP
from qt_thread import Downloadthread, Uploadthread
from utils.file import get_size

import requests

from PyQt5.QtCore import QStringListModel, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QCursor, QStandardItemModel, QStandardItem

from ui import main
from PyQt5.QtWidgets import QApplication, QMainWindow, QAbstractItemView, QMenu, QMessageBox, QHeaderView
from utils.file_manage import FileManage
from log import logger
from utils.constant import file_ico, dir_ico

file = FileManage(current_dir='C:\\')

def error_msg():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    return '{} 出了点问题，详情请见日志'.format(current_time)





class FtpClient(main.Ui_MainWindow):
    def __init__(self, window):
        super(FtpClient, self).__init__()
        self.local_list = []
        self.server_list = []
        self.process_list = []
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

        self.lineEdit_local_search.textChanged.connect(self.lineEdit_local_search_textChanged)
        self.lineEdit_server_search.textChanged.connect(self.lineEdit_server_search_textChanged)
        self.lineEdit_process_search.textChanged.connect(self.lineEdit_process_search_textChanged)



    # 功能函数
    def test(self,data):
        query_list = []
        for line in self.local_list:
            if data in line:
                query_list.append(line)
        self.slm.setStringList(query_list)

    def lineEdit_local_search_textChanged(self, data):
        query_list = []
        for line in self.local_list:
            if data in line:
                query_list.append(line)
        self.slm.setStringList(query_list)

    def lineEdit_server_search_textChanged(self, data):
        query_list = []
        for line in self.server_list:
            if data in line:
                query_list.append(line)
        self.slm_server.setStringList(query_list)

    def lineEdit_process_search_textChanged(self, data):
        tmp = self.process_list
        r=[]
        for line in tmp:
            if data in line[0]:
                r.append(line)
        self.tlm.clear()
        for x in range(len(r)):
            for y in range(3):
                item = QStandardItem(r[x][y])
                self.tlm.setItem(x, y, item)

    def server_delete_item(self, filename):
        """
        远程删除一项
        :param filename:
        :return:
        """
        try:
            self.ftp.delete(filename)
        except:
            self.delAllfile(filename, self.ftp.pwd())
        finally:
            self.listView_server_display()

    def server_delete_items(self, filenames):
        """
        远程删除多项
        :param filenames:
        :return:
        """
        for filename in filenames:
            print('删除{}'.format(filename))
            self.server_delete_item(filename)
            time.sleep(0.1)
        self.listView_server_display()

    def local_delete_item(self, filename):
        """
        本地删除一项
        :param filename:
        :return:
        """
        path = os.path.join(file.current_dir, filename)
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

    def local_delete_items(self, filenames):
        """
        本地删除多项
        :param filenames:
        :return:
        """
        for filename in filenames:
            print('删除{}'.format(filename))
            self.local_delete_item(filename)
            time.sleep(0.1)
        self.listView_local_display(file)

    def refrush_process(self):
        """
        刷新远程进程
        :return:
        """
        r = requests.get('http://{ip}:{port}/process_list'.format(ip = self.address,port = 5001))
        self.process_list = r.json()
        for x in range(len(self.process_list)):
            for y in range(3):
                item = QStandardItem(self.process_list[x][y])
                self.tlm.setItem(x,y,item)
        self.lineEdit_process_search.setText('')

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
        self.local_list = [file for file in file_list if not file.split(' ',1)[1].startswith('.')]
        self.slm.setStringList(self.local_list)

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

    def local_selected_items(self):
        """
        本地选中的所有文件或文件夹
        :return: list
        """
        items = self.listView_local.selectedIndexes()
        return [item.data().split(' ',1)[1] for item in items]


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

    def server_selected_items(self):
        """
        本地选中的所有文件或文件夹
        :return: list
        """
        items = self.listView_server.selectedIndexes()
        return [item.data().split(' ',1)[1] for item in items]


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
        self.ftp_download(filename, self.ftp.pwd(), local_tmp_dir)
        os.system('notepad.exe "{}"'.format(os.path.join(local_tmp_dir,filename)))
        # 编辑结束
        self.ftp_upload(filename, local_tmp_dir, self.ftp.pwd())
        os.remove(os.path.join(local_tmp_dir,filename))
        print('done')

    def ftp_download(self, server_filename, server_dir, local_dir):
        buf_size = 1024
        local_filename = server_filename
        fp = open(os.path.join(local_dir, local_filename), "wb")
        self.ftp.retrbinary('RETR {}'.format(os.path.join(server_dir, server_filename)), fp.write, buf_size)
        fp.close()

    def ftp_upload(self, local_filename, local_dir, server_dir, overwrite=True):
        buf_size = 1024
        server_filename = local_filename
        fp = open(os.path.join(local_dir, local_filename), "rb")
        self.ftp.storbinary("STOR {}".format(os.path.join(server_dir, server_filename)), fp, buf_size)
        fp.close()

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
                self.lineEdit_local_search.setText('')
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
                self.lineEdit_server_search.setText('')
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
                    items = self.local_selected_items()
                    self.local_delete_items(items)
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
                    items = self.server_selected_items()
                    self.server_delete_items(items)
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
            self.widget_server.setEnabled(False)
            self.download_thread = Downloadthread(self, self.server_selected_items(), self.ftp.pwd(),
                                                      file.current_dir)
            self.download_thread._signal.connect(self.callback_download)  # 进程连接回传到GUI的事件
            self.download_thread._signal_message_box.connect(self.callback_message_box)
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
            self.widget_server.setEnabled(False)
            files = self.local_selected_items()
            self.upload_thread = Uploadthread(self, files, file.current_dir,
                                                    self.ftp.pwd())
            self.upload_thread._signal.connect(self.callback_upload)  # 进程连接回传到GUI的事件
            self.upload_thread._signal_bar.connect(self.callback_upload_bar)
            self.upload_thread._signal_message_box.connect(self.callback_message_box)
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
            self.widget_server.setEnabled(True)
        else:
            self.log_list.setText('已下载{}MB'.format(msg))

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
            self.widget_server.setEnabled(True)
        else:
            self.log_list.setText('已上传{}MB'.format(msg))

    def callback_upload_bar(self,msg):
        """
        进度条进度回传
        :param msg: 进度条百分比数字
        :return:
        """
        self.progressBar.setValue(msg)

    def callback_message_box(self, msg):
        msg_d = json.loads(msg)
        reply = QMessageBox.information(MainWindow,
                                    msg_d['title'],
                                    msg_d['msg'],
                                    QMessageBox.Yes)

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
