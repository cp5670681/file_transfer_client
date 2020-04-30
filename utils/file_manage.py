import os

dir = r'C:\Program Files'


class FileManage():
    def __init__(self, current_dir,):
        self.current_dir = current_dir
        self.sub_directory_list = []
        self.sub_file_list = []
        self.enter(current_dir)

    def enter(self, abs_dir):
        """
        进入某个目录
        :param abs_dir: 绝对路径
        :return:
        """
        print('进入{}'.format(abs_dir))
        self.current_dir = abs_dir
        self.sub_directory_list, self.sub_file_list = self.current_file_list()

    def enter_from_current(self, directory):
        """
        进入当前目录下的某个目录
        :param directory:
        :return:
        """
        self.enter(os.path.join(self.current_dir, directory))


    def enter_parent(self):
        """
        进入上级目录
        :return:
        """
        self.enter(os.path.abspath(os.path.dirname(self.current_dir)))

    @classmethod
    def file_list(cls, abs_dir):
        """
        返回某个绝对路径下的目录列表和文件列表
        :param abs_dir:
        :return:
        """
        directory_list = []
        file_list = []
        for file in os.listdir(abs_dir):
            file_path = os.path.join(abs_dir, file)
            if os.path.isdir(file_path):
                directory_list.append(file)
            else:
                file_list.append(file)
        return directory_list, file_list

    def current_file_list(self,):
        """
        返回当前路径下的目录列表和文件列表
        :return:
        """
        return self.file_list(self.current_dir)

    def update_list(self):
        self.enter(self.current_dir)


if __name__ == '__main__':
    file = FileManage(r'C:\Program Files')
    file.enter_from_current('Android')
    file.enter_parent()

